"""Test 2: Failure + recovery — agent handles bad case_id and continues."""
from unittest.mock import patch, MagicMock
from db.models import CaseCorpus


def _make_function_call_response(name, args):
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


def test_get_case_text_invalid_id_returns_error(db_session, seed_cases):
    """get_case_text with a nonexistent ID should return an error dict, not raise."""
    with patch("agent.tools.SessionLocal", return_value=db_session):
        from agent.tools import get_case_text
        result = get_case_text(9999)

    assert "error" in result
    assert "not found" in result["error"].lower()


def test_agent_recovers_from_tool_error(db_session, seed_cases):
    """The agent should handle a tool error observation and continue with other cases."""

    chat_responses = [
        _make_function_call_response("search_cases", {"query": "privacy", "top_k": 3.0}),
        _make_function_call_response("get_case_text", {"case_id": 9999.0}),
        _make_function_call_response("get_case_text", {"case_id": float(seed_cases[0].id)}),
        _make_text_response(
            "# Research Memo\n\nNote: Case ID 9999 was not found in the corpus. "
            f"Analysis continued with available cases. {seed_cases[0].case_name} "
            f"({seed_cases[0].citation}) discusses relevant privacy issues."
        ),
    ]

    mock_chat = MagicMock()
    mock_chat.send_message.side_effect = chat_responses

    mock_chats = MagicMock()
    mock_chats.create.return_value = mock_chat

    mock_search_results = [
        {"case_id": seed_cases[0].id, "chunk_text": "privacy text", "score": 0.9},
    ]

    with patch("agent.loop._client") as mock_client, \
         patch("agent.tools.vector_search", return_value=mock_search_results), \
         patch("agent.tools.SessionLocal", return_value=db_session):

        mock_client.chats = mock_chats

        events = []
        from agent.loop import run_agent
        memo = run_agent("privacy", on_event=lambda e: events.append(e))

    assert memo is not None
    assert "9999" in memo or "not found" in memo.lower()

    tool_results = [e for e in events if e.get("type") == "tool_result"]
    has_error = any(e.get("is_error", False) for e in tool_results)
    assert has_error, "Expected at least one tool error event"

    assert len(tool_results) > 1, "Agent should have continued after error"


def test_validate_citation_invalid(db_session, seed_cases):
    """validate_citation with a nonexistent ID should return valid=False."""
    with patch("agent.tools.SessionLocal", return_value=db_session):
        from agent.tools import validate_citation
        result = validate_citation(9999)

    assert result["valid"] is False
    assert result["citation"] is None
