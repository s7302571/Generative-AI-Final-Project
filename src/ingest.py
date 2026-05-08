"""PDF -> text chunks. Pure — no DB, no embeddings.

Tries to split on SEC-style section headers ("Item 7A.", "PART II", ...) so a
10-K is grouped sensibly. PDFs without those headers fall through to the
size-based windowing in `_chunk_pages` and still produce reasonable chunks.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pdfplumber

from . import config

SECTION_HEADER = re.compile(
    r"^\s*(ITEM\s+\d+[A-Z]?\.?|PART\s+[IVX]+)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_pages(pdf_source) -> list[tuple[int, str]]:
    pages = []
    with pdfplumber.open(pdf_source) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []
            if tables:
                blocks = []
                for t in tables:
                    rows = ["\t".join((c or "") for c in row) for row in t]
                    blocks.append("\n".join(rows))
                text = text + "\n\n[TABLE]\n" + "\n\n".join(blocks)
            pages.append((page_num, text))
    return pages


def _chunk_pages(pages: list[tuple[int, str]]) -> list[dict]:
    chunks: list[dict] = []
    current_section = "Front Matter"
    buffer: list[tuple[int, str]] = []

    def flush():
        if not buffer:
            return
        text = "\n".join(t for _, t in buffer).strip()
        if not text:
            buffer.clear()
            return
        first_page = buffer[0][0]
        max_chars = config.CHUNK_TOKENS * 4
        overlap_chars = config.CHUNK_OVERLAP * 4
        if len(text) <= max_chars:
            chunks.append({"section": current_section, "page": first_page, "text": text})
        else:
            start = 0
            while start < len(text):
                end = min(start + max_chars, len(text))
                chunks.append(
                    {"section": current_section, "page": first_page, "text": text[start:end]}
                )
                if end == len(text):
                    break
                start = end - overlap_chars
        buffer.clear()

    for page_num, text in pages:
        match = SECTION_HEADER.search(text)
        if match:
            flush()
            current_section = match.group(0).strip()[:80]
        buffer.append((page_num, text))
    flush()
    return chunks


def chunks_from_pdf_path(path: Path) -> list[dict]:
    return _chunk_pages(_extract_pages(path))


def chunks_from_pdf_bytes(data: bytes) -> list[dict]:
    return _chunk_pages(_extract_pages(io.BytesIO(data)))
