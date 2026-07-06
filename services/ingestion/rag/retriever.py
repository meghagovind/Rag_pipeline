"""Retrieve pgvector chunks and generate cited answers through Ollama."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

from llama_index.llms.ollama import Ollama
from sqlalchemy import create_engine, text

from rag.embeddings import get_embed_model
from rag.indexer import _vector_literal

logger = logging.getLogger(__name__)


@dataclass
class SourceChunk:
    chunk_text: str
    page_number: int
    document_id: str
    filename: str
    score: float = 0.0


@dataclass
class RAGResponse:
    answer: str
    sources: List[SourceChunk] = field(default_factory=list)


class Retriever:
    """Perform cosine similarity search against the application chunk table."""

    def __init__(self) -> None:
        self.embed_model = get_embed_model()
        self.engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
        self.llm = Ollama(
            model=os.getenv("LLM_MODEL", "mistral"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            request_timeout=120.0,
        )

    def retrieve(
        self,
        query: str,
        document_id: Optional[str] = None,
        top_k: int = 8,
    ) -> List[SourceChunk]:
        embedding = _vector_literal(self.embed_model.get_query_embedding(query))
        document_clause = (
            "AND c.document_id = CAST(:document_id AS uuid)" if document_id else ""
        )
        statement = text(
            "SELECT c.chunk_text, c.page_number, c.document_id, d.filename, "
            "1 - (c.embedding <=> CAST(:embedding AS vector)) AS score "
            "FROM document_chunks c "
            "JOIN documents d ON d.id = c.document_id "
            "WHERE c.embedding IS NOT NULL "
            f"{document_clause} "
            "ORDER BY c.embedding <=> CAST(:embedding AS vector) "
            "LIMIT :top_k"
        )
        params = {
            "embedding": embedding,
            "document_id": document_id,
            "top_k": max(1, min(top_k, 50)),
        }

        with self.engine.connect() as connection:
            rows = connection.execute(statement, params).mappings().all()

        return [
            SourceChunk(
                chunk_text=row["chunk_text"],
                page_number=row["page_number"],
                document_id=str(row["document_id"]),
                filename=row["filename"],
                score=float(row["score"] or 0.0),
            )
            for row in rows
        ]

    def query(
        self,
        question: str,
        document_id: Optional[str] = None,
        top_k: int = 8,
    ) -> RAGResponse:
        sources = self.retrieve(question, document_id=document_id, top_k=top_k)
        if not sources:
            return RAGResponse(
                answer="I couldn't find any relevant information in the uploaded documents."
            )

        context = "\n\n---\n\n".join(
            f"[Source {i} — {source.filename}, Page {source.page_number}]\n"
            f"{source.chunk_text}"
            for i, source in enumerate(sources, 1)
        )
        prompt = (
            "Answer the question using only the document context. Cite page numbers.\n\n"
            f"## Context\n\n{context}\n\n## Question\n\n{question}\n\n## Answer\n"
        )

        try:
            answer = self.llm.complete(prompt).text
        except Exception as exc:
            logger.error("LLM generation failed: %s", exc)
            answer = (
                "Relevant context was found, but Ollama could not generate an answer. "
                "Verify that the configured model is installed."
            )

        return RAGResponse(answer=answer, sources=sources)
