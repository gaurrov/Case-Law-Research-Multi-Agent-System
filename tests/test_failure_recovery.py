"""Test 2: Failure + recovery — agent handles bad case_id and continues."""
from unittest.mock import patch, MagicMock
from db.models import CaseCorpus


def test_get_case_text_invalid_id_returns_error(db_session, seed_cases):
    """get_case_text with a nonexistent ID should return an error dict, not raise."""
    with patch("agent.tools.SessionLocal", return_value=db_session):
        from agent.tools import get_case_text
        result = get_case_text(9999)

    assert "error" in result
    assert "not found" in result["error"].lower()


def test_agent_recovers_from_tool_error(db_session, seed_cases):
    """The agent should handle a tool error observation and continue with other cases."""

    tool_call_sequence = [
        # First: agent searches
        MagicMock(
            stop_reason="tool_use",
            content=[
                MagicMock(type="tool_use", name="search_cases", id="tc1",
                          input={"query": "privacy", "top_k": 3}),
            ],
        ),
        # Second: agent tries to get a case with bad ID (induced failure)
        MagicMock(
            stop_reason="tool_use",
            content=[
                MagicMock(type="tool_use", name="get_case_text", id="tc2",
                          input={"case_id": 9999}),
            ],
        ),
        # Third: agent recovers and tries a valid case
        MagicMock(
            stop_reason="tool_use",
            content=[
                MagicMock(type="tool_use", name="get_case_text", id="tc3",
                          input={"case_id": seed_cases[0].id}),
            ],
        ),
        # Fourth: agent produces memo acknowledging the failure
        MagicMock(
            stop_reason="end_turn",
            content=[
                MagicMock(type="text",
                          text="# Research Memo\n\nNote: Case ID 9999 was not found in the corpus. "
                               f"Analysis continued with available cases. {seed_cases[0].case_name} "
                               f"({seed_cases[0].citation}) discusses relevant privacy issues."),
            ],
        ),
    ]

    mock_search_results = [
        {"case_id": seed_cases[0].id, "chunk_text": "privacy text", "score": 0.9},
    ]

    with patch("agent.loop._client") as mock_client, \
         patch("agent.tools.vector_search", return_value=mock_search_results), \
         patch("agent.tools.SessionLocal", return_value=db_session):

        mock_client.messages.create.side_effect = tool_call_sequence

        events = []
        from agent.loop import run_agent
        memo = run_agent("privacy", on_event=lambda e: events.append(e))

    assert memo is not None
    assert "9999" in memo or "not found" in memo.lower()

    tool_results = [e for e in events if e.get("type") == "tool_result"]
    has_error = any(e.get("is_error", False) for e in tool_results)
    assert has_error, "Expected at least one tool error event"

    assert "end_turn" not in str(events[1]) or len(tool_results) > 1, \
        "Agent should have continued after error"


def test_validate_citation_invalid(db_session, seed_cases):
    """validate_citation with a nonexistent ID should return valid=False."""
    with patch("agent.tools.SessionLocal", return_value=db_session):
        from agent.tools import validate_citation
        result = validate_citation(9999)

    assert result["valid"] is False
    assert result["citation"] is None
