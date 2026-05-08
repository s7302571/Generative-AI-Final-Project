from __future__ import annotations

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from . import config
from .ingest import collection_name


def _client():
    return chromadb.PersistentClient(path=str(config.INDEX_DIR))


def retrieve(filing_id: str, query: str, k: int = config.TOP_K) -> list[dict]:
    client = _client()
    coll = client.get_collection(
        name=collection_name(filing_id),
        embedding_function=SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL),
    )
    res = coll.query(query_texts=[query], n_results=k)
    out = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        out.append(
            {
                "text": doc,
                "section": meta.get("section", "Unknown"),
                "page": meta.get("page", "?"),
                "distance": dist,
            }
        )
    return out
