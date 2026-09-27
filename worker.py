"""Day 3: Durable execution worker.

Polls the DB for queued research queries, runs the agent loop, writes incremental
results, sends heartbeats, and handles stuck/failed jobs.

Run as: python worker.py
"""
from dotenv import load_dotenv
load_dotenv()

import json
import time
import logging
import threading
import yaml
from google import genai
from google.genai import types
from datetime import datetime, timezone, timedelta
from pathlib import Path

from db.database import engine, SessionLocal
from db.models import Base, ResearchQuery, CaseFinding, ResearchReport, AgentEvent
from agent.tools import TOOL_DISPATCH, _get_gemini_tools
from embeddings.store import search as vector_search

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_config_path = Path(__file__).parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)

_worker_config = _config["worker"]
_llm_config = _config["llm"]

POLL_INTERVAL = _worker_config["poll_interval_seconds"]
HEARTBEAT_INTERVAL = _worker_config["heartbeat_interval_seconds"]
HEARTBEAT_TIMEOUT = _worker_config["heartbeat_timeout_seconds"]
MAX_RETRIES = _worker_config["max_retries"]

_genai_client = genai.Client()


def _now():
    return datetime.now(timezone.utc)


def _log_event(db, query_id: int, event_type: str, **kwargs):
    event = AgentEvent(
        query_id=query_id,
        event_type=event_type,
        tool_name=kwargs.get("tool_name"),
        tool_input=kwargs.get("tool_input"),
        tool_output=kwargs.get("tool_output"),
        error=kwargs.get("error"),
    )
    db.add(event)
    db.commit()


def _idempotency_key(query_id: int, case_id: int, tool_name: str) -> str:
    return f"{query_id}:{case_id}:{tool_name}"


def _check_cancellation(db, query_id: int) -> bool:
    q = db.get(ResearchQuery, query_id)
    return q is not None and q.cancel_requested == 1


def _heartbeat(db, query_id: int):
    q = db.get(ResearchQuery, query_id)
    if q:
        q.heartbeat_at = _now()
        db.commit()


class HeartbeatThread(threading.Thread):
    """Sends periodic heartbeats while the agent is running."""

    def __init__(self, query_id: int):
        super().__init__(daemon=True)
        self.query_id = query_id
        self.running = True

    def run(self):
        while self.running:
            try:
                db = SessionLocal()
                _heartbeat(db, self.query_id)
                db.close()
            except Exception as e:
                logger.warning(f"Heartbeat error: {e}")
            time.sleep(HEARTBEAT_INTERVAL)

    def stop(self):
        self.running = False


def process_query(query_id: int):
    """Run the full agent loop for a research query with durable execution."""
    db = SessionLocal()
    try:
        query = db.get(ResearchQuery, query_id)
        if not query or query.status != "queued":
            return

        query.status = "running"
        query.heartbeat_at = _now()
        db.commit()
        _log_event(db, query_id, "agent_start", tool_input={"query": query.query_text})

        hb = HeartbeatThread(query_id)
        hb.start()

        try:
            _run_agent_loop(db, query)
        except Exception as e:
            logger.error(f"Agent loop failed for query {query_id}: {e}")
            query.status = "failed"
            db.commit()
            _log_event(db, query_id, "agent_error", error=str(e))
        finally:
            hb.stop()
    finally:
        db.close()


