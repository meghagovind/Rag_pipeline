"""
Form / Table Parser — extracts tabular data from PDFs and converts to
structured Markdown tables.

Uses camelot-py (primary) or pdfplumber table extraction (fallback).
Also includes a heuristic plaintext table detector for non-PDF inputs.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """A single table extracted from a document page."""

    page_number: int
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    markdown: str = ""
    accuracy: Optional[float] = None


class FormParser:
    """
    Extract tables/forms from PDFs and convert them into Markdown tables.
    Falls back through multiple strategies.
    """

    def extract_tables(
        self, file_path: str | Path, pages: Optional[str] = None
    ) -> List[ExtractedTable]:
        """
        Extract all tables from the given PDF.

        Args:
            file_path: Path to the PDF file.
            pages: Page specification string (e.g. "1,2,3" or "all").
                   Defaults to "all".

        Returns:
            List of ExtractedTable objects with Markdown representations.
        """
        file_path = Path(file_path)
        pages = pages or "all"

        try:
            return self._extract_with_camelot(file_path, pages)
        except Exception as exc:
            logger.warning("camelot extraction failed (%s), trying pdfplumber", exc)

        try:
            return self._extract_with_pdfplumber(file_path)
        except Exception as exc:
            logger.warning("pdfplumber table extraction failed (%s)", exc)

        return []

    def extract_tables_from_text(
        self, text: str, page_number: int = 1
    ) -> List[ExtractedTable]:
        """
        Heuristic fallback: detect table-like structures in plain text
        (e.g. tab-separated or pipe-separated rows).
        """
        tables: List[ExtractedTable] = []

        # Detect pipe-separated tables
        pipe_blocks = self._find_pipe_table_blocks(text)
        for block in pipe_blocks:
            tbl = self._parse_pipe_block(block, page_number)
            if tbl:
                tables.append(tbl)

        # Detect tab-separated tables
        if not tables:
            tab_blocks = self._find_tab_table_blocks(text)
            for block in tab_blocks:
                tbl = self._parse_tab_block(block, page_number)
                if tbl:
                    tables.append(tbl)

        return tables

    # ── camelot ───────────────────────────────────────────────────

    def _extract_with_camelot(
        self, file_path: Path, pages: str
    ) -> List[ExtractedTable]:
        import camelot  # type: ignore

        tables_found = camelot.read_pdf(
            str(file_path), pages=pages, flavor="lattice"
        )

        if not tables_found or len(tables_found) == 0:
            # Retry with stream flavour for borderless tables
            tables_found = camelot.read_pdf(
                str(file_path), pages=pages, flavor="stream"
            )

        results: List[ExtractedTable] = []
        for tbl in tables_found:
            df = tbl.df
            headers = [str(c) for c in df.iloc[0].tolist()]
            rows = [[str(c) for c in row] for row in df.iloc[1:].values.tolist()]
            md = self._to_markdown_table(headers, rows)
            results.append(
                ExtractedTable(
                    page_number=tbl.page,
                    headers=headers,
                    rows=rows,
                    markdown=md,
                    accuracy=tbl.accuracy if hasattr(tbl, "accuracy") else None,
                )
            )

        logger.info("Extracted %d tables with camelot", len(results))
        return results

    # ── pdfplumber fallback ───────────────────────────────────────

    def _extract_with_pdfplumber(self, file_path: Path) -> List[ExtractedTable]:
        import pdfplumber  # type: ignore

        results: List[ExtractedTable] = []
        with pdfplumber.open(file_path) as pdf:
            for idx, page in enumerate(pdf.pages):
                page_tables = page.extract_tables() or []
                for raw_table in page_tables:
                    if not raw_table or len(raw_table) < 2:
                        continue
                    headers = [str(c or "") for c in raw_table[0]]
                    rows = [
                        [str(c or "") for c in row] for row in raw_table[1:]
                    ]
                    md = self._to_markdown_table(headers, rows)
                    results.append(
                        ExtractedTable(
                            page_number=idx + 1,
                            headers=headers,
                            rows=rows,
                            markdown=md,
                        )
                    )
        logger.info("Extracted %d tables with pdfplumber", len(results))
        return results

    # ── Heuristic plain-text helpers ──────────────────────────────

    def _find_pipe_table_blocks(self, text: str) -> List[str]:
        """Find contiguous blocks of lines containing pipe characters."""
        blocks: List[str] = []
        current: list[str] = []
        for line in text.split("\n"):
            if "|" in line:
                current.append(line)
            else:
                if len(current) >= 2:
                    blocks.append("\n".join(current))
                current = []
        if len(current) >= 2:
            blocks.append("\n".join(current))
        return blocks

    def _parse_pipe_block(
        self, block: str, page_number: int
    ) -> Optional[ExtractedTable]:
        """Parse a pipe-delimited text block into an ExtractedTable."""
        lines = [l for l in block.split("\n") if l.strip()]  # noqa: E741
        if len(lines) < 2:
            return None
        # Remove separator lines (---+---)
        data_lines = [
            l for l in lines if not re.match(r"^[\s\|\-\+:]+$", l)  # noqa: E741
        ]
        if len(data_lines) < 2:
            return None

        def split_row(line: str) -> List[str]:
            return [c.strip() for c in line.strip().strip("|").split("|")]

        headers = split_row(data_lines[0])
        rows = [split_row(r) for r in data_lines[1:]]
        md = self._to_markdown_table(headers, rows)
        return ExtractedTable(
            page_number=page_number, headers=headers, rows=rows, markdown=md
        )

    def _find_tab_table_blocks(self, text: str) -> List[str]:
        """Find contiguous blocks of tab-separated lines."""
        blocks: List[str] = []
        current: list[str] = []
        for line in text.split("\n"):
            if "\t" in line:
                current.append(line)
            else:
                if len(current) >= 2:
                    blocks.append("\n".join(current))
                current = []
        if len(current) >= 2:
            blocks.append("\n".join(current))
        return blocks

    def _parse_tab_block(
        self, block: str, page_number: int
    ) -> Optional[ExtractedTable]:
        """Parse a tab-separated text block into an ExtractedTable."""
        lines = [l for l in block.split("\n") if l.strip()]  # noqa: E741
        if len(lines) < 2:
            return None
        headers = [c.strip() for c in lines[0].split("\t")]
        rows = [[c.strip() for c in r.split("\t")] for r in lines[1:]]
        md = self._to_markdown_table(headers, rows)
        return ExtractedTable(
            page_number=page_number, headers=headers, rows=rows, markdown=md
        )

    # ── Markdown table formatter ──────────────────────────────────

    @staticmethod
    def _to_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
        """Convert headers + rows into a Markdown table string."""
        if not headers:
            return ""
        col_count = len(headers)
        # Normalise row lengths
        norm_rows = [r + [""] * (col_count - len(r)) for r in rows]

        header_line = "| " + " | ".join(headers) + " |"
        sep_line = "| " + " | ".join(["---"] * col_count) + " |"
        body_lines = ["| " + " | ".join(r) + " |" for r in norm_rows]

        return "\n".join([header_line, sep_line, *body_lines])
