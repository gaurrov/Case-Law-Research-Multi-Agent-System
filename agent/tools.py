"""Day 1 agent tools — plain functions with clear input/output schemas."""
import anthropic
import yaml
from pathlib import Path

from db.database import SessionLocal
from db.models import CaseCorpus
from embeddings.store import search as vector_search

_config_path = Path(__file__).parent.parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)

_llm_client = anthropic.Anthropic()
_llm_model = _config["llm"]["model"]

TOOL_SCHEMAS = [
    {
        "name": "search_cases",
        "description": "Search the case law corpus for cases relevant to a query. Returns a list of matching cases with snippets and relevance scores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The legal research query"},
                "top_k": {"type": "integer", "description": "Number of results to return", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_case_text",
        "description": "Retrieve the full text of a specific case by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "The database ID of the case"},
            },
            "required": ["case_id"],
        },
    },
    {
        "name": "analyze_relevance",
        "description": "Analyze how relevant a specific case is to a research query using LLM analysis. Returns a relevance score and note.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "The database ID of the case"},
                "query": {"type": "string", "description": "The research query to evaluate against"},
            },
            "required": ["case_id", "query"],
        },
    },
    {
        "name": "validate_citation",
        "description": "Check whether a case ID exists in the corpus. Returns true if valid, false otherwise.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer", "description": "The database ID of the case to validate"},
            },
            "required": ["case_id"],
        },
    },
]


def search_cases(query: str, top_k: int = 5) -> list[dict]:
    hits = vector_search(query, top_k=top_k)
    seen_case_ids = set()
    results = []
    db = SessionLocal()
    try:
        for hit in hits:
            cid = hit["case_id"]
            if cid in seen_case_ids:
                continue
            seen_case_ids.add(cid)
            case = db.get(CaseCorpus, cid)
            if case:
                results.append({
                    "case_id": cid,
                    "case_name": case.case_name,
                    "citation": case.citation,
                    "snippet": hit["chunk_text"][:300],
                    "score": round(hit["score"], 4),
                })
    finally:
        db.close()
    return results


def get_case_text(case_id: int) -> dict:
    db = SessionLocal()
    try:
        case = db.get(CaseCorpus, case_id)
        if not case:
            return {"error": f"Case with id {case_id} not found in corpus."}
        return {
            "case_id": case.id,
            "case_name": case.case_name,
            "citation": case.citation,
            "court": case.court,
            "date": case.date,
            "full_text": case.full_text,
            "summary": case.summary,
        }
    finally:
        db.close()


def analyze_relevance(case_id: int, query: str) -> dict:
    case_data = get_case_text(case_id)
    if "error" in case_data:
        return case_data

    prompt = f"""Analyze the relevance of this legal case to the research query.

Research Query: {query}

Case: {case_data['case_name']} ({case_data['citation']})
Summary: {case_data['summary']}
Full Text (excerpt): {case_data['full_text'][:2000]}

Provide:
1. A relevance score from 0.0 (not relevant) to 1.0 (highly relevant)
2. A brief note explaining the relevance or lack thereof

Respond in exactly this format:
SCORE: <number>
NOTE: <explanation>"""

    response = _llm_client.messages.create(
        model=_llm_model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text

    score = 0.5
    note = text
    for line in text.strip().split("\n"):
        if line.startswith("SCORE:"):
            try:
                score = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("NOTE:"):
            note = line.split(":", 1)[1].strip()

    return {
        "case_id": case_id,
        "case_name": case_data["case_name"],
        "relevance_score": round(score, 2),
        "relevance_note": note,
    }


def validate_citation(case_id: int) -> dict:
    db = SessionLocal()
    try:
        case = db.get(CaseCorpus, case_id)
        return {
            "case_id": case_id,
            "valid": case is not None,
            "citation": case.citation if case else None,
        }
    finally:
        db.close()


TOOL_DISPATCH = {
    "search_cases": search_cases,
    "get_case_text": get_case_text,
    "analyze_relevance": analyze_relevance,
    "validate_citation": validate_citation,
}