def _run_agent_loop(db, query: ResearchQuery):
    """The actual agent loop with incremental DB writes, using Gemini."""
    query_text = query.query_text
    query_id = query.id

    system_prompt = """You are a legal research assistant. Your job is to research case law relevant to a user's query.

You have access to tools that let you search a case law corpus, retrieve full case texts, analyze their relevance, and validate citations.

Follow this workflow:
1. Use search_cases to find potentially relevant cases.
2. For the top results, use analyze_relevance to determine each case's relevance to the query.
3. Use validate_citation to confirm case IDs are valid before citing them.
4. After analyzing cases, provide a research memo summarizing your findings with proper citations.

If a tool returns an error, handle it gracefully — skip that case and continue with others.
Always cite cases you reference and note if any cases could not be fully analyzed."""

    chat = _genai_client.chats.create(
        model=_llm_config["model"],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[_get_gemini_tools()],
        ),
    )
    response = chat.send_message(query_text)

    for iteration in range(15):
        if _check_cancellation(db, query_id):
            query.status = "failed"
            db.commit()
            _log_event(db, query_id, "cancelled")
            return

        _log_event(db, query_id, "llm_call", tool_input={"iteration": iteration + 1})

        function_calls = []
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.function_call and part.function_call.name:
                    function_calls.append(part)

        if not function_calls:
            memo_text = response.text or ""
            _finalize_report(db, query, memo_text)
            return

        function_responses = []

        for part in function_calls:
            if _check_cancellation(db, query_id):
                query.status = "failed"
                db.commit()
                _log_event(db, query_id, "cancelled")
                return

            fc = part.function_call
            tool_name = fc.name
            tool_input = dict(fc.args) if fc.args else {}
            for key, val in tool_input.items():
                if isinstance(val, float) and val == int(val):
                    tool_input[key] = int(val)

            case_id = tool_input.get("case_id", 0)
            idem_key = _idempotency_key(query_id, case_id, tool_name)

            existing = db.query(CaseFinding).filter_by(idempotency_key=idem_key).first()
            if existing and existing.status == "analyzed":
                result = {
                    "case_id": existing.case_id,
                    "relevance_score": existing.relevance_score,
                    "relevance_note": existing.relevance_note,
                    "cached": True,
                }
                _log_event(db, query_id, "tool_cached", tool_name=tool_name,
                           tool_input=tool_input, tool_output=result)
            else:
                func = TOOL_DISPATCH.get(tool_name)
                if not func:
                    result = {"error": f"Unknown tool: {tool_name}"}
                else:
                    try:
                        result = func(**tool_input)
                    except Exception as e:
                        result = {"error": str(e)}

                _log_event(db, query_id, "tool_call", tool_name=tool_name,
                           tool_input=tool_input,
                           tool_output=result if "error" not in (result if isinstance(result, dict) else {}) else None,
                           error=result.get("error") if isinstance(result, dict) else None)

                if tool_name == "analyze_relevance" and isinstance(result, dict) and "error" not in result:
                    finding = db.query(CaseFinding).filter_by(
                        query_id=query_id, case_id=case_id
                    ).first()
                    if not finding:
                        finding = CaseFinding(
                            query_id=query_id,
                            case_id=case_id,
                            idempotency_key=idem_key,
                        )
                        db.add(finding)
                    finding.relevance_score = result.get("relevance_score", 0)
                    finding.relevance_note = result.get("relevance_note", "")
                    finding.status = "analyzed"
                    db.commit()

                elif tool_name == "analyze_relevance" and isinstance(result, dict) and "error" in result:
                    finding = db.query(CaseFinding).filter_by(
                        query_id=query_id, case_id=case_id
                    ).first()
                    if not finding:
                        finding = CaseFinding(
                            query_id=query_id,
                            case_id=case_id,
                            idempotency_key=idem_key,
                        )
                        db.add(finding)
                    finding.retry_count += 1
                    if finding.retry_count >= MAX_RETRIES:
                        finding.status = "failed"
                    db.commit()

            function_responses.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response={"result": json.dumps(result, default=str)},
                )
            )

        response = chat.send_message(function_responses)

    query.status = "failed"
    db.commit()
    _log_event(db, query_id, "max_iterations_reached")


def _finalize_report(db, query: ResearchQuery, memo_text: str):
    """Create the research report and mark query completed."""
    query_id = query.id
    findings = db.query(CaseFinding).filter_by(query_id=query_id).all()

    analyzed = [f.case_id for f in findings if f.status == "analyzed"]
    not_analyzed = [f.case_id for f in findings if f.status in ("failed", "timed_out", "pending")]
    cited = analyzed

    report = ResearchReport(
        query_id=query_id,
        memo_text=memo_text,
        cited_case_ids=cited,
        cases_analyzed=analyzed,
        cases_not_analyzed=not_analyzed,
    )
    db.add(report)

    query.status = "completed"
    db.commit()

    _log_event(db, query_id, "agent_done",
               tool_output={"cases_analyzed": len(analyzed), "cases_not_analyzed": len(not_analyzed)})


def reap_stuck_jobs():
    """Find jobs with stale heartbeats and mark them failed or requeue once."""
    db = SessionLocal()
    try:
        cutoff = _now() - timedelta(seconds=HEARTBEAT_TIMEOUT)
        stuck = (
            db.query(ResearchQuery)
            .filter(
                ResearchQuery.status == "running",
                ResearchQuery.heartbeat_at < cutoff,
            )
            .all()
        )
        for q in stuck:
            if q.retry_count < 1:
                logger.warning(f"Reaping stuck query {q.id} — requeuing (attempt {q.retry_count + 1})")
                q.status = "queued"
                q.retry_count += 1
                _log_event(db, q.id, "reaped_requeued")
            else:
                logger.warning(f"Reaping stuck query {q.id} — marking failed (max retries)")
                q.status = "failed"
                _log_event(db, q.id, "reaped_failed")
        db.commit()
    finally:
        db.close()


def poll_loop():
    """Main worker loop: poll for queued jobs and process them."""
    logger.info("Worker starting — polling for jobs...")
    while True:
        reap_stuck_jobs()

        db = SessionLocal()
        try:
            query = (
                db.query(ResearchQuery)
                .filter_by(status="queued")
                .order_by(ResearchQuery.created_at)
                .first()
            )
            query_id = query.id if query else None
        finally:
            db.close()

        if query_id:
            logger.info(f"Processing query {query_id}")
            process_query(query_id)
        else:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    from seed_data import seed_database
    from embeddings.store import build_index
    Base.metadata.create_all(engine)
    seed_database()
    build_index()
    poll_loop()
