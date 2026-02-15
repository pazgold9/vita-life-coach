"""Embedding via LLMod.ai (OpenAI-compatible)."""
from backend import config
from backend import llm_client


def embed(texts: list[str]) -> list[list[float]]:
    """Return embeddings for the given texts."""
    return llm_client.embed(texts, model=config.LLMOD_EMBEDDING_MODEL)


def embed_single(text: str) -> list[float]:
    """Return embedding for a single text."""
    return embed([text])[0]
