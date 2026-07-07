"""Generic file parser for text, code, CSV/TSV, JSON/XML/HTML, and Office XML files."""

from __future__ import annotations

import csv
import html
import json
import logging
import os
import re
import zipfile
from pathlib import Path
from typing import Iterable, List
from xml.etree import ElementTree

from parsers.pdf_parser import PageResult

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = int(os.getenv("RAG_MAX_TEXT_CHARS", "10000"))
MAX_DELIMITED_ROWS = int(os.getenv("RAG_MAX_DELIMITED_ROWS", "25"))
MAX_CELL_CHARS = int(os.getenv("RAG_MAX_CELL_CHARS", "300"))


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".sql",
    ".json",
    ".jsonl",
    ".xml",
    ".html",
    ".htm",
    ".log",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".kts",
    ".r",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".bat",
    ".cmd",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".svg",
}

OFFICE_EXTENSIONS = {".docx", ".xlsx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | OFFICE_EXTENSIONS | IMAGE_EXTENSIONS | {".pdf"}


class TextParser:
    """Extract readable text from common non-PDF file formats."""

    def parse(self, file_path: str | Path) -> List[PageResult]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix in {".csv", ".tsv"}:
            text = self._parse_delimited_file(file_path, delimiter="\t" if suffix == ".tsv" else ",")
        elif suffix == ".json":
            text = self._parse_json(file_path)
        elif suffix == ".docx":
            text = self._parse_docx(file_path)
        elif suffix == ".xlsx":
            text = self._parse_xlsx(file_path)
        elif suffix in IMAGE_EXTENSIONS:
            text = self._parse_image(file_path)
        else:
            text = self._read_text(file_path)

        text = text.strip()
        if not text:
            raise ValueError(f"No readable text could be extracted from {file_path.name}")

        return [
            PageResult(page_number=index + 1, raw_text=chunk)
            for index, chunk in enumerate(self._split_text(text))
        ]

    def _read_text(self, file_path: Path) -> str:
        data = file_path.read_bytes()
        if b"\x00" in data[:4096]:
            raise ValueError(
                f"{file_path.name} looks like a binary file. Add a format-specific parser to index it."
            )

        for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
            try:
                return self._cap_text(data.decode(encoding), file_path.name)
            except UnicodeDecodeError:
                continue
        return self._cap_text(data.decode("utf-8", errors="replace"), file_path.name)

    def _parse_delimited_file(self, file_path: Path, delimiter: str) -> str:
        rows: list[list[str]] = []
        has_more_rows = False
        with file_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            for row in reader:
                if len(rows) < MAX_DELIMITED_ROWS + 1:
                    rows.append(row)
                else:
                    has_more_rows = True
                    break

        if not rows:
            return ""

        header = rows[0]
        body = rows[1:]
        markdown = self._markdown_table(header, body)
        sampled_rows = max(0, len(rows) - 1)
        note = (
            f"Delimited data file: {file_path.name}\n"
            f"Columns: {', '.join(header)}\n"
            f"Rows indexed: first {sampled_rows} data rows"
        )
        if has_more_rows:
            note += " from a larger file"
        note += (
            "\n\nNote: Large delimited files are sampled during RAG ingestion "
            "to keep upload and embedding generation fast. For full-dataset analytics, "
            "load the CSV into a database or dataframe tool.\n\n"
        )
        return self._cap_text(note + markdown, file_path.name)

    def _parse_json(self, file_path: Path) -> str:
        raw_text = self._read_text(file_path)
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            return raw_text
        return self._cap_text(json.dumps(parsed, indent=2, ensure_ascii=False), file_path.name)

    def _parse_docx(self, file_path: Path) -> str:
        try:
            with zipfile.ZipFile(file_path) as archive:
                xml = archive.read("word/document.xml")
        except Exception as exc:
            raise ValueError(f"Could not read DOCX text from {file_path.name}: {exc}") from exc

        root = ElementTree.fromstring(xml)
        lines: list[str] = []
        for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            parts = [
                node.text or ""
                for node in paragraph.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
            ]
            line = "".join(parts).strip()
            if line:
                lines.append(line)
        return self._cap_text("\n".join(lines), file_path.name)

    def _parse_xlsx(self, file_path: Path) -> str:
        try:
            with zipfile.ZipFile(file_path) as archive:
                shared_strings = self._xlsx_shared_strings(archive)
                sheet_names = sorted(
                    name
                    for name in archive.namelist()
                    if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
                )
                sections = []
                for sheet_name in sheet_names:
                    rows = self._xlsx_sheet_rows(archive.read(sheet_name), shared_strings)
                    if rows:
                        sections.append(f"Sheet: {Path(sheet_name).stem}\n\n{self._markdown_table(rows[0], rows[1:])}")
        except Exception as exc:
            raise ValueError(f"Could not read XLSX text from {file_path.name}: {exc}") from exc

        return self._cap_text("\n\n".join(sections), file_path.name)

    def _xlsx_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        try:
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
        except KeyError:
            return []
        namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        values = []
        for item in root.iter(f"{namespace}si"):
            values.append("".join(node.text or "" for node in item.iter(f"{namespace}t")))
        return values

    def _xlsx_sheet_rows(self, xml: bytes, shared_strings: list[str]) -> list[list[str]]:
        root = ElementTree.fromstring(xml)
        namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        rows = []
        for row in root.iter(f"{namespace}row"):
            values = []
            for cell in row.iter(f"{namespace}c"):
                value_node = cell.find(f"{namespace}v")
                value = value_node.text if value_node is not None else ""
                if cell.attrib.get("t") == "s" and value:
                    value = shared_strings[int(value)] if int(value) < len(shared_strings) else value
                values.append(value or "")
            if any(value.strip() for value in values):
                rows.append(values)
        return rows

    def _parse_image(self, file_path: Path) -> str:
        try:
            from PIL import Image  # type: ignore
            import pytesseract  # type: ignore

            return pytesseract.image_to_string(Image.open(file_path)).strip()
        except Exception as exc:
            raise ValueError(f"Could not OCR image {file_path.name}: {exc}") from exc

    def _split_text(self, text: str, max_chars: int = 12000) -> Iterable[str]:
        if len(text) <= max_chars:
            yield text
            return

        paragraphs = re.split(r"\n\s*\n", text)
        current: list[str] = []
        current_len = 0
        for paragraph in paragraphs:
            paragraph_len = len(paragraph)
            if current and current_len + paragraph_len + 2 > max_chars:
                yield "\n\n".join(current)
                current = []
                current_len = 0
            if paragraph_len > max_chars:
                for index in range(0, paragraph_len, max_chars):
                    yield paragraph[index : index + max_chars]
            else:
                current.append(paragraph)
                current_len += paragraph_len + 2
        if current:
            yield "\n\n".join(current)

    @staticmethod
    def _markdown_table(header: list[str], rows: list[list[str]]) -> str:
        width = max(len(header), *(len(row) for row in rows)) if rows else len(header)
        normalized_header = TextParser._normalize_row(header, width)
        normalized_rows = [TextParser._normalize_row(row, width) for row in rows]

        header_line = "| " + " | ".join(normalized_header) + " |"
        separator = "| " + " | ".join(["---"] * width) + " |"
        body = ["| " + " | ".join(row) + " |" for row in normalized_rows]
        return "\n".join([header_line, separator, *body])

    @staticmethod
    def _normalize_row(row: list[str], width: int) -> list[str]:
        cells = []
        for cell in row:
            value = str(cell).strip()
            if len(value) > MAX_CELL_CHARS:
                value = value[:MAX_CELL_CHARS] + "..."
            cells.append(html.escape(value))
        return cells + [""] * (width - len(cells))

    @staticmethod
    def _cap_text(text: str, filename: str) -> str:
        if len(text) <= MAX_TEXT_CHARS:
            return text
        return (
            text[:MAX_TEXT_CHARS]
            + "\n\n[Ingestion note: content from "
            + filename
            + f" was truncated to the first {MAX_TEXT_CHARS:,} characters "
            + "to keep indexing responsive.]"
        )
