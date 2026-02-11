"""Document parser — extracts text from PDF, DOCX, TXT, CSV files."""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parse various document formats into plain text."""

    SUPPORTED = {".pdf", ".docx", ".txt", ".csv", ".md"}

    def parse(self, filepath: Path) -> tuple[str, dict]:
        """
        Parse a document and return (text, metadata).

        Metadata includes page count, format, etc.
        """
        suffix = filepath.suffix.lower()
        if suffix not in self.SUPPORTED:
            raise ValueError(f"Unsupported file type: {suffix}")

        parser_map = {
            ".pdf": self._parse_pdf,
            ".docx": self._parse_docx,
            ".txt": self._parse_txt,
            ".md": self._parse_txt,
            ".csv": self._parse_csv,
        }
        return parser_map[suffix](filepath)

    @staticmethod
    def _parse_pdf(filepath: Path) -> tuple[str, dict]:
        import fitz  # PyMuPDF

        doc = fitz.open(str(filepath))
        pages = []
        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")
            if text.strip():
                pages.append(f"[Page {page_num}]\n{text}")
        doc.close()
        return "\n\n".join(pages), {"pages": len(pages), "format": "pdf"}

    @staticmethod
    def _parse_docx(filepath: Path) -> tuple[str, dict]:
        from docx import Document

        doc = Document(str(filepath))
        paragraphs = []
        for para in doc.paragraphs:
            if para.text.strip():
                # Preserve heading structure
                if para.style.name.startswith("Heading"):
                    level = para.style.name.replace("Heading ", "").strip()
                    paragraphs.append(f"{'#' * int(level) if level.isdigit() else '#'} {para.text}")
                else:
                    paragraphs.append(para.text)
        return "\n\n".join(paragraphs), {"paragraphs": len(paragraphs), "format": "docx"}

    @staticmethod
    def _parse_txt(filepath: Path) -> tuple[str, dict]:
        text = filepath.read_text(encoding="utf-8", errors="replace")
        return text, {"chars": len(text), "format": "txt"}

    @staticmethod
    def _parse_csv(filepath: Path) -> tuple[str, dict]:
        text = filepath.read_text(encoding="utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return text, {"rows": 0, "format": "csv"}

        # Convert CSV rows into readable text
        parts = []
        headers = list(rows[0].keys())
        parts.append("Headers: " + ", ".join(headers))
        for i, row in enumerate(rows, 1):
            row_text = " | ".join(f"{k}: {v}" for k, v in row.items())
            parts.append(f"Row {i}: {row_text}")

        return "\n".join(parts), {"rows": len(rows), "columns": len(headers), "format": "csv"}
