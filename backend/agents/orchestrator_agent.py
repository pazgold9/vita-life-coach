"""Orchestrator Agent (Head Coach): autonomous ReAct reasoning loop with parallel specialist dispatch."""
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional

from backend import llm_client
from backend.agents.specialists import run_specialist
from backend import db

logger = logging.getLogger(__name__)
MODULE_NAME = "Orchestrator Agent"
MAX_ITERATIONS = 4

_SPECIALIST_ALIASES: dict[str, str] = {
    "nutrition expert": "Nutrition Expert",
    "nutritionexpert": "Nutrition Expert",
    "nutrition": "Nutrition Expert",
    "science researcher": "Science Researcher",
    "scienceresearcher": "Science Researcher",
    "science": "Science Researcher",
    "researcher": "Science Researcher",
    "wellness coach": "Wellness Coach",
    "wellnesscoach": "Wellness Coach",
    "wellness": "Wellness Coach",
    "coach": "Wellness Coach",
}

REACT_SYSTEM_PROMPT = """You are the Head Coach of Vita, an AI wellness and nutrition coach.

Your scope is ONLY: nutrition, diet, food, wellness, exercise, sleep, stress, mindfulness, and health research.

Each turn output exactly one block:

Thought: <reasoning>
Action: <action name>
Action Input: <input>

Available actions:

1) call_specialists
   Call one or more specialists at once. List each on its own line:
   SpecialistName | task description

   Specialists:
     - Nutrition Expert — diet, food, nutrients, meals, ingredients, calorie calculation (has nutrition database + TDEE calculator)
     - Science Researcher — evidence, research, clinical trials, medical facts (has live PubMed search)
     - Wellness Coach — stress, exercise, sleep, mindfulness, habits (has wellness research database)

   Single specialist example:
     Action: call_specialists
     Action Input: Nutrition Expert | List high-protein breakfast options

   Multiple specialists example:
     Action: call_specialists
     Action Input: Nutrition Expert | List vegan high-protein breakfast options
     Science Researcher | Evidence on plant protein for muscle building

2) finish
   Action Input: your complete, friendly final response to the user

Rules:
- Always start with a Thought.
- OFF-TOPIC: If the question is clearly unrelated to health, nutrition, wellness, or fitness (e.g. politics, coding, math homework), call finish immediately with a friendly message: explain that you are a wellness and nutrition coach and cannot help with that topic, and suggest what kinds of questions you CAN help with.
- ALWAYS ANSWER: Even if the user didn't provide every detail (e.g. missing age, activity level), work with what you have and make reasonable assumptions. NEVER block the conversation asking for more info. Instead, give the best answer you can and add a short note at the end like "For a more precise plan, you could share your activity level and any dietary restrictions." The conversation must always flow forward.
- ROUTING: Think carefully about which specialist(s) truly fit the question. Call only those that are needed — one is fine, two or three are fine if the question genuinely spans domains. Use your judgment.
- SUPERVISOR REVIEW: After specialists respond, you MUST review their Observations before finishing:
  * Verify the answers are relevant to the user's actual question (not off-topic).
  * Check for contradictions between specialists — if found, note them honestly.
  * If a specialist returned an error or empty/useless answer, do NOT include it — rely on the others.
  * If you realize another specialist could add meaningful value that is missing, you may call them. But NEVER re-call a specialist that already returned an Observation.
- Once you have verified the information, call finish with a synthesized, quality-checked answer.
- FORMAT YOUR FINAL RESPONSE for easy reading:
  * Start with one short opening sentence that directly answers the question.
  * Then use 2-4 short sections with a bold header each (e.g. **Nutrition**, **What research says**).
  * Each section: 1-3 short sentences. Use bullet points for lists.
  * End with one practical next-step or follow-up suggestion.
  * If PMIDs or references are available, add a small "References" line at the end.
  * Total length: 8-15 lines max. Prefer whitespace and clarity over density.
- Do NOT output anything after the Action Input line.
"""

ProgressCallback = Optional[Callable[[str, dict[str, Any]], None]]


def _normalize_specialist(name: str) -> str:
    key = name.strip().lower()
    if key in _SPECIALIST_ALIASES:
        return _SPECIALIST_ALIASES[key]
    return name.strip()


def _parse_react_output(text: str) -> dict[str, str]:
    thought = ""
    action = ""
    action_input = ""

    thought_match = re.search(r"Thought:\s*(.+?)(?=\nAction:|\Z)", text, re.DOTALL)
    if thought_match:
        thought = thought_match.group(1).strip()

    action_match = re.search(r"Action:\s*(.+?)(?=\nAction Input:|\Z)", text, re.DOTALL)
    if action_match:
        action = action_match.group(1).strip()

    input_match = re.search(r"Action Input:\s*(.+)", text, re.DOTALL)
    if input_match:
        action_input = input_match.group(1).strip()

    return {"thought": thought, "action": action, "action_input": action_input}


