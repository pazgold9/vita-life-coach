"""Ingest PubMed Summarization dataset (Hugging Face) into Pinecone namespace 'pubmed'."""
import logging
import sys
from pathlib import Path

# Run from project root so backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend import config
from backend.rag.embedder import embed
from backend.rag.pinecone_client import get_index, upsert_vectors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
NAMESPACE = "pubmed"
BATCH_SIZE = 50
MAX_TEXTS = 2000  # cap for budget; increase if needed


def build_text(record: dict) -> str:
    """Build a single text chunk from a PubMed record."""
    article = (record.get("article") or record.get("Article") or "").strip()
    abstract = (record.get("abstract") or record.get("abstractive_summary") or record.get("summary") or "").strip()
    if article and abstract:
        return f"{article}\n\n{abstract}"
    return article or abstract or ""


def main():
    if not config.PINECONE_API_KEY or not config.LLMOD_API_KEY:
        logger.error("Set PINECONE_API_KEY and LLMOD_API_KEY")
        return 1
    idx = get_index()
    if idx is None:
        logger.error("Pinecone index not available")
        return 1
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("Install datasets: pip install datasets")
        return 1
    logger.info("Loading ccdv/pubmed-summarization...")
    try:
        ds = load_dataset("ccdv/pubmed-summarization", "section", trust_remote_code=True)
    except Exception:
        ds = load_dataset("ccdv/pubmed-summarization", split="train", trust_remote_code=True)
    if isinstance(ds, dict):
        if "train" in ds:
            ds = ds["train"]
        else:
            ds = ds[list(ds.keys())[0]]
    texts = []
    ids = []
    for i, row in enumerate(ds):
        if i >= MAX_TEXTS:
            break
        t = build_text(row)
        if not t or len(t) < 20:
            continue
        texts.append(t[:8000])  # limit chunk size
        ids.append(f"pubmed_{i}")
    if not texts:
        logger.error("No valid texts")
        return 1
    logger.info("Embedding %d texts in batches of %d...", len(texts), BATCH_SIZE)
    all_vectors = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        all_vectors.extend(embed(batch))
        logger.info("Embedded %d / %d", min(start + BATCH_SIZE, len(texts)), len(texts))
    metadatas = [{"text": t} for t in texts]
    logger.info("Upserting to namespace %s...", NAMESPACE)
    for start in range(0, len(ids), BATCH_SIZE):
        end = start + BATCH_SIZE
        upsert_vectors(NAMESPACE, ids[start:end], all_vectors[start:end], metadatas[start:end])
        logger.info("Upserted %d / %d", end, len(ids))
    logger.info("Done. %d vectors in %s", len(ids), NAMESPACE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
