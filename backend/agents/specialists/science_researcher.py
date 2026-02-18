"""Science Researcher: autonomous RAG + live PubMed search agent."""
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote_plus

from backend import llm_client
from backend.rag.retrieval import get_research_context

logger = logging.getLogger(__name__)
MODULE_NAME = "Science Researcher"
MAX_ITERATIONS = 2

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _search_pubmed_live(query: str, max_results: int = 5) -> str:
    """Search PubMed in real-time via NCBI E-utilities. Returns formatted abstracts with PMIDs.

    Falls back to static RAG if the live API fails.
    """
    try:
        import requests

        search_url = f"{ESEARCH_URL}?db=pubmed&term={quote_plus(query)}&retmax={max_results}&sort=relevance&retmode=xml"
        resp = requests.get(search_url, headers={"User-Agent": "VitaLifeCoach/1.0"}, timeout=8)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        pmids = [el.text for el in root.findall(".//Id") if el.text]

        if not pmids:
            logger.info("Live PubMed returned no results for '%s', falling back to RAG", query)
            return get_research_context(query) or "No research data found."

        ids_str = ",".join(pmids[:max_results])
        fetch_url = f"{EFETCH_URL}?db=pubmed&id={ids_str}&retmode=xml"
        resp2 = requests.get(fetch_url, headers={"User-Agent": "VitaLifeCoach/1.0"}, timeout=10)
        resp2.raise_for_status()
        fetch_root = ET.fromstring(resp2.content)

        results = []
        for article in fetch_root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//PMID")
            title_el = article.find(".//ArticleTitle")
            abstract_el = article.find(".//Abstract")

            pmid = pmid_el.text if pmid_el is not None else ""
            title = title_el.text if title_el is not None else ""

            abstract_parts = []
            if abstract_el is not None:
                for at in abstract_el.findall("AbstractText"):
                    text = "".join(at.itertext()).strip()
                    if text:
                        abstract_parts.append(text)
            abstract = " ".join(abstract_parts)

            if title and abstract and len(abstract) >= 30:
                results.append(f"PMID: {pmid}\nTitle: {title}\nAbstract: {abstract[:600]}")

        if results:
            return "\n\n---\n\n".join(results)

        logger.info("Live PubMed fetch returned no usable abstracts, falling back to RAG")
        return get_research_context(query) or "No research data found."

    except Exception as e:
        logger.warning("Live PubMed search failed (%s), falling back to static RAG", e)
        return get_research_context(query) or "No research data found."


REACT_SYSTEM_PROMPT = """You are a Science Researcher specialising in evidence-based health and wellness research.

You ONLY handle research and evidence topics: clinical trials, meta-analyses, scientific evidence, medical facts, study findings.
You do NOT handle: meal planning, specific food recommendations, exercise programs, lifestyle coaching.

Each turn output exactly one block:

Thought: <your reasoning>
Action: <one action>
Action Input: <input>

Available actions:
- search_pubmed_live(<query>) — search PubMed in real-time for the latest studies (returns titles, abstracts, and PMIDs)
- search_research(<query>) — search local PubMed database for relevant studies
- finish(<response>) — return your final, evidence-based answer

Rules:
- You MUST search on your first turn. Prefer search_pubmed_live() for the latest evidence. Use search_research() as backup.
- After seeing the Observation, DECIDE: if results are sufficient, call finish(). If results are empty or not relevant enough, search again with a different query.
- Always include PMIDs in your answer so the user can verify.
- Keep search queries short and specific (e.g. "creatine supplementation muscle strength meta-analysis").
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
    """Run Science Researcher ReAct loop. Returns (response_text, steps_list)."""
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

        live_match = re.match(r"search_pubmed_live\(\s*(.+?)\s*\)$", action, re.DOTALL)
        static_match = re.match(r"search_research\(\s*(.+?)\s*\)$", action, re.DOTALL)

        if live_match:
            query = live_match.group(1)
            observation = _search_pubmed_live(query)
        elif static_match:
            query = static_match.group(1)
            result = get_research_context(query)
            observation = result or "No research data found."
        else:
            observation = f"Unknown action: {action}. Use search_pubmed_live(), search_research(), or finish()."

        scratchpad += f"\nThought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: {observation}\n"

    messages = [
        {"role": "system", "content": "You are a Science Researcher. Give a clear, structured answer: state the key finding first, then supporting evidence in bullet points. Include PMIDs. Keep it under 8 sentences."},
        {"role": "user", "content": f"Task: {task}\n\n{scratchpad}\n\nFinal answer:"},
    ]
    content, raw = llm_client.chat_with_raw_response(messages)
    steps.append({"module": MODULE_NAME, "prompt": {"messages": messages}, "response": raw})
    return content, steps
