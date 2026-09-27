"""Day 1 checkpoint: CLI script that runs a research query through the hand-rolled agent.

Usage:
    python agent_cli.py "what cases discuss employee privacy rights"
    python agent_cli.py --demo  # runs the demo with induced failure
"""
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def setup():
    """Initialize DB and embeddings if needed."""
    from seed_data import seed_database
    from embeddings.store import build_index
    seed_database()
    build_index()


def run_demo():
    """Run a demo query that deliberately triggers a failure (bad case_id) to show recovery."""
    from agent.tools import TOOL_DISPATCH, get_case_text

    print("\n" + "=" * 70)
    print("DEMO: Induced failure + recovery")
    print("=" * 70)

    print("\n--- Attempting to get_case_text with invalid case_id=9999 ---")
    result = get_case_text(9999)
    print(f"Result: {json.dumps(result, indent=2)}")
    print("Agent would see this error as a tool observation and skip this case.\n")

    print("--- Now running full agent loop with a real query ---")
    from agent.loop import run_agent

    def log_event(event):
        etype = event.get("type", "unknown")
        if etype == "tool_call":
            print(f"  -> Tool call: {event['tool']}({json.dumps(event['input'])})")
        elif etype == "tool_result":
            is_err = event.get("is_error", False)
            status = "ERROR" if is_err else "OK"
            print(f"  <- Tool result [{status}]: {event['result_preview'][:200]}")
        elif etype == "agent_start":
            print(f"\nAgent starting: {event['query']}")
        elif etype == "agent_done":
            print(f"\nAgent completed in {event['iterations']} iterations.")

    memo = run_agent(
        "What cases discuss digital privacy rights and warrantless searches of electronic devices?",
        on_event=log_event,
    )

    print("\n" + "=" * 70)
    print("RESEARCH MEMO")
    print("=" * 70)
    print(memo)


def run_query(query: str):
    """Run a single research query."""
    from agent.loop import run_agent

    def log_event(event):
        etype = event.get("type", "unknown")
        if etype == "tool_call":
            print(f"  -> {event['tool']}({json.dumps(event['input'])})")
        elif etype == "tool_result":
            is_err = event.get("is_error", False)
            status = "ERROR" if is_err else "OK"
            print(f"  <- [{status}] {event['result_preview'][:200]}")
        elif etype == "agent_start":
            print(f"\nResearching: {event['query']}")
        elif etype == "agent_done":
            print(f"\nDone in {event['iterations']} iterations.\n")

    memo = run_agent(query, on_event=log_event)
    print("=" * 70)
    print("RESEARCH MEMO")
    print("=" * 70)
    print(memo)


if __name__ == "__main__":
    setup()

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo()
    elif len(sys.argv) > 1:
        run_query(sys.argv[1])
    else:
        print("Usage: python agent_cli.py \"your research query\"")
        print("       python agent_cli.py --demo")
