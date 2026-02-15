"""RAG retrieval: query by namespace and return context string for prompts."""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.rag.embedder import embed_single
from backend.rag.pinecone_client import get_index, query_by_vector, retrieve_texts

logger = logging.getLogger(__name__)
MAX_CHUNKS = 3  # fewer chunks = faster Pinecone + smaller prompts


def get_nutrition_context(query: str, top_k: int = MAX_CHUNKS) -> str:
    """Retrieve context from openfoodfacts and usda in parallel. Returns "" on any failure so agent can still run."""
    try:
        if get_index() is None:
            return ""
        vector = embed_single(query)
        parts = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(query_by_vector, "openfoodfacts", vector, top_k): "openfoodfacts",
                pool.submit(query_by_vector, "usda", vector, top_k): "usda",
            }
            for fut in as_completed(futures):
                hits = fut.result()
                texts = []
                for h in hits:
                    meta = h.get("metadata") or {}
                    text = meta.get("text") or meta.get("content") or ""
                    if text:
                        texts.append(text)
                if texts:
                    parts.append("\n".join(texts))
        return "\n\n---\n\n".join(parts) if parts else ""
    except Exception as e:
        logger.warning("RAG nutrition context failed (using empty context): %s", e)
        return ""


def get_research_context(query: str, top_k: int = MAX_CHUNKS) -> str:
    """Retrieve context from pubmed for Science Researcher. Returns "" on any failure so agent can still run."""
    try:
        if get_index() is None:
            return ""
        return "\n".join(retrieve_texts("pubmed", query, top_k=top_k))
    except Exception as e:
        logger.warning("RAG research context failed (using empty context): %s", e)
        return ""
