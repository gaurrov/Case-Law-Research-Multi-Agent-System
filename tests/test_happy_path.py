"""Test 1: Happy path — query retrieves cases and produces a memo with valid citations."""
from unittest.mock import patch, MagicMock
from db.models import CaseCorpus


def _make_function_call_response(name, args):
    """Create a mock Gemini response with a function call."""
    fc = MagicMock()
    fc.name = name
    fc.args = args

    part = MagicMock()
    part.function_call = fc

    content = MagicMock()
    content.parts = [part]

    candidate = MagicMock()
    candidate.content = content

    resp = MagicMock()
    resp.candidates = [candidate]
    resp.text = None
    return resp


def _make_text_response(text):
    """Create a mock Gemini response with plain text (no function calls)."""
    part = MagicMock()
    part.function_call = MagicMock()
    part.function_call.name = ""

    content = MagicMock()
    content.parts = [part]

    candidate = MagicMock()
    candidate.content = content

    resp = MagicMock()
    resp.candidates = [candidate]
    resp.text = text
    return resp


def test_happy_path_agent_produces_memo(db_session, seed_cases):
    """The agent loop should call tools, analyze cases, and return a coherent memo."""

    mock_search_results = [
        {"case_id": seed_cases[0].id, "chunk_text": seed_cases[0].full_text[:300], "score": 0.9},
        {"case_id": seed_cases[1].id, "chunk_text": seed_cases[1].full_text[:300], "score": 0.85},
        {"case_id": seed_cases[2].id, "chunk_text": seed_cases[2].full_text[:300], "score": 0.6},
    ]

    chat_responses = [
        _make_function_call_response("search_cases", {"query": "digital privacy rights", "top_k": 5.0}),
        _make_function_call_response("analyze_relevance", {"case_id": float(seed_cases[0].id), "query": "digital privacy rights"}),
        _make_function_call_response("validate_citation", {"case_id": float(seed_cases[0].id)}),
        _make_text_response(
            f"# Research Memo\n\nBased on analysis, {seed_cases[0].case_name} "
            f"({seed_cases[0].citation}) is highly relevant to digital privacy rights."
        ),
    ]

    mock_chat = MagicMock()
    mock_chat.send_message.side_effect = chat_responses

    mock_chats = MagicMock()
    mock_chats.create.return_value = mock_chat

    mock_analysis_response = MagicMock()
    mock_analysis_response.text = "SCORE: 0.9\nNOTE: Directly discusses digital privacy rights"

    mock_models = MagicMock()
    mock_models.generate_content.return_value = mock_analysis_response

    with patch("agent.loop._client") as mock_client, \
         patch("agent.tools.vector_search", return_value=mock_search_results), \
         patch("agent.tools._genai_client") as mock_tools_client, \
         patch("agent.tools.SessionLocal", return_value=db_session):

        mock_client.chats = mock_chats
        mock_tools_client.models = mock_models

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
