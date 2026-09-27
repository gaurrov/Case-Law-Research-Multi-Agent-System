# Case Law Research Multi-Agent System — Architecture Document

## Page 1: Problem Statement & System Overview

### Problem
Legal researchers need to efficiently search, analyze, and synthesize case law across a 
corpus of judicial opinions. Manual review is time-consuming and error-prone — a researcher 
must search for relevant cases, read each one, assess its relevance to the research question, 
and synthesize findings into a coherent memo with proper citations.

This system automates that workflow using an AI agent that orchestrates multiple tools — 
vector search, case retrieval, relevance analysis, and citation validation — to produce 
a research memo with verified citations.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│   curl / test_client.py / Postman                                   │
│   Headers: X-Api-Key: researcher-key-001                            │
└──────────────┬──────────────────────────────────────┬───────────────┘
               │                                      │
               ▼                                      ▼
┌──────────────────────────┐          ┌──────────────────────────────┐
│   FastAPI (main.py)      │          │   SSE Event Stream           │
│                          │          │   GET /research/{id}/events  │
│ POST /research/query     │          │                              │
│ GET  /research/{id}/report│         │   Polls agent_events table   │
│ POST /research/{id}/cancel│         │   and streams to client      │
└──────────┬───────────────┘          └──────────────────────────────┘
           │ inserts queued row
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        SQLite DATABASE                               │
│                                                                      │
│  cases_corpus          research_queries       case_findings          │
│  ┌──────────┐          ┌──────────────┐       ┌─────────────┐       │
│  │ id       │          │ id           │       │ id          │       │
│  │ case_name│          │ user_id      │       │ query_id FK │       │
│  │ citation │          │ query_text   │       │ case_id FK  │       │
│  │ court    │          │ status       │       │ relevance_* │       │
│  │ date     │          │ heartbeat_at │       │ status      │       │
│  │ full_text│          │ retry_count  │       │ idempot_key │       │
│  │ summary  │          │ cancel_req   │       └─────────────┘       │
│  └──────────┘          └──────────────┘                              │
│                                                                      │
│  research_reports      agent_events           case_embeddings        │
│  ┌──────────────┐      ┌──────────────┐       ┌──────────────┐      │
│  │ id           │      │ id           │       │ id           │      │
│  │ query_id FK  │      │ query_id FK  │       │ case_id FK   │      │
│  │ memo_text    │      │ event_type   │       │ chunk_text   │      │
│  │ cited_cases  │      │ tool_name    │       │ chroma_id    │      │
│  │ analyzed     │      │ tool_input   │       └──────────────┘      │
│  │ not_analyzed │      │ tool_output  │                              │
│  └──────────────┘      └──────────────┘                              │
└──────────────────────────────────────────────────────────────────────┘
           ▲
           │ polls for queued jobs
           │
┌──────────────────────────────────────────────────────────────────────┐
│                        WORKER (worker.py)                            │
│                                                                      │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐     │
│  │ Poll Loop   │───>│ Process Query│───>│ Agent Loop          │     │
│  │ (2s cycle)  │    │ set running  │    │ (model->tool->obs)  │     │
│  └─────────────┘    └──────────────┘    └─────────┬───────────┘     │
│         │                                         │                  │
│  ┌──────▼──────┐    ┌──────────────┐    ┌─────────▼───────────┐     │
│  │ Reaper      │    │ Heartbeat    │    │ Gemini API       │     │
│  │ (stuck jobs)│    │ Thread (5s)  │    │ (gemini-2.0-flash)  │     │
│  └─────────────┘    └──────────────┘    └─────────────────────┘     │
│                                                                      │
│  Durable execution features:                                         │
│  • Heartbeat thread (5s interval)                                    │
│  • Reaper marks stale jobs failed/requeued (30s timeout)             │
│  • Idempotency keys prevent duplicate analysis                       │
│  • Cancellation checked between tool calls                           │
│  • Dead-letter: 2 retries then permanent failure                     │
└──────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     VECTOR STORE (Chroma)                            │
│                                                                      │
│  Local file-based Chroma DB (./chroma_data/)                         │
│  Embedding model: all-MiniLM-L6-v2 (sentence-transformers)          │
│  Indexed: case text chunks (500 words, 100 word overlap)             │
│  Search: cosine similarity                                           │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Page 2: API Design & Database Schema

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/research/query` | API key | Submit a research query. Returns `{query_id, status: "queued"}` immediately. |
| GET | `/research/{id}/report` | API key | Get current status + report (memo, citations, findings) if ready. |
| GET | `/research/{id}/events` | API key | Stream agent tool events via SSE as they happen. |
| POST | `/research/{id}/cancel` | API key | Request cancellation of a running query. |
| GET | `/health` | None | Health check. |

### Authentication
Static API key mapping in `config.yaml`. Header: `X-Api-Key`. Each key maps to a `user_id`. 
Queries are scoped by `user_id` — users can only see their own queries.

### Request Flow (POST /research/query)

```
Client                  API                    DB                  Worker
  │                      │                      │                    │
  │──POST /query────────>│                      │                    │
  │                      │──INSERT queued───────>│                    │
  │<──{query_id, queued}─│                      │                    │
  │                      │                      │<──poll (2s)────────│
  │                      │                      │──queued row───────>│
  │                      │                      │<──set running──────│
  │                      │                      │<──heartbeat (5s)───│
  │                      │                      │<──agent_event──────│
  │                      │                      │<──case_finding─────│
  │                      │                      │<──agent_event──────│
  │                      │                      │<──report + done────│
  │──GET /report────────>│                      │                    │
  │                      │──SELECT──────────────>│                    │
  │<──{memo, citations}──│                      │                    │
