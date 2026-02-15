"""OpenAI-compatible LLM client for LLMod.ai."""
import logging
from typing import Any, Optional

from openai import OpenAI

from backend import config

logger = logging.getLogger(__name__)

_client = None  # Optional[OpenAI]


def get_client() -> OpenAI:
    """Return a singleton OpenAI-compatible client (LLMod.ai)."""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=config.LLMOD_API_KEY or "not-set",
            base_url=config.LLMOD_BASE_URL,
        )
    return _client


def chat(
    messages: list,
    model: Optional[str] = None,
) -> str:
    """
    Send a chat completion request and return the assistant message content.
    messages: list of {"role": "user"|"system"|"assistant", "content": "..."}
    """
    client = get_client()
    model = model or config.LLMOD_MODEL
    resp = client.chat.completions.create(model=model, messages=messages)
    if not resp.choices:
        raise ValueError("Empty completion response")
    return resp.choices[0].message.content or ""


def _resp_to_dict(resp):
    """Convert API response to plain dict for logging (avoid non-JSON types)."""
    try:
        if hasattr(resp, "model_dump"):
            return resp.model_dump()
        if hasattr(resp, "dict"):
            return resp.dict()
    except Exception:
        pass
    content = ""
    if getattr(resp, "choices", None) and len(resp.choices) > 0:
        content = getattr(resp.choices[0].message, "content", "") or ""
    return {"choices": [{"message": {"content": content}}]}


def chat_with_raw_response(
    messages: list,
    model: Optional[str] = None,
):
    """
    Same as chat() but also return the raw API response for step logging.
    Returns (content, raw_response_dict).
    """
    client = get_client()
    model = model or config.LLMOD_MODEL
    resp = client.chat.completions.create(model=model, messages=messages)
    if not resp.choices:
        raise ValueError("Empty completion response")
    content = resp.choices[0].message.content or ""
    raw = _resp_to_dict(resp)
    return content, raw


def embed(texts: list, model: Optional[str] = None):
    """Return embeddings for the given texts. Uses config embedding model."""
    if not texts:
        return []
    client = get_client()
    model = model or config.LLMOD_EMBEDDING_MODEL
    resp = client.embeddings.create(input=texts, model=model)
    return [e.embedding for e in resp.data]
