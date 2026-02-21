"""Specialist sub-agents: Nutrition Expert, Science Researcher, Wellness Coach."""
from typing import Any

from backend.agents.specialists.nutrition_expert import run as nutrition_expert_run
from backend.agents.specialists.science_researcher import run as science_researcher_run
from backend.agents.specialists.wellness_coach import run as wellness_coach_run

SPECIALISTS = {
    "Nutrition Expert": nutrition_expert_run,
    "Science Researcher": science_researcher_run,
    "Wellness Coach": wellness_coach_run,
}


def run_specialist(module_name: str, task: str, context: str = "") -> tuple[str, list[dict[str, Any]]]:
    """Run the named specialist. Returns (response_text, steps_list)."""
    fn = SPECIALISTS.get(module_name)
    if not fn:
        raise ValueError(f"Unknown specialist: {module_name}")
    return fn(task, context)
