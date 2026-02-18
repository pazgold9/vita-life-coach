"""Nutrition Expert: autonomous RAG-backed dietary recommendations agent with TDEE calculator."""
import logging
import re
from typing import Any

from backend import llm_client
from backend.rag.retrieval import get_nutrition_context

logger = logging.getLogger(__name__)
MODULE_NAME = "Nutrition Expert"
MAX_ITERATIONS = 2


def _calculate_tdee(params_str: str) -> str:
    """Pure math — Mifflin-St Jeor equation. No LLM call.

    Expected input: "weight_kg, height_cm, age, sex, activity_level"
    activity_level: sedentary | light | moderate | active | very_active
    """
    try:
        parts = [p.strip().lower() for p in params_str.split(",")]
        if len(parts) < 5:
            return "Error: provide weight_kg, height_cm, age, sex (male/female), activity_level (sedentary/light/moderate/active/very_active)"

        weight = float(parts[0])
        height = float(parts[1])
        age = int(parts[2])
        sex = parts[3]
        activity = parts[4]

        if sex.startswith("m"):
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        multipliers = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "active": 1.725,
            "very_active": 1.9,
        }
        mult = multipliers.get(activity, 1.55)
        tdee = round(bmr * mult)

        protein_min = round(weight * 1.2)
        protein_max = round(weight * 2.0)

        return (
            f"BMR (Mifflin-St Jeor): {round(bmr)} kcal/day\n"
            f"TDEE at '{activity}' activity: {tdee} kcal/day\n"
            f"Weight loss (~500 kcal deficit): {tdee - 500} kcal/day\n"
            f"Weight gain (~300 kcal surplus): {tdee + 300} kcal/day\n"
            f"Protein target: {protein_min}–{protein_max} g/day (1.2–2.0 g/kg)"
        )
    except (ValueError, IndexError) as e:
        return f"Error parsing inputs: {e}. Format: weight_kg, height_cm, age, sex, activity_level"


REACT_SYSTEM_PROMPT = """You are a Nutrition Expert specialising in dietary recommendations, food composition, and meal planning.

You ONLY handle nutrition topics: diet, food, nutrients, meals, ingredients, calories, macros, meal planning.
You do NOT handle: exercise programs, mental health, stress, sleep, research papers.

Each turn output exactly one block:

Thought: <your reasoning>
Action: <one action>
Action Input: <input>

Available actions:
- search_nutrition(<query>) — search Open Food Facts + USDA for food/nutrient data
- calculate_tdee(<weight_kg>, <height_cm>, <age>, <sex>, <activity_level>) — calculate daily calorie needs using Mifflin-St Jeor. Activity levels: sedentary, light, moderate, active, very_active.
- finish(<response>) — return your final answer

Rules:
- You MUST call search_nutrition() on your first turn to ground your answer in real data. NEVER skip the search.
- After seeing the Observation, DECIDE: if results are sufficient, call finish(). If results are empty or not relevant enough, search again with a different query. You can also call calculate_tdee() as a second action if needed.
- Use calculate_tdee() when the user provides their weight, height, age, sex, and activity level (or you can reasonably infer them).
- Keep search queries short and specific (e.g. "high protein breakfast foods").
- Do NOT output anything after "Action Input:".
"""


def _parse_react(text: str) -> dict[str, str]:
    thought = action = action_input = ""
    m = re.search(r"Thought:\s*(.+?)(?=\nAction:|\Z)", text, re.DOTALL)
    if m:
        thought = m.group(1).strip()
    m = re.search(r"Action:\s*(.+?)(?=\nAction Input:|\Z)", text, re.DOTALL)
    if m:
        action = m.group(1).strip()
    m = re.search(r"Action Input:\s*(.+)", text, re.DOTALL)
    if m:
        action_input = m.group(1).strip()
    return {"thought": thought, "action": action, "action_input": action_input}


def run(task: str, context: str = "") -> tuple[str, list[dict[str, Any]]]:
    """Run Nutrition Expert ReAct loop. Returns (response_text, steps_list)."""
    steps: list[dict[str, Any]] = []
    scratchpad = ""
    if context:
        scratchpad = f"Pre-loaded context:\n{context}\n"

    for _ in range(MAX_ITERATIONS):
        messages = [
            {"role": "system", "content": REACT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}\n\n{scratchpad}".strip()},
        ]
        llm_output, raw = llm_client.chat_with_raw_response(messages)
        steps.append({"module": MODULE_NAME, "prompt": {"messages": messages}, "response": raw})

        parsed = _parse_react(llm_output)
        thought = parsed["thought"]
        action = parsed["action"]
        action_input = parsed["action_input"]

        finish_match = re.match(r"finish\(\s*(.+?)\s*\)$", action, re.DOTALL | re.IGNORECASE)
        if finish_match:
            return finish_match.group(1), steps
        if action.lower() == "finish":
            return action_input, steps

        sn_match = re.match(r"search_nutrition\(\s*(.+?)\s*\)$", action, re.DOTALL)
        tdee_match = re.match(r"calculate_tdee\(\s*(.+?)\s*\)$", action, re.DOTALL)

        if sn_match:
            query = sn_match.group(1)
            result = get_nutrition_context(query)
            observation = result or "No nutrition data found."
        elif tdee_match:
            observation = _calculate_tdee(tdee_match.group(1))
        elif "calculate_tdee" in action.lower():
            observation = _calculate_tdee(action_input)
        else:
            observation = f"Unknown action: {action}. Use search_nutrition(), calculate_tdee(), or finish()."

        scratchpad += f"\nThought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: {observation}\n"

    messages = [
        {"role": "system", "content": "You are a Nutrition Expert. Give a clear, structured answer: use short bullet points or numbered lists for food items. Cite data sources when available. Keep it under 8 sentences."},
        {"role": "user", "content": f"Task: {task}\n\n{scratchpad}\n\nFinal answer:"},
    ]
    content, raw = llm_client.chat_with_raw_response(messages)
    steps.append({"module": MODULE_NAME, "prompt": {"messages": messages}, "response": raw})
    return content, steps
