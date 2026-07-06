"""
Ingestion Orchestrator — coordinates the full document ingestion pipeline:
  1. Download file
  2. PDF text extraction
  3. OCR (if needed)
  4. Layout analysis → Markdown
  5. Table / form extraction
  6. Chunking + embedding via LlamaIndex
  7. Storage in Neon Postgres (pgvector)
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
import json
from pathlib import Path
from typing import Any, Dict, List

import httpx

from parsers.form_parser import FormParser
from parsers.layout_parser import LayoutParser
from parsers.ocr_parser import OCRParser
from parsers.pdf_parser import PDFParser
logger = logging.getLogger(__name__)


def _update_status(document_id: str, status: str, error: str | None = None) -> None:
    """Keep the document and its latest ingestion job in sync."""
    from sqlalchemy import create_engine, text

    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    completed = status in {"COMPLETED", "FAILED"}
    with engine.begin() as connection:
        connection.execute(
            text(
                'UPDATE documents SET status = CAST(:status AS "JobStatus") '
                "WHERE id = CAST(:document_id AS uuid)"
            ),
            {"status": status, "document_id": document_id},
        )
        connection.execute(
            text(
                'UPDATE ingestion_jobs SET status = CAST(:status AS "JobStatus"), '
                "error = :error, completed_at = CASE WHEN :completed "
                "THEN CURRENT_TIMESTAMP ELSE NULL END "
                "WHERE id = (SELECT id FROM ingestion_jobs "
                "WHERE document_id = CAST(:document_id AS uuid) "
                "ORDER BY created_at DESC LIMIT 1)"
            ),
            {
                "status": status,
                "error": error,
                "completed": completed,
                "document_id": document_id,
            },
        )
    engine.dispose()


def _replace_pages(document_id: str, pages: List[Dict[str, Any]]) -> None:
    """Persist parsed pages used to produce the vector index."""
    from sqlalchemy import create_engine, text

    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM document_pages WHERE document_id = CAST(:id AS uuid)"),
            {"id": document_id},
        )
        for page in pages:
            connection.execute(
                text(
                    "INSERT INTO document_pages "
                    "(id, document_id, page_number, raw_text, markdown, layout_json) "
                    "VALUES (CAST(:id AS uuid), CAST(:document_id AS uuid), "
                    ":page_number, :raw_text, :markdown, CAST(:layout_json AS jsonb))"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "page_number": page["page_number"],
                    "raw_text": page["raw_text"],
                    "markdown": page["markdown"],
                    "layout_json": json.dumps(page["layout_json"]),
                },
            )
    engine.dispose()


async def run_ingestion(
    document_id: str,
    filename: str,
    file_url: str,
    db_update_callback=None,
) -> Dict[str, Any]:
    """
    Run the full ingestion pipeline for a single document.

    Args:
        document_id: UUID of the document row.
        filename: Original filename.
        file_url: URL to download the file from (Vercel Blob / S3).
        db_update_callback: Optional async callable(document_id, status, error)
                            to update the ingestion job row.

    Returns:
        Dict with ingestion results and stats.
    """
    logger.info("Starting ingestion for document %s (%s)", document_id, filename)

    try:
        if db_update_callback:
            await db_update_callback(document_id, "PROCESSING", None)
        else:
            _update_status(document_id, "PROCESSING")

        # 1. Download file to a temp location
        file_path = await _download_file(file_url, filename)
        logger.info("Downloaded file to %s", file_path)

        # 2. PDF text extraction
        pdf_parser = PDFParser()
        page_results = pdf_parser.parse(file_path)
        logger.info("Extracted %d pages from PDF", len(page_results))

        # 3. OCR — run on pages with very little text (likely scanned)
        ocr_parser = OCRParser()
        for page in page_results:
            if len(page.raw_text.strip()) < 50:
                ocr_results = ocr_parser.ocr_pdf(file_path)
                for ocr_page in ocr_results:
                    # Merge OCR text into pages with missing text
                    matching = [
                        p
                        for p in page_results
                        if p.page_number == ocr_page.page_number
                    ]
                    if matching and len(matching[0].raw_text.strip()) < 50:
                        matching[0].raw_text = ocr_page.ocr_text
                break  # Only run OCR once for the whole document

        # 4. Layout analysis — convert raw text to Markdown
        layout_parser = LayoutParser()
        parsed_pages: List[Dict[str, Any]] = []
        for page in page_results:
            layout = layout_parser.parse_page(page.raw_text, page.page_number)
            parsed_pages.append(
                {
                    "page_number": page.page_number,
                    "raw_text": page.raw_text,
                    "markdown": layout.markdown,
                    "layout_json": layout.layout_json,
                    "tables_markdown": "",
                }
            )

        # 5. Table / form extraction
        form_parser = FormParser()
        try:
            extracted_tables = form_parser.extract_tables(file_path)
            for table in extracted_tables:
                # Attach table markdown to the corresponding page
                for page_data in parsed_pages:
                    if page_data["page_number"] == table.page_number:
                        if page_data["tables_markdown"]:
                            page_data["tables_markdown"] += "\n\n" + table.markdown
                        else:
                            page_data["tables_markdown"] = table.markdown
        except Exception as exc:
            logger.warning("Table extraction failed: %s", exc)

        # Store the parsed representation before creating embeddings.
        _replace_pages(document_id, parsed_pages)

        # 6. & 7. Chunk + embed + store via LlamaIndex. Import lazily so the
        # health endpoint starts without loading the full ML runtime.
        from rag.indexer import Indexer

        indexer = Indexer()
        chunk_count = indexer.index_document(
            document_id=document_id,
            filename=filename,
            pages=parsed_pages,
        )

        if db_update_callback:
            await db_update_callback(document_id, "COMPLETED", None)
        else:
            _update_status(document_id, "COMPLETED")

        result = {
            "document_id": document_id,
            "filename": filename,
            "pages_parsed": len(parsed_pages),
            "chunks_indexed": chunk_count,
            "status": "COMPLETED",
        }
        logger.info("Ingestion completed: %s", result)
        return result

    except Exception as exc:
        logger.exception("Ingestion failed for document %s", document_id)
        try:
            if db_update_callback:
                await db_update_callback(document_id, "FAILED", str(exc))
            else:
                _update_status(document_id, "FAILED", str(exc))
        except Exception:
            logger.exception("Could not persist FAILED status for %s", document_id)
        return {
            "document_id": document_id,
            "filename": filename,
            "status": "FAILED",
            "error": str(exc),
        }


async def _download_file(file_url: str, filename: str) -> Path:
    """Download a file from a URL to a temp directory."""
    # If it's already a local path, just return it
    if os.path.exists(file_url):
        return Path(file_url)

    tmp_dir = Path(tempfile.mkdtemp(prefix="rag_ingest_"))
    dest = tmp_dir / filename

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(file_url)
        response.raise_for_status()
        dest.write_bytes(response.content)

    return dest
