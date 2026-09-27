"""Test 3: Timeout edge case — one case analysis times out, memo reports it honestly."""
import asyncio
import time
from unittest.mock import patch, MagicMock
from chains.analysis import CaseAnalysis


def _slow_analyze(case_data, query):
    """Simulates a slow analysis that will exceed the timeout."""
    time.sleep(10)
    return CaseAnalysis(relevance_score=0.5, relevance_note="This should never be seen")


def test_timeout_case_reported_in_not_analyzed():
    """When one case times out, it should appear in not_analyzed, not crash the run."""
    case_data_1 = {
        "case_id": 1, "case_name": "Normal Case", "citation": "100 F.3d 100",
        "court": "Test", "date": "2020-01-01", "summary": "Normal",
        "full_text": "Normal case text about privacy rights.",
    }
    case_data_2 = {
        "case_id": 2, "case_name": "Slow Case", "citation": "200 F.3d 200",
        "court": "Test", "date": "2021-01-01", "summary": "Slow",
        "full_text": "This case will time out during analysis.",
    }

    call_count = {"n": 0}
    def mock_analyze(case_data, query):
        call_count["n"] += 1
        if case_data["case_id"] == 2:
            time.sleep(10)
        return CaseAnalysis(relevance_score=0.9, relevance_note="Relevant to query")

    mock_candidates = [
        {"case_id": 1, "snippet": "snippet 1", "retrieval_score": 0.9},
        {"case_id": 2, "snippet": "snippet 2", "retrieval_score": 0.8},
    ]

    with patch("chains.orchestrator.retrieve_candidates", return_value=mock_candidates), \
         patch("chains.orchestrator._get_case_data") as mock_get, \
         patch("chains.orchestrator.analyze_case", side_effect=mock_analyze), \
         patch("chains.orchestrator.synthesize_memo") as mock_synth, \
         patch("chains.orchestrator.PER_TASK_TIMEOUT", 2):

        mock_get.side_effect = lambda cid: case_data_1 if cid == 1 else case_data_2
        mock_synth.return_value = "Memo: Case 1 analyzed. Case 2 could not be fully analyzed (timed out)."

        from chains.orchestrator import run_research
        result = asyncio.run(run_research("privacy rights"))

    assert 2 in result["cases_not_analyzed"], \
        f"Timed-out case should be in cases_not_analyzed, got {result['cases_not_analyzed']}"
    assert 1 in result["cases_analyzed"], \
        f"Normal case should be in cases_analyzed, got {result['cases_analyzed']}"
    assert "timed out" in result["memo"].lower() or "not" in result["memo"].lower(), \
        "Memo should mention the timeout/not-analyzed case"

    synth_args = mock_synth.call_args
    not_analyzed_arg = synth_args[0][2] if len(synth_args[0]) > 2 else synth_args[1].get("not_analyzed", [])
    not_analyzed_ids = [na.get("case_id") for na in not_analyzed_arg]
    assert 2 in not_analyzed_ids, "Timed-out case should be passed to synthesis as not_analyzed"
