"""Pinecone index connection and query helpers."""
import logging
from typing import Any

from backend import config
from backend.rag.embedder import embed_single

logger = logging.getLogger(__name__)

_index = None

NAMESPACES = {"openfoodfacts", "pubmed", "usda"}


def get_index():
    """Return the Pinecone index (lazy init)."""
    global _index
    if _index is None:
        try:
            from pinecone import Pinecone

            pc = Pinecone(api_key=config.PINECONE_API_KEY)
            _index = pc.Index(config.PINECONE_INDEX_NAME)
        except Exception as e:
            logger.warning("Pinecone not available: %s", e)
            _index = None
    return _index


def query(
    namespace: str,
    query_text: str,
    top_k: int = 3,
    include_metadata: bool = True,
) -> list[dict[str, Any]]:
    """
    Query the vector index in the given namespace.
    Returns list of { "id", "score", "metadata" } (metadata includes "text" when stored).
    """
    vector = embed_single(query_text)
    return query_by_vector(namespace, vector, top_k=top_k, include_metadata=include_metadata)


def query_by_vector(
    namespace: str,
    vector: list[float],
    top_k: int = 3,
    include_metadata: bool = True,
) -> list[dict[str, Any]]:
    """Query by precomputed vector (avoids re-embedding the same query)."""
    idx = get_index()
    if idx is None:
        return []
    try:
        result = idx.query(
            vector=vector,
            namespace=namespace,
            top_k=top_k,
            include_metadata=include_metadata,
        )
        out = []
        for match in (result.matches or []):
            meta = (match.metadata or {}).copy()
            out.append({"id": match.id, "score": getattr(match, "score", None), "metadata": meta})
        return out
    except Exception as e:
        logger.warning("Pinecone query failed: %s", e)
        return []


def upsert_vectors(
    namespace: str,
    ids: list[str],
    vectors: list[list[float]],
    metadatas: list[dict[str, Any]] | None = None,
) -> None:
    """Upsert vectors to the given namespace. metadatas[i] for ids[i]/vectors[i]."""
    idx = get_index()
    if idx is None:
        raise RuntimeError("Pinecone index not available")
    meta = metadatas or [{}] * len(ids)
    records = [
        {"id": i, "values": v, "metadata": {k: _sanitize_meta_val(val) for k, val in (m or {}).items()}}
        for i, v, m in zip(ids, vectors, meta)
    ]
    idx.upsert(vectors=records, namespace=namespace)


def _sanitize_meta_val(v: Any) -> str | float | int | bool:
    """Pinecone metadata values must be str, float, int, or bool."""
    if isinstance(v, (str, float, int, bool)):
        return v
    return str(v)


def retrieve_texts(namespace: str, query_text: str, top_k: int = 3) -> list[str]:
    """Return list of text chunks from the namespace for the query (for RAG context)."""
    hits = query(namespace, query_text, top_k=top_k)
    texts = []
    for h in hits:
        meta = h.get("metadata") or {}
        text = meta.get("text") or meta.get("content") or ""
        if text:
            texts.append(text)
    return texts