def _parse_specialist_lines(action_input: str) -> list[tuple[str, str]]:
    """Parse one or more 'SpecialistName | task' lines from action_input."""
    tasks = []
    for line in action_input.strip().split("\n"):
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts = line.split("|", 1)
        name = _normalize_specialist(parts[0])
        task = parts[1].strip()
        if name and task:
            tasks.append((name, task))

    if not tasks and "|" in action_input:
        parts = action_input.split("|", 1)
        name = _normalize_specialist(parts[0])
        task = parts[1].strip()
        if name and task:
            tasks.append((name, task))

    return tasks


def _execute_specialists(
    action_input: str,
    steps: list[dict[str, Any]],
    on_progress: ProgressCallback = None,
) -> str:
    """Dispatch one or more specialists, running multiple in parallel."""
    tasks = _parse_specialist_lines(action_input)

    if not tasks:
        return "No valid specialist calls found in Action Input. Use format: SpecialistName | task"

    def _summarize(text: str, max_len: int = 100) -> str:
        """First sentence or first max_len chars for progress display."""
        first_line = text.split("\n")[0].split(". ")[0]
        if len(first_line) > max_len:
            return first_line[:max_len] + "..."
        return first_line

    if len(tasks) == 1:
        name, task = tasks[0]
        if on_progress:
            on_progress("specialist_start", {"specialist": name, "task": task, "message": f"{name} is researching: {task}"})
        try:
            response_text, specialist_steps = run_specialist(name, task)
            steps.extend(specialist_steps)
            if on_progress:
                on_progress("specialist_done", {
                    "specialist": name,
                    "message": f"{name} found results",
                    "summary": _summarize(response_text),
                })
            return f"[{name}]: {response_text}"
        except Exception as e:
            logger.exception("Specialist %s failed", name)
            steps.append({"module": name, "prompt": {"task": task}, "response": {"error": str(e)}})
            return f"[{name}] Error: {e}"

    if on_progress:
        names = [n for n, _ in tasks]
        on_progress("specialists_dispatched", {
            "specialists": names,
            "message": f"Consulting {len(tasks)} specialists in parallel: {', '.join(names)}",
        })
        for name, task in tasks:
            on_progress("specialist_start", {"specialist": name, "task": task, "message": f"{name} is researching: {task}"})

    results: dict[str, str] = {}
    all_specialist_steps: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(run_specialist, name, task): name
            for name, task in tasks
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                response_text, specialist_steps = fut.result()
                results[name] = response_text
                all_specialist_steps.extend(specialist_steps)
                if on_progress:
                    on_progress("specialist_done", {
                        "specialist": name,
                        "message": f"{name} completed",
                        "summary": _summarize(response_text),
                    })
            except Exception as e:
                logger.exception("Specialist %s failed", name)
                results[name] = f"Error: {e}"
                all_specialist_steps.append(
                    {"module": name, "prompt": {"task": dict(futures)[name] if False else ""}, "response": {"error": str(e)}}
                )

    steps.extend(all_specialist_steps)

    observations = []
    for name, _ in tasks:
        observations.append(f"[{name}]: {results.get(name, 'No response')}")

    return "\n\n".join(observations)


def _force_finish(prompt: str, scratchpad: str, steps: list[dict[str, Any]]) -> str:
    messages = [
        {"role": "system", "content": "You are the Head Coach of Vita. First, verify the specialist outputs: discard anything irrelevant or contradictory. Then format your response for easy reading: start with a one-sentence direct answer, then 2-4 short sections with bold headers, each 1-3 sentences. Use bullet points for lists. End with a practical next step. Add references (PMIDs) at the end if available. Keep it clean and scannable — no walls of text."},
        {"role": "user", "content": f"User request: {prompt}\n\nSpecialist outputs (review for quality before using):\n{scratchpad}\n\nProvide your verified, final answer:"},
    ]
    final_content, raw_response = llm_client.chat_with_raw_response(messages)
    steps.append({"module": MODULE_NAME, "prompt": {"messages": messages}, "response": raw_response})
    return final_content


_PROFILE_EXTRACT_PROMPT = """Extract any personal details the user shared in this message. Return ONLY a JSON object with the fields that were mentioned. If a field was not mentioned, omit it entirely. Return {} if no personal info was shared.

Fields: name (string), age (integer), sex (male/female), weight_kg (number), height_cm (number), activity_level (sedentary/light/moderate/active/very_active), dietary_restrictions (string), medical_conditions (string), goals (string)

User message: {message}

JSON:"""


