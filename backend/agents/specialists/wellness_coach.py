"""Wellness Coach: non-diet protocols (stress, exercise)."""
from typing import Any

from backend import llm_client

MODULE_NAME = "Wellness Coach"


def run(task: str, context: str = "") -> tuple[str, dict[str, Any]]:
    """Run Wellness Coach on the task. No RAG; LLM-only."""
    messages = [
        {
            "role": "system",
            "content": "You are a wellness coach. Provide non-diet protocols: stress relief, exercise, sleep, mindfulness. Be practical and actionable.",
        },
        {"role": "user", "content": task},
    ]
    prompt_for_step = {"messages": messages}
    content, raw = llm_client.chat_with_raw_response(messages)
    return content, {"module": MODULE_NAME, "prompt": prompt_for_step, "response": raw}
