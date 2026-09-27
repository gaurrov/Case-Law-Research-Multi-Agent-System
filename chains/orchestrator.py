"""Orchestrator-worker pattern: retrieval -> fan-out analysis -> merge -> synthesize."""
import asyncio
import logging
import yaml
from pathlib import Path

from db.database import SessionLocal
from db.models import CaseCorpus
from chains.retrieval import retrieve_candidates
from chains.analysis import analyze_case
from chains.synthesis import synthesize_memo

logger = logging.getLogger(__name__)

_config_path = Path(__file__).parent.parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)

MAX_CONCURRENCY = _config["analysis"]["max_concurrency"]
PER_TASK_TIMEOUT = _config["analysis"]["per_task_timeout_seconds"]
RELEVANCE_THRESHOLD = _config["retrieval"]["relevance_threshold"]


def _get_case_data(case_id: int) -> dict | None:
    db = SessionLocal()
    try:
        case = db.get(CaseCorpus, case_id)
        if not case:
            return None
        return {
            "case_id": case.id,
            "case_name": case.case_name,
            "citation": case.citation,
            "court": case.court,
            "date": case.date,
            "summary": case.summary,
            "full_text": case.full_text,
        }
    finally:
        db.close()


async def _analyze_one(case_data: dict, query: str, semaphore: asyncio.Semaphore) -> dict:
    """Analyze a single case with timeout and concurrency control."""
    async with semaphore:
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, analyze_case, case_data, query
                ),
                timeout=PER_TASK_TIMEOUT,
            )
            return {
                "case_id": case_data["case_id"],
                "case_name": case_data["case_name"],
                "citation": case_data["citation"],
                "relevance_score": result.relevance_score,
                "relevance_note": result.relevance_note,
                "status": "analyzed",
            }
        except asyncio.TimeoutError:
            logger.warning(f"Timeout analyzing case {case_data['case_id']}")
            return {
                "case_id": case_data["case_id"],
                "case_name": case_data.get("case_name", "Unknown"),
                "status": "timed_out",
                "reason": "Analysis timed out",
            }
        except Exception as e:
            logger.error(f"Error analyzing case {case_data['case_id']}: {e}")
            return {
                "case_id": case_data["case_id"],
                "case_name": case_data.get("case_name", "Unknown"),
                "status": "failed",
                "reason": str(e),
            }


async def run_research(query: str) -> dict:
    """Full orchestrator flow: retrieve -> fan-out analyze -> merge -> synthesize."""
    logger.info(f"Retrieving candidates for: {query}")
    candidates = retrieve_candidates(query)
    logger.info(f"Found {len(candidates)} candidate cases")

    case_data_list = []
    for c in candidates:
        data = _get_case_data(c["case_id"])
        if data:
            case_data_list.append(data)

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    tasks = [_analyze_one(cd, query, semaphore) for cd in case_data_list]
    results = await asyncio.gather(*tasks)

    analyzed = [r for r in results if r["status"] == "analyzed"]
    not_analyzed = [r for r in results if r["status"] != "analyzed"]

    relevant = [a for a in analyzed if a.get("relevance_score", 0) >= RELEVANCE_THRESHOLD]

    logger.info(f"Analyzed: {len(analyzed)}, Not analyzed: {len(not_analyzed)}, "
                f"Above threshold: {len(relevant)}")

    memo = await asyncio.get_event_loop().run_in_executor(
        None, synthesize_memo, query, relevant, not_analyzed
    )

    return {
        "memo": memo,
        "cases_analyzed": [r["case_id"] for r in analyzed],
        "cases_not_analyzed": [r["case_id"] for r in not_analyzed],
        "cited_case_ids": [r["case_id"] for r in relevant],
    }