def _extract_and_save_profile(prompt: str, conversation_history: list[dict[str, str]]):
    """Try to extract profile info from the user's message without an extra LLM call.

    Uses simple pattern matching — no LLM needed.
    """
    import json as _json
    text = prompt.lower()
    updates: dict[str, Any] = {}

    age_m = re.search(r'(?:(?:ben|בן|בת|age|גיל)[:\s]*(\d{1,3}))|(?:(\d{1,3})\s*(?:years?\s*old|שנים|שנה))', text)
    if age_m:
        val = int(age_m.group(1) or age_m.group(2))
        if 10 <= val <= 120:
            updates["age"] = val

    weight_m = re.search(r'(\d{2,3})\s*(?:kg|קילו|ק"ג|קג|kilo)', text)
    if weight_m:
        updates["weight_kg"] = float(weight_m.group(1))

    height_m = re.search(r'(\d{2,3})\s*(?:cm|ס"מ|סמ|סנטימטר)', text)
    if height_m:
        updates["height_cm"] = float(height_m.group(1))

    if re.search(r'\b(?:male|זכר|גבר)\b', text):
        updates["sex"] = "male"
    elif re.search(r'\b(?:female|נקבה|אישה)\b', text):
        updates["sex"] = "female"

    for level in ["sedentary", "light", "moderate", "active", "very_active"]:
        if level.replace("_", " ") in text or level in text:
            updates["activity_level"] = level
            break

    diet_keywords = {
        "vegan": "vegan", "צמחוני": "vegetarian", "vegetarian": "vegetarian",
        "טבעוני": "vegan", "gluten": "gluten-free", "גלוטן": "gluten-free",
        "kosher": "kosher", "כשר": "kosher", "lactose": "lactose-free",
    }
    for kw, val in diet_keywords.items():
        if kw in text:
            updates["dietary_restrictions"] = val
            break

    goal_keywords = {
        "lose weight": "weight loss", "לרדת במשקל": "weight loss",
        "gain muscle": "muscle gain", "לעלות במסה": "muscle gain",
        "bulk": "muscle gain", "cut": "weight loss", "דיאטה": "weight loss",
        "maintain": "maintenance",
    }
    for kw, val in goal_keywords.items():
        if kw in text:
            updates["goals"] = val
            break

    if updates:
        db.update_profile(updates)
        logger.info("Profile updated: %s", updates)


def run(
    prompt: str,
    conversation_history: list[dict[str, str]] | None = None,
    on_progress: ProgressCallback = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Run the orchestrator ReAct loop. Returns (final_response, steps)."""
    steps: list[dict[str, Any]] = []
    scratchpad = ""

    _extract_and_save_profile(prompt, conversation_history or [])

    profile_summary = db.get_profile_summary()
    profile_block = ""
    if profile_summary:
        profile_block = f"Known user profile:\n{profile_summary}\n\n"

    history_block = ""
    if conversation_history:
        recent = conversation_history[-10:]
        history_block = "Previous conversation:\n"
        for turn in recent:
            history_block += f"{turn['role'].capitalize()}: {turn['content']}\n"
        history_block += "\n"

    if on_progress:
        on_progress("orchestrator_start", {"message": "Analyzing your question..."})

    for iteration in range(MAX_ITERATIONS):
        user_content = f"{profile_block}{history_block}User request: {prompt}\n\n{scratchpad}".strip()
        messages = [
            {"role": "system", "content": REACT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        if on_progress:
            on_progress("orchestrator_thinking", {
                "iteration": iteration + 1,
                "message": "Deciding which experts to consult..." if iteration == 0 else "Reviewing specialist findings...",
            })

        llm_output, raw_response = llm_client.chat_with_raw_response(messages)
        steps.append({"module": MODULE_NAME, "prompt": {"messages": messages}, "response": raw_response})

        parsed = _parse_react_output(llm_output)
        thought = parsed["thought"]
        action = parsed["action"]
        action_input = parsed["action_input"]

        logger.info("Iteration %d — Thought: %s | Action: %s", iteration + 1, thought[:80], action[:80] if action else "")

        if on_progress and thought:
            short_thought = thought[:120] + ("..." if len(thought) > 120 else "")
            on_progress("orchestrator_thought", {"message": short_thought})

        if action.lower().strip() == "finish":
            if on_progress:
                on_progress("composing", {"message": "Composing your answer..."})
            return action_input, steps
        finish_match = re.match(r"finish\(\s*(.+?)\s*\)$", action, re.DOTALL | re.IGNORECASE)
        if finish_match:
            if on_progress:
                on_progress("composing", {"message": "Composing your answer..."})
            return finish_match.group(1), steps

        action_key = action.lower().strip()
        if action_key in ("call_specialists", "call_specialist", "call_specialist()"):
            observation = _execute_specialists(action_input, steps, on_progress)
        elif action_key.startswith("call_specialist"):
            observation = _execute_specialists(action_input, steps, on_progress)
        else:
            observation = f"Unknown action: {action}. Use call_specialists or finish."

        scratchpad += f"\nThought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: {observation}\n"

    logger.warning("Max iterations (%d) reached, forcing synthesis.", MAX_ITERATIONS)
    if on_progress:
        on_progress("composing", {"message": "Composing your answer..."})
    return _force_finish(prompt, scratchpad, steps), steps
