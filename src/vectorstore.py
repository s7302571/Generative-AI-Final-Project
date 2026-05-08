"""In-memory hybrid (dense + BM25) vector store.

One instance = one PDF, lives in Streamlit session state. Dense side is cosine
similarity via L2-normalized embeddings + IndexFlatIP. Sparse side is BM25Okapi
over a simple lowercase/word-token split. Final ranking fuses the two with
Reciprocal Rank Fusion (RRF), which avoids having to calibrate score scales
across the two retrievers.

The encoder is loaded once and cached at module level — `SentenceTransformer.__init__`
is the slow path (downloads the model on first run) and Streamlit reruns the
script on every interaction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
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


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class VectorStore:
    chunks: list[dict] = field(default_factory=list)
    index: faiss.Index | None = None
    bm25: BM25Okapi | None = None
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
        texts = [c["text"] for c in chunks]
        embeddings = _embed(texts)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        bm25 = BM25Okapi([_tokenize(t) for t in texts])
        return cls(chunks=chunks, index=index, bm25=bm25, name=name)

    def query(self, text: str, k: int = config.TOP_K) -> list[dict]:
        if self.index is None or not self.chunks:
            return []
        n = len(self.chunks)
        cand = min(config.HYBRID_CANDIDATES, n)

        q_dense = _embed([text])
        _, dense_idxs = self.index.search(q_dense, cand)
        dense_ranks: dict[int, int] = {
            int(i): rank for rank, i in enumerate(dense_idxs[0]) if i >= 0
        }

        sparse_ranks: dict[int, int] = {}
        if self.bm25 is not None:
            scores = self.bm25.get_scores(_tokenize(text))
            top = np.argsort(scores)[::-1][:cand]
            sparse_ranks = {int(i): rank for rank, i in enumerate(top) if scores[i] > 0}

        rrf_k = config.RRF_K
        fused: dict[int, float] = {}
        for i, r in dense_ranks.items():
            fused[i] = fused.get(i, 0.0) + 1.0 / (rrf_k + r)
        for i, r in sparse_ranks.items():
            fused[i] = fused.get(i, 0.0) + 1.0 / (rrf_k + r)

        ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[: min(k, n)]
        out = []
        for i, score in ordered:
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
