"""Ingest real PubMed abstracts on wellness topics into Pinecone namespace 'wellness'.

Uses NCBI E-utilities (free, no API key required for moderate use):
  - esearch: find PMIDs for a search term
  - efetch: fetch title + abstract XML for those PMIDs

Every record stored has a real PMID, real title, and real abstract straight from NCBI.
"""
import logging
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote_plus

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend import config
from backend.rag.embedder import embed
from backend.rag.pinecone_client import get_index, upsert_vectors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NAMESPACE = "wellness"
BATCH_SIZE = 50
PER_TOPIC = 60

WELLNESS_TOPICS = [
    "exercise physical activity health benefits",
    "sleep hygiene insomnia interventions",
    "stress management coping techniques",
    "mindfulness meditation mental health",
    "healthy habits behavior change wellness",
]

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _fetch_url(url: str) -> bytes:
    resp = requests.get(url, headers={"User-Agent": "VitaLifeCoach/1.0"}, timeout=30)
    resp.raise_for_status()
    return resp.content


def search_pmids(term: str, max_results: int = PER_TOPIC) -> list[str]:
    url = f"{ESEARCH_URL}?db=pubmed&term={quote_plus(term)}&retmax={max_results}&sort=relevance&retmode=xml"
    data = _fetch_url(url)
    root = ET.fromstring(data)
    return [id_el.text for id_el in root.findall(".//Id") if id_el.text]


def fetch_abstracts(pmids: list[str]) -> list[dict]:
    """Fetch title + abstract for a list of PMIDs. Returns list of {pmid, title, abstract}."""
    if not pmids:
        return []
    ids_str = ",".join(pmids)
    url = f"{EFETCH_URL}?db=pubmed&id={ids_str}&retmode=xml"
    data = _fetch_url(url)
    root = ET.fromstring(data)

    records = []
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        title_el = article.find(".//ArticleTitle")
        abstract_el = article.find(".//Abstract")

        pmid = pmid_el.text if pmid_el is not None else ""
        title = title_el.text if title_el is not None else ""

        abstract_parts = []
        if abstract_el is not None:
            for at in abstract_el.findall("AbstractText"):
                label = at.get("Label", "")
                text = "".join(at.itertext()).strip()
                if text:
                    abstract_parts.append(f"{label}: {text}" if label else text)
        abstract = " ".join(abstract_parts)

        if title and abstract and len(abstract) >= 50:
            records.append({"pmid": pmid, "title": title, "abstract": abstract})

    return records


def main():
    if not config.PINECONE_API_KEY or not config.LLMOD_API_KEY:
        logger.error("Set PINECONE_API_KEY and LLMOD_API_KEY in .env")
        return 1

    idx = get_index()
    if idx is None:
        logger.error("Pinecone index not available")
        return 1

    all_records = []
    seen_pmids = set()

    for topic in WELLNESS_TOPICS:
        logger.info("Searching PubMed for: %s", topic)
        pmids = search_pmids(topic, PER_TOPIC)
        logger.info("  Found %d PMIDs", len(pmids))

        if not pmids:
            continue

        time.sleep(0.4)  # respect NCBI rate limit

        records = fetch_abstracts(pmids)
        for r in records:
            if r["pmid"] not in seen_pmids:
                seen_pmids.add(r["pmid"])
                all_records.append(r)

        logger.info("  Fetched %d unique abstracts (total so far: %d)", len(records), len(all_records))
        time.sleep(0.4)

    if not all_records:
        logger.error("No records fetched from PubMed")
        return 1

    logger.info("Total unique records: %d", len(all_records))

    # Build text chunks: "PMID: X | Title | Abstract"
    texts = []
    ids = []
    for r in all_records:
        text = f"PMID: {r['pmid']}\nTitle: {r['title']}\n\n{r['abstract']}"
        texts.append(text[:8000])
        ids.append(f"wellness_{r['pmid']}")

    logger.info("Embedding %d texts in batches of %d...", len(texts), BATCH_SIZE)
    all_vectors = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        all_vectors.extend(embed(batch))
        logger.info("  Embedded %d / %d", min(start + BATCH_SIZE, len(texts)), len(texts))

    metadatas = [{"text": t, "pmid": r["pmid"], "title": r["title"]} for t, r in zip(texts, all_records)]

    logger.info("Upserting to namespace '%s'...", NAMESPACE)
    for start in range(0, len(ids), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(ids))
        upsert_vectors(NAMESPACE, ids[start:end], all_vectors[start:end], metadatas[start:end])
        logger.info("  Upserted %d / %d", end, len(ids))

    logger.info("Done. %d vectors in namespace '%s'", len(ids), NAMESPACE)

    # Print sample for verification
    logger.info("\n--- SAMPLE RECORDS (first 3) ---")
    for r in all_records[:3]:
        logger.info("PMID: %s | Title: %s | Abstract: %s...", r["pmid"], r["title"], r["abstract"][:150])

    return 0


if __name__ == "__main__":
    sys.exit(main())
