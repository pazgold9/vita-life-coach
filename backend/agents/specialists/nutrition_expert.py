"""Nutrition Expert: RAG-backed dietary recommendations (stub until RAG wired)."""
from typing import Any

from backend import llm_client

MODULE_NAME = "Nutrition Expert"


def run(task: str, context: str = "") -> tuple[str, dict[str, Any]]:
    """Run Nutrition Expert on the task. context = RAG-retrieved text when available."""
    messages = [
        {
            "role": "system",
            "content": "You are a nutrition expert. Give precise dietary recommendations. Use the following context when provided.\n\nContext:\n" + (context or "(No context yet)"),
        },
        {"role": "user", "content": task},
    ]
    prompt_for_step = {"messages": messages}
    content, raw = llm_client.chat_with_raw_response(messages)
    return content, {"module": MODULE_NAME, "prompt": prompt_for_step, "response": raw}
