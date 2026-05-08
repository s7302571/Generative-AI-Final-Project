"""PDF -> chunks -> embeddings -> ChromaDB.

A 10-K is split on heuristic section-header boundaries; tables stay intact in the
chunk that contains them. For an MVP this is good enough — refine the splitter
when you see specific failure modes in eval.
"""

from __future__ import annotations

import re
from pathlib import Path

import chromadb
import pdfplumber
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from . import config

# Headings like "Item 1.", "ITEM 7A.", "PART II"
SECTION_HEADER = re.compile(
    r"^\s*(ITEM\s+\d+[A-Z]?\.?|PART\s+[IVX]+)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = page.extract_tables() or []
            if tables:
                table_blocks = []
                for t in tables:
                    rows = ["\t".join((c or "") for c in row) for row in t]
                    table_blocks.append("\n".join(rows))
                text = text + "\n\n[TABLE]\n" + "\n\n".join(table_blocks)
            pages.append((page_num, text))
    return pages


def _chunk_pages(pages: list[tuple[int, str]]) -> list[dict]:
    """Group pages by section header, then break long sections into windows."""
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
        # Window long sections by character count (rough proxy for tokens).
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


def _embedding_fn():
    return SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL)


def _client():
    return chromadb.PersistentClient(path=str(config.INDEX_DIR))


def collection_name(filing_id: str) -> str:
    return f"filing_{filing_id}"


def ingest_filing(pdf_path: Path, filing_id: str) -> int:
    """Ingest a 10-K PDF. Idempotent — re-running replaces the collection."""
    pages = _extract_pages(pdf_path)
    chunks = _chunk_pages(pages)

    client = _client()
    name = collection_name(filing_id)
    try:
        client.delete_collection(name)
    except Exception:
        pass
    coll = client.create_collection(name=name, embedding_function=_embedding_fn())

    coll.add(
        ids=[f"{filing_id}_{i}" for i in range(len(chunks))],
        documents=[c["text"] for c in chunks],
        metadatas=[{"section": c["section"], "page": c["page"]} for c in chunks],
    )
    return len(chunks)


def list_filings() -> list[str]:
    client = _client()
    return [c.name.removeprefix("filing_") for c in client.list_collections() if c.name.startswith("filing_")]
