"""Chunk documents, create embeddings, and store them in pgvector."""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, List

from llama_index.core import Document as LIDocument
from llama_index.core.node_parser import SentenceSplitter
from sqlalchemy import create_engine, text

from rag.embeddings import get_embed_model

logger = logging.getLogger(__name__)


def _vector_literal(values: List[float]) -> str:
    """Serialize a vector for PostgreSQL's vector input format."""
    return "[" + ",".join(f"{value:.9g}" for value in values) + "]"


class Indexer:
    """Create 384-dimensional chunks in the Prisma-managed chunk table."""

    def __init__(self) -> None:
        self.embed_model = get_embed_model()
        self.splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        self.engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

    def index_document(
        self,
        document_id: str,
        filename: str,
        pages: List[Dict[str, Any]],
    ) -> int:
        chunks: list[dict[str, Any]] = []

        for page in pages:
            page_number = page["page_number"]
            content = page.get("markdown") or page.get("raw_text", "")
            if page.get("tables_markdown"):
                content = f"{content}\n\n{page['tables_markdown']}"
            if not content.strip():
                continue

            document = LIDocument(text=content)
            for node in self.splitter.get_nodes_from_documents([document]):
                chunks.append(
                    {
                        "text": node.get_content(),
                        "page_number": page_number,
                        "metadata": {
                            "document_id": document_id,
                            "page_number": page_number,
                            "filename": filename,
                        },
                    }
                )

        if not chunks:
            logger.warning("No chunks produced for document %s", document_id)
            return 0

        embeddings = self.embed_model.get_text_embedding_batch(
            [chunk["text"] for chunk in chunks]
        )

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "DELETE FROM document_chunks "
                    "WHERE document_id = CAST(:document_id AS uuid)"
                ),
                {"document_id": document_id},
            )
            for chunk, embedding in zip(chunks, embeddings):
                connection.execute(
                    text(
                        "INSERT INTO document_chunks "
                        "(id, document_id, page_number, chunk_text, metadata, embedding) "
                        "VALUES (CAST(:id AS uuid), CAST(:document_id AS uuid), "
                        ":page_number, :chunk_text, CAST(:metadata AS jsonb), "
                        "CAST(:embedding AS vector))"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "document_id": document_id,
                        "page_number": chunk["page_number"],
                        "chunk_text": chunk["text"],
                        "metadata": json.dumps(chunk["metadata"]),
                        "embedding": _vector_literal(embedding),
                    },
                )

        logger.info("Indexed %d chunks for document %s", len(chunks), document_id)
        return len(chunks)
