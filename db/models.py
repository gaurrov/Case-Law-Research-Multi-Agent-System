import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class CaseCorpus(Base):
    __tablename__ = "cases_corpus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_name = Column(String(500), nullable=False)
    citation = Column(String(200), nullable=False, unique=True)
    court = Column(String(200), nullable=False)
    date = Column(String(50), nullable=False)
    full_text = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)

    embeddings = relationship("CaseEmbedding", back_populates="case")
    findings = relationship("CaseFinding", back_populates="case")


class CaseEmbedding(Base):
    __tablename__ = "case_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases_corpus.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chroma_id = Column(String(200), nullable=True)

    case = relationship("CaseCorpus", back_populates="embeddings")


class ResearchQuery(Base):
    __tablename__ = "research_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False)
    query_text = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="queued")
    heartbeat_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    cancel_requested = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    findings = relationship("CaseFinding", back_populates="query")
    reports = relationship("ResearchReport", back_populates="query")
    events = relationship("AgentEvent", back_populates="query")


class CaseFinding(Base):
    __tablename__ = "case_findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("research_queries.id"), nullable=False)
    case_id = Column(Integer, ForeignKey("cases_corpus.id"), nullable=False)
    relevance_score = Column(Float, nullable=True)
    relevance_note = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    idempotency_key = Column(String(500), nullable=True, unique=True)
    retry_count = Column(Integer, nullable=False, default=0)

    query = relationship("ResearchQuery", back_populates="findings")
    case = relationship("CaseCorpus", back_populates="findings")


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("research_queries.id"), nullable=False)
    memo_text = Column(Text, nullable=False)
    cited_case_ids = Column(JSON, nullable=False, default=list)
    cases_analyzed = Column(JSON, nullable=False, default=list)
    cases_not_analyzed = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    query = relationship("ResearchQuery", back_populates="reports")


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("research_queries.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    tool_name = Column(String(100), nullable=True)
    tool_input = Column(JSON, nullable=True)
    tool_output = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    query = relationship("ResearchQuery", back_populates="events")
