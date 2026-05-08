"""PDF -> text chunks. Pure — no DB, no embeddings.

Tries to split on SEC-style section headers ("Item 7A.", "PART II", ...) so a
10-K is grouped sensibly. PDFs without those headers fall through to the
size-based windowing in `_chunk_pages` and still produce reasonable chunks.

Extraction:
- pdfplumber is the primary path (handles tables well)
- pypdf is the fallback when pdfplumber returns ~no text (it succeeds on some
  PDFs pdfplumber can't decode, especially when fonts/encodings are unusual)
- If both yield nothing, the PDF is almost certainly scanned (image-only) and
  needs OCR — we surface that explicitly to the caller.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from . import config

SECTION_HEADER = re.compile(
    r"^\s*(ITEM\s+\d+[A-Z]?\.?|PART\s+[IVX]+)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)

# If both extractors yield fewer chars than this total, treat as a scan.
_MIN_TEXT_CHARS = 500


class PDFTextExtractionError(RuntimeError):
    """Raised when no extractor can pull meaningful text from a PDF."""


def _extract_pages_pdfplumber(data: bytes) -> list[tuple[int, str]]:
    pages = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
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


def _extract_pages_pypdf(data: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(io.BytesIO(data))
    return [(i, p.extract_text() or "") for i, p in enumerate(reader.pages, start=1)]


def _total_chars(pages: list[tuple[int, str]]) -> int:
    return sum(len(t) for _, t in pages)


def _extract_pages(data: bytes) -> list[tuple[int, str]]:
    primary = _extract_pages_pdfplumber(data)
    if _total_chars(primary) >= _MIN_TEXT_CHARS:
        return primary

    # pdfplumber gave up — try pypdf
    try:
        fallback = _extract_pages_pypdf(data)
    except Exception:
        fallback = []

    if _total_chars(fallback) > _total_chars(primary):
        return fallback

    n_pages = len(primary) or len(fallback)
    raise PDFTextExtractionError(
        f"Couldn't extract text from this PDF ({n_pages} pages, "
        f"{_total_chars(primary)} chars from pdfplumber, "
        f"{_total_chars(fallback)} chars from pypdf). "
        "It's probably a scanned/image-based PDF — run OCR first "
        "(e.g. `ocrmypdf input.pdf output.pdf`) and re-upload."
    )


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
    return _chunk_pages(_extract_pages(path.read_bytes()))


def chunks_from_pdf_bytes(data: bytes) -> list[dict]:
    return _chunk_pages(_extract_pages(data))
