"""
Layout Parser — detects document layout structure (headings, paragraphs,
lists, tables, figures) and converts raw page text into clean Markdown.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class LayoutBlock:
    """Represents one detected layout block on a page."""

    block_type: str  # heading | paragraph | list | table | figure | unknown
    content: str
    order: int  # reading order index


@dataclass
class LayoutResult:
    """Layout analysis result for a single page."""

    page_number: int
    blocks: List[LayoutBlock] = field(default_factory=list)
    markdown: str = ""
    layout_json: Dict = field(default_factory=dict)


class LayoutParser:
    """
    Heuristic layout parser that converts raw text into structured Markdown.
    Uses regex-based detection for headings, lists, and paragraphs.
    Can be extended to use ML-based layout detection (layoutparser, etc.).
    """

    # Heuristic patterns
    _HEADING_PATTERN = re.compile(
        r"^(?:CHAPTER|SECTION|PART)?\s*\d*\.?\d*\s*[A-Z][A-Z ]{4,}$", re.MULTILINE
    )
    _LIST_PATTERN = re.compile(r"^\s*(?:[•\-\*]|\d+[.)]) ", re.MULTILINE)
    _TABLE_SEPARATOR = re.compile(r"[\|\+][\-\+]+[\|\+]")

    def parse_page(self, raw_text: str, page_number: int) -> LayoutResult:
        """
        Analyse raw_text and produce a LayoutResult with classified blocks
        and a clean Markdown rendition.
        """
        blocks = self._detect_blocks(raw_text)
        markdown = self._blocks_to_markdown(blocks)

        layout_json = {
            "page_number": page_number,
            "block_count": len(blocks),
            "block_types": [b.block_type for b in blocks],
        }

        return LayoutResult(
            page_number=page_number,
            blocks=blocks,
            markdown=markdown,
            layout_json=layout_json,
        )

    # ── Block detection ───────────────────────────────────────────

    def _detect_blocks(self, text: str) -> List[LayoutBlock]:
        """Split text into layout blocks using heuristics."""
        lines = text.split("\n")
        blocks: List[LayoutBlock] = []
        current_lines: list[str] = []
        current_type = "paragraph"
        order = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                # Flush current block
                if current_lines:
                    blocks.append(
                        LayoutBlock(
                            block_type=current_type,
                            content="\n".join(current_lines),
                            order=order,
                        )
                    )
                    order += 1
                    current_lines = []
                    current_type = "paragraph"
                continue

            detected = self._classify_line(stripped)
            if detected != current_type and current_lines:
                blocks.append(
                    LayoutBlock(
                        block_type=current_type,
                        content="\n".join(current_lines),
                        order=order,
                    )
                )
                order += 1
                current_lines = []

            current_type = detected
            current_lines.append(stripped)

        if current_lines:
            blocks.append(
                LayoutBlock(
                    block_type=current_type,
                    content="\n".join(current_lines),
                    order=order,
                )
            )

        return blocks

    def _classify_line(self, line: str) -> str:
        """Classify a single line into a block type."""
        if self._HEADING_PATTERN.match(line):
            return "heading"
        if self._LIST_PATTERN.match(line):
            return "list"
        if self._TABLE_SEPARATOR.search(line):
            return "table"
        return "paragraph"

    # ── Markdown conversion ───────────────────────────────────────

    def _blocks_to_markdown(self, blocks: List[LayoutBlock]) -> str:
        """Convert classified blocks into Markdown text."""
        md_parts: list[str] = []
        for block in blocks:
            if block.block_type == "heading":
                # Use ## for detected headings
                md_parts.append(f"## {block.content}\n")
            elif block.block_type == "list":
                # Normalise list markers to Markdown dashes
                items = block.content.split("\n")
                for item in items:
                    clean = re.sub(r"^\s*(?:[•\-\*]|\d+[.)])\s*", "", item)
                    md_parts.append(f"- {clean}")
                md_parts.append("")
            elif block.block_type == "table":
                md_parts.append(f"```\n{block.content}\n```\n")
            else:
                md_parts.append(f"{block.content}\n")

        return "\n".join(md_parts)
