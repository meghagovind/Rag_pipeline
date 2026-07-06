"""
OCR Parser — runs optical character recognition on scanned PDF pages.
Uses pytesseract (primary) with Pillow; falls back gracefully if unavailable.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OCRPageResult:
    """OCR result for a single page image."""

    page_number: int
    ocr_text: str
    confidence: Optional[float] = None


class OCRParser:
    """Perform OCR on page images extracted from a PDF."""

    def ocr_pdf(self, file_path: str | Path) -> List[OCRPageResult]:
        """
        Convert each PDF page to an image and run OCR.
        Returns a list of OCRPageResult with extracted text.
        """
        file_path = Path(file_path)
        images = self._pdf_to_images(file_path)
        if not images:
            logger.warning("No images extracted from PDF for OCR")
            return []

        results: List[OCRPageResult] = []
        for idx, img in enumerate(images):
            text = self._run_ocr(img)
            results.append(OCRPageResult(page_number=idx + 1, ocr_text=text))

        logger.info("OCR completed for %d pages", len(results))
        return results

    def ocr_image(self, image_bytes: bytes, page_number: int = 1) -> OCRPageResult:
        """Run OCR on a single image provided as raw bytes."""
        from PIL import Image  # type: ignore

        img = Image.open(io.BytesIO(image_bytes))
        text = self._run_ocr(img)
        return OCRPageResult(page_number=page_number, ocr_text=text)

    # ── Internals ─────────────────────────────────────────────────

    def _pdf_to_images(self, file_path: Path) -> list:
        """Convert PDF pages to PIL images using pdfplumber page rendering."""
        try:
            import pdfplumber  # type: ignore
            from PIL import Image  # type: ignore

            images = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Render page to image at 200 DPI
                    img = page.to_image(resolution=200)
                    pil_img = img.original
                    images.append(pil_img)
            return images
        except Exception as exc:
            logger.warning("Failed to convert PDF to images: %s", exc)
            return []

    def _run_ocr(self, image) -> str:  # noqa: ANN001
        """Run pytesseract on a PIL image; return empty string if unavailable."""
        try:
            import pytesseract  # type: ignore

            text: str = pytesseract.image_to_string(image)
            return text.strip()
        except ImportError:
            logger.warning(
                "pytesseract not installed — skipping OCR. "
                "Install with: pip install pytesseract"
            )
            return ""
        except Exception as exc:
            logger.error("OCR failed: %s", exc)
            return ""
