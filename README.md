# Case Law Research Multi-Agent System

A multi-agent legal research system that searches, analyzes, and synthesizes case law into research memos with verified citations. Built as a 5-day learning project covering agent fundamentals, async APIs, durable execution, LangChain, and LangGraph.

## Architecture

```
Client → FastAPI → SQLite (job queue) → Worker → Agent Loop → Gemini API
                                                      ↕
                                              Chroma (vector search)
```

See [docs/architecture.md](docs/architecture.md) for the full 3-page architecture document.

## Setup

### Prerequisites
- Python 3.11+
- A Google Gemini API key

### Installation

```bash
# Clone and enter the project
cd Case-Law-Research-Multi-Agent-System

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Set your API key
export GOOGLE_API_KEY="your-key-here"
# set GOOGLE_API_KEY=your-key-here       # Windows cmd
# $env:GOOGLE_API_KEY="your-key-here"    # Windows PowerShell
```

### Seed the Database & Build Embeddings

```bash
python seed_data.py
python -c "from embeddings.store import build_index; build_index()"
```

This creates `case_law.db` (SQLite) with 18 synthetic legal cases and `chroma_data/` with vector embeddings.

## Running

### Day 1: Agent CLI (no server needed)

```bash
python agent_cli.py "what cases discuss employee privacy rights"
python agent_cli.py --demo    # shows induced failure + recovery
```

### Day 2-5: API Server + Worker

**Terminal 1 — API server:**
```bash
uvicorn main:app --reload
```

**Terminal 2 — Background worker:**
```bash
python worker.py
```

**Terminal 3 — Test client:**
```bash
python test_client.py
```

Or use curl:
```bash
# Submit a query
curl -X POST http://127.0.0.1:8000/research/query \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: researcher-key-001" \
  -d '{"query_text": "cases about digital privacy and warrantless searches"}'

# Check status / get report
curl http://127.0.0.1:8000/research/1/report \
  -H "X-Api-Key: researcher-key-001"

# Stream events (SSE)
curl http://127.0.0.1:8000/research/1/events \
  -H "X-Api-Key: researcher-key-001"

# Cancel a query
curl -X POST http://127.0.0.1:8000/research/1/cancel \
  -H "X-Api-Key: researcher-key-001"
```

## Running Tests

```bash
pytest tests/ -v
```

Tests cover:
1. **Happy path**: Query retrieves cases and produces a memo with valid citations
2. **Failure recovery**: Agent handles bad case_id and continues with other cases
3. **Timeout edge case**: One case analysis times out; memo reports it honestly

## Project Structure

```
├── main.py                 # FastAPI app entry point
├── worker.py               # Background worker with durable execution
├── agent_cli.py            # Day 1 CLI agent demo
├── test_client.py          # API demo client
├── seed_data.py            # Seeds 18 synthetic legal cases
├── config.yaml             # All configuration (thresholds, timeouts, etc.)
├── agent/
│   ├── loop.py             # Hand-rolled agent loop (Day 1)
│   └── tools.py            # Tool functions + schemas
├── api/
│   ├── auth.py             # API key authentication
│   └── routes.py           # FastAPI routes + SSE streaming
├── chains/
│   ├── retrieval.py        # LangChain vector retrieval (Day 4)
│   ├── analysis.py         # LCEL per-case analysis chain
│   ├── synthesis.py        # LCEL memo synthesis chain
│   └── orchestrator.py     # Fan-out orchestrator with timeouts
├── graph/
│   └── research_graph.py   # LangGraph graph definition (Day 5)
├── db/
│   ├── database.py         # SQLAlchemy engine + session
│   └── models.py           # All SQLAlchemy models
├── embeddings/
│   └── store.py            # Chroma vector store
├── tests/
│   ├── conftest.py         # Test fixtures
│   ├── test_happy_path.py
│   ├── test_failure_recovery.py
│   └── test_timeout.py
└── docs/
    └── architecture.md     # 3-page architecture document
```

## Key Design Decisions

- **SQLite + Chroma on disk**: No external services needed. One `case_law.db` file and a `chroma_data/` directory.
- **DB-backed job queue**: `research_queries` table with status column acts as the queue. No Celery/Redis.
- **Heartbeat + reaper**: Worker sends heartbeats every 5s. A reaper marks jobs as failed if heartbeat is stale for 30s.
- **Idempotency keys**: `query_id:case_id:tool_name` prevents duplicate analysis on retry.
- **Citation integrity**: The LangGraph synthesize node only passes analyzed cases to the LLM. The prompt explicitly forbids citing cases from the not_analyzed list.
- **Transparent failures**: Timed-out or failed cases appear in `cases_not_analyzed`, never silently dropped.

## Configuration

All tunable parameters are in `config.yaml`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `retrieval.top_k` | 5 | Number of candidate cases to retrieve |
| `retrieval.relevance_threshold` | 0.4 | Minimum score to include in memo |
| `analysis.max_concurrency` | 3 | Parallel analysis tasks |
| `analysis.per_task_timeout_seconds` | 30 | Timeout per case analysis |
| `worker.heartbeat_interval_seconds` | 5 | Heartbeat frequency |
| `worker.heartbeat_timeout_seconds` | 30 | Reaper threshold |
| `worker.max_retries` | 2 | Dead-letter after N failures |

## Auth

Static API keys in `config.yaml`:
- `researcher-key-001` → `user_1`
- `researcher-key-002` → `user_2`

Pass via `X-Api-Key` header. Users can only see their own queries.
