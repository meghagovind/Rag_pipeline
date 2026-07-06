"""Retrieve pgvector chunks and generate cited answers through Ollama."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from llama_index.llms.ollama import Ollama
from sqlalchemy import create_engine, text

from rag.embeddings import get_embed_model
from rag.indexer import _vector_literal

logger = logging.getLogger(__name__)


REFUSAL_PATTERNS = (
    "can't provide personal information",
    "cannot provide personal information",
    "can't assist with",
    "cannot assist with",
    "i can't provide",
    "i cannot provide",
    "is there anything else i can help you with",
)


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
            context_window=2048,
            request_timeout=180.0,
            temperature=0.2,
            additional_kwargs={"num_predict": 160},
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

    @staticmethod
    def _looks_like_refusal(answer: str) -> bool:
        normalized = answer.lower()
        return any(pattern in normalized for pattern in REFUSAL_PATTERNS)

    @staticmethod
    def _extractive_answer(question: str, sources: List[SourceChunk]) -> str:
        """Return a conservative answer directly from retrieved document text.

        This is used when a small local model refuses to summarize user-uploaded
        documents, even though the app is explicitly an authorized document Q&A
        tool. It keeps the answer grounded by using only retrieved lines.
        """
        seen: set[str] = set()
        lines: list[str] = []

        for source in sources:
            for raw_line in source.chunk_text.splitlines():
                line = re.sub(r"\s+", " ", raw_line).strip(" |")
                if not line or len(line) < 3:
                    continue
                key = line.lower()
                if key in seen:
                    continue
                seen.add(key)
                lines.append(line)
                if len(lines) >= 60:
                    break
            if len(lines) >= 60:
                break

        if not lines:
            return (
                "I found matching document context, but it did not contain enough "
                "readable text to answer the question."
            )

        question_lower = question.lower()
        if any(term in question_lower for term in ("complete", "detail", "summary", "summarize")):
            intro = "Here are the details I found in the uploaded document:"
        else:
            intro = "Here is the relevant information I found in the uploaded document:"

        bullet_lines = "\n".join(f"- {line}" for line in lines)
        page_refs = sorted({source.page_number for source in sources})
        pages = ", ".join(str(page) for page in page_refs)
        return f"{intro}\n\n{bullet_lines}\n\nSources: page {pages}."

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
            f"{source.chunk_text[:1200]}"
            for i, source in enumerate(sources, 1)
        )
        prompt = (
            "You are a document extraction assistant inside a private local RAG app. "
            "The user uploaded these documents and is asking you to fetch details from them. "
            "Answer using only the document context. Do not refuse just because the document "
            "contains names, contact details, receipt details, addresses, or masked payment "
            "information. Do not invent or reveal any information that is not present in the "
            "context. If payment data is masked, keep it masked exactly as shown. "
            "Cite page numbers. Be concise and use no more than 180 words.\n\n"
            f"## Context\n\n{context}\n\n## Question\n\n{question}\n\n## Answer\n"
        )

        try:
            answer = self.llm.complete(prompt).text.strip()
        except Exception as exc:
            logger.error("LLM generation failed: %s", exc)
            answer = (
                "Relevant context was found, but Ollama could not generate an answer. "
                "Verify that the configured model is installed."
            )

        if self._looks_like_refusal(answer):
            logger.warning("LLM refused document extraction; using extractive fallback")
            answer = self._extractive_answer(question, sources)

        return RAGResponse(answer=answer, sources=sources)