```

### Database Schema Details

**cases_corpus**: The seed corpus of 18 synthetic legal cases spanning privacy law, 
employment law, environmental law, Fair Housing Act, constitutional law, and more.

**case_embeddings**: Mapping table linking each text chunk to its Chroma vector ID. 
Chunks are ~500 words with 100-word overlap. This table proves "citations validated 
against corpus" — every cited case_id can be traced back to a real corpus entry.

**research_queries**: The job queue. Status flow: `queued → running → completed|failed`. 
`heartbeat_at` is updated every 5 seconds while running. `cancel_requested` is checked 
between tool calls.

**case_findings**: Per-case analysis results. `idempotency_key` = `query_id:case_id:tool_name` 
prevents duplicate analysis on retry. `retry_count` tracks failures; after 2 retries, 
status is set to `failed` (dead-letter).

**research_reports**: Final output. `cited_case_ids` contains only cases that were 
successfully analyzed. `cases_not_analyzed` transparently lists failures/timeouts.

---

## Page 3: Agent & LangGraph Flow

### Day 1: Hand-Rolled Agent Loop (agent/loop.py)

The agent loop follows a simple pattern:
1. Send the query to Gemini with available tool schemas
2. If Gemini returns function_call parts, execute each tool
3. Pass tool results back as observations
4. Repeat until Gemini returns a text response with no function calls (the final memo)

Tools:
- `search_cases(query, top_k)` — cosine similarity search over Chroma embeddings
- `get_case_text(case_id)` — retrieve full case text from SQLite
- `analyze_relevance(case_id, query)` — LLM-powered relevance scoring
- `validate_citation(case_id)` — verify case exists in corpus

Error handling: tool errors are returned as observations ("case not found"), not exceptions. 
The agent sees the error and adapts (skips bad cases, tries alternatives).

### Day 4: LangChain LCEL Chains (chains/)

Three LCEL chains replace the raw tool logic:
- **Retrieval chain**: LangChain Chroma wrapper → deduplicated candidate list
- **Analysis chain**: ChatPromptTemplate → ChatGoogleGenerativeAI → Pydantic CaseAnalysis output
- **Synthesis chain**: ChatPromptTemplate → ChatGoogleGenerativeAI → StrOutputParser → memo text

The orchestrator (`chains/orchestrator.py`) ties them together:
1. Retrieve candidates
2. Fan out analysis with `asyncio.gather` + `Semaphore(3)` for bounded concurrency
3. Each analysis task has `asyncio.wait_for` timeout
4. Merge: classify results as analyzed vs. timed_out/failed
5. Synthesize: only pass analyzed cases to the memo chain

### Day 5: LangGraph Graph (graph/research_graph.py)

```
    START
      │
      ▼
  ┌──────────┐
  │ retrieve  │  retrieve_candidates() → list of case_ids
  └────┬─────┘
       │
       ▼ (conditional edges via Send API)
  ┌────────────────────────────────────────┐
  │  analyze_case_node  (parallel, one per │
  │  candidate via Send)                   │
  │                                        │
  │  Case 1 ─┐                            │
  │  Case 2 ─┼─→ each runs analyze_case() │
  │  Case 3 ─┤   with timeout handling    │
  │  Case N ─┘                            │
  └────────────────────┬───────────────────┘
                       │ (results aggregated via operator.add)
                       ▼
                 ┌───────────┐
                 │   merge   │  Split results → analyzed / not_analyzed
                 └─────┬─────┘
                       │
                       ▼
                 ┌─────────────┐
                 │ synthesize  │  Build memo from analyzed cases only
                 └─────┬───────┘  Cite only verified cases
                       │
                       ▼
                 ┌──────────┐
                 │   save   │  Persist to DB (findings + report)
                 └────┬─────┘
                      │
                      ▼
                     END
```

**Fan-out**: Uses LangGraph's `Send` API — `route_to_analyses()` returns a list of 
`Send("analyze_case_node", {case_data})` messages, one per candidate. LangGraph 
executes them in parallel.

**Merge**: Results are aggregated into `case_results` via `Annotated[list, operator.add]`. 
The merge node classifies each result by status.

**Citation integrity**: The synthesize node only passes cases with `status="analyzed"` 
and `relevance_score >= threshold` to the synthesis chain. The synthesis prompt explicitly 
instructs the LLM not to cite cases from the not_analyzed list.

**Timeout handling**: Each analysis node catches exceptions. If analysis times out or 
errors, the result is marked with `status="failed"` or `status="timed_out"` and routed 
to `cases_not_analyzed` — it never silently vanishes.
