"""Orchestrator Agent (Head Coach): plan, route to specialists, synthesize."""
import json
import logging
import re
from typing import Any

from backend import llm_client
from backend.agents.specialists import run_specialist
from backend.rag.retrieval import get_nutrition_context, get_research_context

logger = logging.getLogger(__name__)
MODULE_NAME = "Orchestrator Agent"

PLAN_PROMPT = """You are the Head Coach of Vita, an AI wellness and nutrition coach. Given the user's request, break it into 1-3 clear sub-tasks and assign each to exactly one specialist.

Specialists:
- "Nutrition Expert": diet, food, nutrients, meals, branded products, ingredients, Nutri-score.
- "Science Researcher": evidence, research, clinical trials, medical facts, "is X supported by science".
- "Wellness Coach": stress, exercise, sleep, mindfulness, non-diet habits.

Reply with ONLY a JSON array, no other text. Each element: {"task": "sub-task description", "specialist": "Nutrition Expert"|"Science Researcher"|"Wellness Coach"}.
Example: [{"task": "Suggest a healthy breakfast", "specialist": "Nutrition Expert"}, {"task": "Is it evidence-based?", "specialist": "Science Researcher"}]

User request:
"""
SYNTHESIS_PROMPT = """You are the Head Coach of Vita. Below are the user's request and the specialists' answers. Write one concise, friendly final response that addresses the user's request. Do not repeat raw outputs; integrate them into a coherent answer.

User request: {user_prompt}

Specialist answers:
{specialist_outputs}

Final response:
"""


def _parse_plan(raw: str) -> list[dict[str, str]]:
    """Extract JSON array of {task, specialist} from LLM output."""
    raw = raw.strip()
    # Try to find a JSON array
    match = re.search(r"\[[\s\S]*\]", raw)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                out = []
                for item in data:
                    if isinstance(item, dict) and "task" in item and "specialist" in item:
                        spec = item["specialist"]
                        if spec in ("Nutrition Expert", "Science Researcher", "Wellness Coach"):
                            out.append({"task": str(item["task"]), "specialist": spec})
                if out:
                    return out
        except json.JSONDecodeError:
            pass
    return [{"task": raw or "Address the user request.", "specialist": "Wellness Coach"}]


def run(prompt: str) -> tuple[str, list[dict[str, Any]]]:
    """Run the orchestrator: plan, call specialists, synthesize. Returns (final_response, steps)."""
    steps: list[dict[str, Any]] = []

    # 1. Plan + route
    plan_messages = [
        {"role": "system", "content": "You output only valid JSON. No markdown, no explanation."},
        {"role": "user", "content": PLAN_PROMPT + prompt},
    ]
    plan_content, plan_raw = llm_client.chat_with_raw_response(plan_messages)
    steps.append({"module": MODULE_NAME, "prompt": {"messages": plan_messages}, "response": plan_raw})

    sub_tasks = _parse_plan(plan_content)

    # 2. Call specialists (RAG context for Nutrition / Science)
    specialist_outputs: list[str] = []
    for i, st in enumerate(sub_tasks):
        task, specialist = st["task"], st["specialist"]
        context = ""
        if specialist == "Nutrition Expert":
            context = get_nutrition_context(task)
        elif specialist == "Science Researcher":
            context = get_research_context(task)
        try:
            response_text, step_dict = run_specialist(specialist, task, context=context)
            specialist_outputs.append(f"[{specialist}] {task}\n{response_text}")
            steps.append(step_dict)
        except Exception as e:
            logger.exception("Specialist %s failed", specialist)
            specialist_outputs.append(f"[{specialist}] {task}\nError: {e}")
            steps.append({
                "module": specialist,
                "prompt": {"task": task},
                "response": {"error": str(e)},
            })

    # 3. Synthesize
    combined = "\n\n".join(specialist_outputs)
    synth_messages = [
        {"role": "user", "content": SYNTHESIS_PROMPT.format(user_prompt=prompt, specialist_outputs=combined)},
    ]
    final_content, synth_raw = llm_client.chat_with_raw_response(synth_messages)
    steps.append({"module": MODULE_NAME, "prompt": {"messages": synth_messages}, "response": synth_raw})

    return final_content, steps
