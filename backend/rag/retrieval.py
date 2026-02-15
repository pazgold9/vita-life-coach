"""RAG retrieval: query by namespace and return context string for prompts."""
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.rag.embedder import embed_single
from backend.rag.pinecone_client import query_by_vector, retrieve_texts

MAX_CHUNKS = 3  # fewer chunks = faster Pinecone + smaller prompts


def get_nutrition_context(query: str, top_k: int = MAX_CHUNKS) -> str:
    """Retrieve context from openfoodfacts and usda in parallel (one embedding, two parallel queries)."""
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


def get_research_context(query: str, top_k: int = MAX_CHUNKS) -> str:
    """Retrieve context from pubmed for Science Researcher."""
    return "\n".join(retrieve_texts("pubmed", query, top_k=top_k))
