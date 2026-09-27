"""Test 1: Happy path — query retrieves cases and produces a memo with valid citations."""
import json
from unittest.mock import patch, MagicMock
from db.models import CaseCorpus


def test_happy_path_agent_produces_memo(db_session, seed_cases):
    """The agent loop should call tools, analyze cases, and return a coherent memo."""

    mock_search_results = [
        {"case_id": seed_cases[0].id, "chunk_text": seed_cases[0].full_text[:300], "score": 0.9},
        {"case_id": seed_cases[1].id, "chunk_text": seed_cases[1].full_text[:300], "score": 0.85},
        {"case_id": seed_cases[2].id, "chunk_text": seed_cases[2].full_text[:300], "score": 0.6},
    ]

    tool_call_sequence = [
        MagicMock(
            stop_reason="tool_use",
            content=[
                MagicMock(type="tool_use", name="search_cases", id="tc1",
                          input={"query": "digital privacy rights", "top_k": 5}),
            ],
        ),
        MagicMock(
            stop_reason="tool_use",
            content=[
                MagicMock(type="tool_use", name="analyze_relevance", id="tc2",
                          input={"case_id": seed_cases[0].id, "query": "digital privacy rights"}),
            ],
        ),
        MagicMock(
            stop_reason="tool_use",
            content=[
                MagicMock(type="tool_use", name="validate_citation", id="tc3",
                          input={"case_id": seed_cases[0].id}),
            ],
        ),
        MagicMock(
            stop_reason="end_turn",
            content=[
                MagicMock(type="text",
                          text=f"# Research Memo\n\nBased on analysis, {seed_cases[0].case_name} "
                               f"({seed_cases[0].citation}) is highly relevant to digital privacy rights."),
            ],
        ),
    ]

    with patch("agent.loop._client") as mock_client, \
         patch("agent.tools.vector_search", return_value=mock_search_results), \
         patch("agent.tools._llm_client") as mock_analysis_client:

        mock_client.messages.create.side_effect = tool_call_sequence

        mock_analysis_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="SCORE: 0.9\nNOTE: Directly discusses digital privacy rights")]
        )

        # Patch SessionLocal to use our test session
        with patch("agent.tools.SessionLocal", return_value=db_session):
            from agent.loop import run_agent
            memo = run_agent("digital privacy rights")

    assert memo is not None
    assert len(memo) > 0
    assert "Research Memo" in memo
    assert seed_cases[0].citation in memo


def test_search_cases_deduplicates(db_session, seed_cases):
    """search_cases should not return the same case_id twice."""
    mock_hits = [
        {"case_id": seed_cases[0].id, "chunk_text": "chunk 1", "score": 0.9},
        {"case_id": seed_cases[0].id, "chunk_text": "chunk 2", "score": 0.85},
        {"case_id": seed_cases[1].id, "chunk_text": "chunk 3", "score": 0.7},
    ]

    with patch("agent.tools.vector_search", return_value=mock_hits), \
         patch("agent.tools.SessionLocal", return_value=db_session):
        from agent.tools import search_cases
        results = search_cases("test query", top_k=5)

    case_ids = [r["case_id"] for r in results]
    assert len(case_ids) == len(set(case_ids)), "Duplicate case_ids returned"
