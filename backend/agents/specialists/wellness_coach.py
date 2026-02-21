"""Wellness Coach: autonomous RAG-backed agent for stress, exercise, sleep, mindfulness."""
import logging
import re
from typing import Any

from backend import llm_client
from backend.rag.retrieval import get_wellness_context

logger = logging.getLogger(__name__)
MODULE_NAME = "Wellness Coach"
MAX_ITERATIONS = 2

REACT_SYSTEM_PROMPT = """You are a Wellness Coach specialising in stress relief, exercise, sleep, mindfulness, and healthy habits.

You ONLY handle wellness topics: exercise, stress, sleep, mindfulness, habits, mental wellbeing.
You do NOT handle: specific food/nutrient recommendations, calorie calculations, research paper analysis.

Each turn output exactly one block:

Thought: <your reasoning>
Action: <one action>
Action Input: <input>

Available actions:
- search_wellness(<query>) — search PubMed research on exercise, sleep, stress, mindfulness
- finish(<response>) — return your final, practical and actionable answer

Rules:
- You MUST call search_wellness() on your first turn to ground your answer in real research. NEVER skip the search.
- After seeing the Observation, DECIDE: if results are sufficient, call finish(). If results are empty or not relevant enough, search again with a different query.
- Keep search queries short and specific (e.g. "stress reduction techniques", "sleep hygiene interventions").
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
    """Run Wellness Coach ReAct loop. Returns (response_text, steps_list)."""
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

        sw_match = re.match(r"search_wellness\(\s*(.+?)\s*\)$", action, re.DOTALL)
        if sw_match:
            query = sw_match.group(1)
            result = get_wellness_context(query)
            observation = result or "No wellness research data found."
        else:
            observation = f"Unknown action: {action}. Use search_wellness() or finish()."

        scratchpad += f"\nThought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: {observation}\n"

    messages = [
        {"role": "system", "content": "You are a Wellness Coach. Give a clear, structured answer: one key takeaway first, then actionable tips as bullet points. Include PMIDs when relevant. Keep it under 8 sentences."},
        {"role": "user", "content": f"Task: {task}\n\n{scratchpad}\n\nFinal answer:"},
    ]
    content, raw = llm_client.chat_with_raw_response(messages)
    steps.append({"module": MODULE_NAME, "prompt": {"messages": messages}, "response": raw})
    return content, steps
