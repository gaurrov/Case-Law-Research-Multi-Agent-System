"""FastAPI application entry point."""
from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI

from db.database import engine
from db.models import Base
from api.routes import router as research_router
from seed_data import seed_database
from embeddings.store import build_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    seed_database()
    build_index()
    yield


app = FastAPI(
    title="Case Law Research System",
    description="Multi-agent legal research system over a case-law corpus",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(research_router)


@app.get("/health")
def health():
    return {"status": "ok"}
