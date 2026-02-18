"""Entry point: run the orchestrator and return response + steps."""
from typing import Any, Callable, Optional

from backend.agents.orchestrator_agent import run as orchestrator_run


def run_agent(
    prompt: str,
    conversation_history: Optional[list[dict[str, str]]] = None,
    on_progress: Optional[Callable] = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Run the Vita agent on the user prompt. Returns (final_response, steps)."""
    return orchestrator_run(
        prompt,
        conversation_history=conversation_history or [],
        on_progress=on_progress,
    )
