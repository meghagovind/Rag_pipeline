"""
PDF Parser — extracts raw text per page using pdfplumber (primary) or pypdf (fallback).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class PageResult:
    """Parsed result for a single PDF page."""

    page_number: int
    raw_text: str
    tables: list = field(default_factory=list)


class PDFParser:
    """Extract text from each page of a PDF file."""

    def parse(self, file_path: str | Path) -> List[PageResult]:
        """
        Parse the PDF and return a list of PageResult objects.
        Tries pdfplumber first; falls back to pypdf.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {file_path}")

        try:
            return self._parse_with_pdfplumber(file_path)
        except Exception as exc:
            logger.warning("pdfplumber failed (%s), falling back to pypdf", exc)
            return self._parse_with_pypdf(file_path)

    # ── pdfplumber ────────────────────────────────────────────────

    def _parse_with_pdfplumber(self, file_path: Path) -> List[PageResult]:
        import pdfplumber  # type: ignore

        results: List[PageResult] = []
        with pdfplumber.open(file_path) as pdf:
            for idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                results.append(
                    PageResult(
                        page_number=idx + 1,
                        raw_text=text,
                        tables=tables,
                    )
                )
        logger.info("Parsed %d pages with pdfplumber", len(results))
        return results

    # ── pypdf fallback ────────────────────────────────────────────

    def _parse_with_pypdf(self, file_path: Path) -> List[PageResult]:
        from pypdf import PdfReader  # type: ignore

        results: List[PageResult] = []
        reader = PdfReader(str(file_path))
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            results.append(
                PageResult(
                    page_number=idx + 1,
                    raw_text=text,
                    tables=[],
                )
            )
        logger.info("Parsed %d pages with pypdf", len(results))
        return results
