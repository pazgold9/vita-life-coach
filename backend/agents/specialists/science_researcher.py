"""Science Researcher: RAG-backed evidence-based answers (stub until RAG wired)."""
from typing import Any

from backend import llm_client

MODULE_NAME = "Science Researcher"


def run(task: str, context: str = "") -> tuple[str, dict[str, Any]]:
    """Run Science Researcher on the task. context = RAG-retrieved research when available."""
    messages = [
        {
            "role": "system",
            "content": "You are a science researcher. Answer wellness and health questions using evidence-based medical research. Use the following context when provided.\n\nContext:\n" + (context or "(No context yet)"),
        },
        {"role": "user", "content": task},
    ]
    prompt_for_step = {"messages": messages}
    content, raw = llm_client.chat_with_raw_response(messages)
    return content, {"module": MODULE_NAME, "prompt": prompt_for_step, "response": raw}
