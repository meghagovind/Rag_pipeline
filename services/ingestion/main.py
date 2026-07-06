"""
FastAPI Ingestion Service — exposes /ingest and /health endpoints.
Runs heavy document parsing outside Vercel serverless functions.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

# Both services share the repository-level environment file.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from ingest import run_ingestion

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Ingestion service starting up …")
    yield
    logger.info("Ingestion service shutting down …")


# ── App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Document RAG Ingestion Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Models ────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    """Payload for triggering document ingestion."""

    document_id: str
    filename: str
    file_url: str


class IngestResponse(BaseModel):
    """Response after triggering ingestion."""

    document_id: str
    status: str
    message: str


class QueryRequest(BaseModel):
    """Payload for querying the RAG pipeline."""

    question: str
    document_id: Optional[str] = None
    top_k: int = 4


class QueryResponse(BaseModel):
    """Response from the RAG query."""

    answer: str
    sources: list


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str


@lru_cache(maxsize=1)
def get_retriever():
    """Keep the embedding model, database pool, and Ollama client warm."""
    from rag.retriever import Retriever

    return Retriever()


# ── Routes ────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="ingestion",
        version="1.0.0",
    )


@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger document ingestion. The heavy parsing runs as a background task
    so the HTTP response returns immediately.
    """
    logger.info(
        "Ingestion requested for document %s (%s)",
        request.document_id,
        request.filename,
    )

    background_tasks.add_task(
        run_ingestion,
        document_id=request.document_id,
        filename=request.filename,
        file_url=request.file_url,
    )

    return IngestResponse(
        document_id=request.document_id,
        status="PROCESSING",
        message="Ingestion started in background",
    )


@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query the RAG pipeline: retrieve similar chunks and generate an answer.
    """
    try:
        retriever = get_retriever()
        result = retriever.query(
            question=request.question,
            document_id=request.document_id,
            top_k=request.top_k,
        )

        sources = [
            {
                "chunk_text": s.chunk_text[:500],
                "page_number": s.page_number,
                "document_id": s.document_id,
                "filename": s.filename,
                "score": round(s.score, 4),
            }
            for s in result.sources
        ]

        return QueryResponse(answer=result.answer, sources=sources)
    except Exception as exc:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
