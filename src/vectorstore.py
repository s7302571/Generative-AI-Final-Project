"""In-memory FAISS vector store.

One instance = one PDF, lives in Streamlit session state. Cosine similarity via
L2-normalized embeddings + IndexFlatIP. The encoder is loaded once and cached
at module level — `SentenceTransformer.__init__` is the slow path (downloads
the model on first run) and Streamlit reruns the script on every interaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from . import config
from .ingest import chunks_from_pdf_bytes, chunks_from_pdf_path


@lru_cache(maxsize=1)
def _encoder() -> SentenceTransformer:
    return SentenceTransformer(config.EMBEDDING_MODEL)


def _embed(texts: list[str]) -> np.ndarray:
    vecs = _encoder().encode(texts, convert_to_numpy=True, show_progress_bar=False)
    faiss.normalize_L2(vecs)
    return vecs.astype("float32")


@dataclass
class VectorStore:
    chunks: list[dict] = field(default_factory=list)
    index: faiss.Index | None = None
    name: str = ""

    @classmethod
    def from_pdf_bytes(cls, data: bytes, name: str = "") -> "VectorStore":
        return cls._build(chunks_from_pdf_bytes(data), name)

    @classmethod
    def from_pdf_path(cls, path, name: str = "") -> "VectorStore":
        return cls._build(chunks_from_pdf_path(path), name or str(path))

    @classmethod
    def _build(cls, chunks: list[dict], name: str) -> "VectorStore":
        if not chunks:
            raise ValueError("PDF produced zero chunks")
        embeddings = _embed([c["text"] for c in chunks])
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        return cls(chunks=chunks, index=index, name=name)

    def query(self, text: str, k: int = config.TOP_K) -> list[dict]:
        if self.index is None or not self.chunks:
            return []
        q = _embed([text])
        scores, idxs = self.index.search(q, min(k, len(self.chunks)))
        out = []
        for score, i in zip(scores[0], idxs[0]):
            if i < 0:
                continue
            chunk = self.chunks[i]
            out.append(
                {
                    "text": chunk["text"],
                    "section": chunk["section"],
                    "page": chunk["page"],
                    "score": float(score),
                }
            )
        return out

    def __len__(self) -> int:
        return len(self.chunks)
