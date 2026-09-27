"""Demo test client — exercises the full API flow.

Usage:
    1. Start the API server:  uvicorn main:app --reload
    2. Start the worker:      python worker.py
    3. Run this script:       python test_client.py
"""
import time
import json
import httpx

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "researcher-key-001"
HEADERS = {"X-Api-Key": API_KEY}


def demo_happy_path():
    """Submit a query, poll for completion, and display the report."""
    print("\n" + "=" * 70)
    print("DEMO 1: Happy Path — Submit query and get research report")
    print("=" * 70)

    resp = httpx.post(f"{BASE_URL}/research/query",
                      json={"query_text": "What cases discuss digital privacy and warrantless searches?"},
                      headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    query_id = data["query_id"]
    print(f"\nSubmitted query {query_id}, status: {data['status']}")

    print("\nPolling for completion...")
    for i in range(60):
        time.sleep(3)
        resp = httpx.get(f"{BASE_URL}/research/{query_id}/report", headers=HEADERS)
        resp.raise_for_status()
        report = resp.json()
        status = report["status"]
        print(f"  [{i * 3}s] Status: {status}")

        if status == "completed":
            print("\n--- RESEARCH REPORT ---")
            print(f"Memo:\n{report['memo_text'][:1000]}...")
            print(f"\nCited case IDs: {report['cited_case_ids']}")
            print(f"Cases analyzed: {report['cases_analyzed']}")
            print(f"Cases not analyzed: {report['cases_not_analyzed']}")
            print(f"Findings: {json.dumps(report['findings'], indent=2)[:500]}")
            return query_id

        if status == "failed":
            print(f"\nQuery failed. Findings so far: {report.get('findings')}")
            return query_id

    print("\nTimed out waiting for completion.")
    return query_id


def demo_sse_events(query_id: int = None):
    """Stream events for a query via SSE."""
    if not query_id:
        resp = httpx.post(f"{BASE_URL}/research/query",
                          json={"query_text": "Cases about employee monitoring and workplace privacy"},
                          headers=HEADERS)
        resp.raise_for_status()
        query_id = resp.json()["query_id"]
        print(f"\nSubmitted query {query_id} for SSE demo")

    print("\n" + "=" * 70)
    print(f"DEMO 2: SSE Event Stream for query {query_id}")
    print("=" * 70)
    print("(Connecting to event stream — will show events as they arrive)\n")

    try:
        with httpx.stream("GET", f"{BASE_URL}/research/{query_id}/events",
                          headers=HEADERS, timeout=120) as resp:
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    try:
                        event = json.loads(data)
                        print(f"  Event: {json.dumps(event, indent=2)[:200]}")
                    except json.JSONDecodeError:
                        print(f"  Raw: {data[:200]}")
                elif line.startswith("event:"):
                    event_type = line[6:].strip()
                    print(f"\n[{event_type}]")
                    if event_type == "done":
                        break
    except httpx.ReadTimeout:
        print("Stream timed out.")


def demo_auth_failure():
    """Demonstrate auth rejection with bad API key."""
    print("\n" + "=" * 70)
    print("DEMO 3: Auth failure with bad API key")
    print("=" * 70)

    resp = httpx.post(f"{BASE_URL}/research/query",
                      json={"query_text": "test"},
                      headers={"X-Api-Key": "bad-key-123"})
    print(f"\nStatus: {resp.status_code}")
    print(f"Response: {resp.json()}")


def demo_cancellation():
    """Submit a query and immediately cancel it."""
    print("\n" + "=" * 70)
    print("DEMO 4: Query cancellation")
    print("=" * 70)

    resp = httpx.post(f"{BASE_URL}/research/query",
                      json={"query_text": "Cases about contract law and breach of warranty"},
                      headers=HEADERS)
    resp.raise_for_status()
    query_id = resp.json()["query_id"]
    print(f"\nSubmitted query {query_id}")

    resp = httpx.post(f"{BASE_URL}/research/{query_id}/cancel", headers=HEADERS)
    print(f"Cancel response: {resp.json()}")

    time.sleep(5)
    resp = httpx.get(f"{BASE_URL}/research/{query_id}/report", headers=HEADERS)
    print(f"Final status: {resp.json()['status']}")


if __name__ == "__main__":
    print("Case Law Research System — API Demo Client")
    print("Make sure the API (uvicorn main:app) and worker (python worker.py) are running.\n")

    resp = httpx.get(f"{BASE_URL}/health")
    if resp.status_code != 200:
        print("ERROR: API server not reachable. Start it first.")
        exit(1)
    print("API server is healthy.\n")

    demo_auth_failure()
    query_id = demo_happy_path()
    demo_cancellation()
