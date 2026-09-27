"""Day 5: LangGraph graph for the research pipeline.

Graph: query -> retrieve_candidates -> fan_out(analyze each case) -> merge -> synthesize_memo
"""
import asyncio
import logging
import operator
import yaml
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

from db.database import SessionLocal
from db.models import CaseCorpus, CaseFinding, ResearchReport
from chains.retrieval import retrieve_candidates
from chains.analysis import analyze_case, CaseAnalysis
from chains.synthesis import synthesize_memo

logger = logging.getLogger(__name__)

_config_path = Path(__file__).parent.parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)

PER_TASK_TIMEOUT = _config["analysis"]["per_task_timeout_seconds"]
RELEVANCE_THRESHOLD = _config["retrieval"]["relevance_threshold"]


# --- State types ---

class CaseResult(TypedDict):
    case_id: int
    case_name: str
    citation: str
    relevance_score: float
    relevance_note: str
    status: str
    reason: str


class OverallState(TypedDict):
    query: str
    query_id: int
    candidates: list[dict]
    case_results: Annotated[list[CaseResult], operator.add]
    memo: str
    cases_analyzed: list[int]
    cases_not_analyzed: list[int]
    cited_case_ids: list[int]


class AnalyzeState(TypedDict):
    query: str
    case_id: int
    case_data: dict


# --- Helper ---

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


# --- Graph nodes ---

def retrieve_node(state: OverallState) -> dict:
    """Retrieve candidate cases from the vector store."""
    query = state["query"]
    logger.info(f"Retrieving candidates for: {query}")
    candidates = retrieve_candidates(query)
    logger.info(f"Found {len(candidates)} candidates")
    return {"candidates": candidates}


def route_to_analyses(state: OverallState) -> list[Send]:
    """Fan out: create one Send per candidate for parallel analysis."""
    sends = []
    for candidate in state["candidates"]:
        case_data = _get_case_data(candidate["case_id"])
        if case_data:
            sends.append(Send("analyze_case_node", {
                "query": state["query"],
                "case_id": candidate["case_id"],
                "case_data": case_data,
            }))
    return sends


def analyze_case_node(state: AnalyzeState) -> dict:
    """Analyze a single case's relevance (runs in parallel via Send)."""
    case_data = state["case_data"]
    query = state["query"]
    case_id = state["case_id"]

    try:
        result: CaseAnalysis = analyze_case(case_data, query)
        return {"case_results": [{
            "case_id": case_id,
            "case_name": case_data["case_name"],
            "citation": case_data["citation"],
            "relevance_score": result.relevance_score,
            "relevance_note": result.relevance_note,
            "status": "analyzed",
            "reason": "",
        }]}
    except Exception as e:
        logger.error(f"Error analyzing case {case_id}: {e}")
        return {"case_results": [{
            "case_id": case_id,
            "case_name": case_data.get("case_name", "Unknown"),
            "citation": case_data.get("citation", "Unknown"),
            "relevance_score": 0.0,
            "relevance_note": "",
            "status": "failed",
            "reason": str(e),
        }]}


def merge_node(state: OverallState) -> dict:
    """Merge all analysis results, classify as analyzed vs. not-analyzed."""
    results = state.get("case_results", [])
    analyzed = [r for r in results if r["status"] == "analyzed"]
    not_analyzed = [r for r in results if r["status"] != "analyzed"]

    logger.info(f"Merge: {len(analyzed)} analyzed, {len(not_analyzed)} not analyzed")

    return {
        "cases_analyzed": [r["case_id"] for r in analyzed],
        "cases_not_analyzed": [r["case_id"] for r in not_analyzed],
    }


def synthesize_node(state: OverallState) -> dict:
    """Synthesize the research memo from analyzed findings."""
    query = state["query"]
    results = state.get("case_results", [])

    analyzed = [r for r in results if r["status"] == "analyzed"
                and r.get("relevance_score", 0) >= RELEVANCE_THRESHOLD]
    not_analyzed = [
        {"case_id": r["case_id"], "reason": r.get("reason", "analysis failed or timed out")}
        for r in results if r["status"] != "analyzed"
    ]

    memo = synthesize_memo(query, analyzed, not_analyzed)

    analyzed_ids = set(state.get("cases_analyzed", []))
    cited_ids = []
    for r in analyzed:
        if r["case_id"] in analyzed_ids:
            cited_ids.append(r["case_id"])

    return {
        "memo": memo,
        "cited_case_ids": cited_ids,
    }


def _save_results(state: OverallState):
    """Persist results to database if query_id is provided."""
    query_id = state.get("query_id")
    if not query_id:
        return

    db = SessionLocal()
    try:
        for r in state.get("case_results", []):
            finding = CaseFinding(
                query_id=query_id,
                case_id=r["case_id"],
                relevance_score=r.get("relevance_score"),
                relevance_note=r.get("relevance_note"),
                status=r["status"],
            )
            db.add(finding)

        report = ResearchReport(
            query_id=query_id,
            memo_text=state.get("memo", ""),
            cited_case_ids=state.get("cited_case_ids", []),
            cases_analyzed=state.get("cases_analyzed", []),
            cases_not_analyzed=state.get("cases_not_analyzed", []),
        )
        db.add(report)
        db.commit()
    finally:
        db.close()


def save_node(state: OverallState) -> dict:
    """Save results to the database."""
    _save_results(state)
    return {}


# --- Build the graph ---

def build_graph() -> StateGraph:
    graph = StateGraph(OverallState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("analyze_case_node", analyze_case_node)
    graph.add_node("merge", merge_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("save", save_node)

    graph.add_edge(START, "retrieve")
    graph.add_conditional_edges("retrieve", route_to_analyses, ["analyze_case_node"])
    graph.add_edge("analyze_case_node", "merge")
    graph.add_edge("merge", "synthesize")
    graph.add_edge("synthesize", "save")
    graph.add_edge("save", END)

    return graph.compile()


research_graph = build_graph()


def run_research_graph(query: str, query_id: int = 0) -> dict:
    """Run the full research graph synchronously."""
    initial_state: OverallState = {
        "query": query,
        "query_id": query_id,
        "candidates": [],
        "case_results": [],
        "memo": "",
        "cases_analyzed": [],
        "cases_not_analyzed": [],
        "cited_case_ids": [],
    }

    final_state = research_graph.invoke(initial_state)

    return {
        "memo": final_state.get("memo", ""),
        "cases_analyzed": final_state.get("cases_analyzed", []),
        "cases_not_analyzed": final_state.get("cases_not_analyzed", []),
        "cited_case_ids": final_state.get("cited_case_ids", []),
    }
