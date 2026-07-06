"""
Tests for the document parsers.
These tests use mock data and don't require external binaries (tesseract, etc.).
"""

from __future__ import annotations

import textwrap

import pytest

from parsers.form_parser import FormParser
from parsers.layout_parser import LayoutParser


# ── Layout Parser Tests ───────────────────────────────────────────


class TestLayoutParser:
    def test_heading_detection(self):
        text = "INTRODUCTION TO THE SYSTEM\n\nSome paragraph text here."
        parser = LayoutParser()
        result = parser.parse_page(text, page_number=1)
        assert result.page_number == 1
        assert result.markdown  # should produce non-empty markdown
        assert "INTRODUCTION" in result.markdown

    def test_list_detection(self):
        text = "Items:\n- First item\n- Second item\n- Third item"
        parser = LayoutParser()
        result = parser.parse_page(text, page_number=2)
        assert "First item" in result.markdown
        assert "Second item" in result.markdown

    def test_empty_text(self):
        parser = LayoutParser()
        result = parser.parse_page("", page_number=1)
        assert result.page_number == 1
        assert result.blocks == []

    def test_layout_json_structure(self):
        text = "HEADING TEXT\n\nParagraph content."
        parser = LayoutParser()
        result = parser.parse_page(text, page_number=3)
        assert "page_number" in result.layout_json
        assert result.layout_json["page_number"] == 3
        assert "block_count" in result.layout_json


# ── Form / Table Parser Tests ────────────────────────────────────


class TestFormParser:
    def test_pipe_table_extraction(self):
        text = textwrap.dedent("""\
            | Name  | Age | City     |
            |-------|-----|----------|
            | Alice | 30  | New York |
            | Bob   | 25  | London   |
        """)
        parser = FormParser()
        tables = parser.extract_tables_from_text(text, page_number=1)
        assert len(tables) >= 1
        tbl = tables[0]
        assert "Name" in tbl.headers
        assert len(tbl.rows) >= 2
        assert "Alice" in tbl.rows[0]

    def test_tab_table_extraction(self):
        text = "Name\tAge\tCity\nAlice\t30\tNew York\nBob\t25\tLondon"
        parser = FormParser()
        tables = parser.extract_tables_from_text(text, page_number=5)
        assert len(tables) >= 1
        tbl = tables[0]
        assert "Name" in tbl.headers

    def test_markdown_output(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        parser = FormParser()
        tables = parser.extract_tables_from_text(text, page_number=1)
        assert len(tables) >= 1
        assert "|" in tables[0].markdown

    def test_no_table_in_plain_text(self):
        text = "This is just a normal paragraph with no tables at all."
        parser = FormParser()
        tables = parser.extract_tables_from_text(text, page_number=1)
        assert len(tables) == 0

    def test_to_markdown_table_static(self):
        headers = ["Col1", "Col2"]
        rows = [["a", "b"], ["c", "d"]]
        md = FormParser._to_markdown_table(headers, rows)
        assert "Col1" in md
        assert "| a | b |" in md
