"""FastAPI routes for the research API."""
import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from db.database import get_db
from db.models import ResearchQuery, ResearchReport, AgentEvent, CaseFinding
from api.auth import get_current_user

router = APIRouter(prefix="/research", tags=["research"])


class QueryRequest(BaseModel):
    query_text: str


class QueryResponse(BaseModel):
    query_id: int
    status: str


class ReportResponse(BaseModel):
    query_id: int
    status: str
    memo_text: str | None = None
    cited_case_ids: list[int] | None = None
    cases_analyzed: list[int] | None = None
    cases_not_analyzed: list[int] | None = None
    findings: list[dict] | None = None
    created_at: str | None = None


@router.post("/query", response_model=QueryResponse)
def submit_query(
    req: QueryRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = ResearchQuery(
        user_id=user_id,
        query_text=req.query_text,
        status="queued",
    )
    db.add(query)
    db.commit()
    db.refresh(query)
    return QueryResponse(query_id=query.id, status=query.status)


@router.get("/{query_id}/report", response_model=ReportResponse)
def get_report(
    query_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ResearchQuery).filter_by(id=query_id, user_id=user_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    report = db.query(ResearchReport).filter_by(query_id=query_id).first()
    findings = db.query(CaseFinding).filter_by(query_id=query_id).all()

    findings_list = [
        {
            "case_id": f.case_id,
            "relevance_score": f.relevance_score,
            "relevance_note": f.relevance_note,
            "status": f.status,
        }
        for f in findings
    ]

    return ReportResponse(
        query_id=query_id,
        status=query.status,
        memo_text=report.memo_text if report else None,
        cited_case_ids=report.cited_case_ids if report else None,
        cases_analyzed=report.cases_analyzed if report else None,
        cases_not_analyzed=report.cases_not_analyzed if report else None,
        findings=findings_list if findings else None,
        created_at=report.created_at.isoformat() if report else None,
    )


@router.get("/{query_id}/events")
async def stream_events(
    query_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ResearchQuery).filter_by(id=query_id, user_id=user_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    async def event_generator():
        last_event_id = 0
        while True:
            fresh_db = next(get_db())
            try:
                events = (
                    fresh_db.query(AgentEvent)
                    .filter(AgentEvent.query_id == query_id, AgentEvent.id > last_event_id)
                    .order_by(AgentEvent.id)
                    .all()
                )

                for event in events:
                    last_event_id = event.id
                    yield {
                        "event": event.event_type,
                        "data": json.dumps({
                            "id": event.id,
                            "tool_name": event.tool_name,
                            "tool_input": event.tool_input,
                            "tool_output": event.tool_output,
                            "error": event.error,
                            "created_at": event.created_at.isoformat(),
                        }),
                    }

                q = fresh_db.get(ResearchQuery, query_id)
                if q and q.status in ("completed", "failed"):
                    yield {"event": "done", "data": json.dumps({"status": q.status})}
                    return
            finally:
                fresh_db.close()

            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@router.post("/{query_id}/cancel")
def cancel_query(
    query_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ResearchQuery).filter_by(id=query_id, user_id=user_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    if query.status not in ("queued", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel query in state: {query.status}")
    query.cancel_requested = 1
    db.commit()
    return {"query_id": query_id, "cancel_requested": True}
