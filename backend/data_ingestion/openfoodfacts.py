"""Ingest Open Food Facts (Hugging Face) into Pinecone namespace 'openfoodfacts'."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend import config
from backend.rag.embedder import embed
from backend.rag.pinecone_client import get_index, upsert_vectors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
NAMESPACE = "openfoodfacts"
BATCH_SIZE = 50
MAX_ROWS = 50000  # sample for budget; increase if needed


def build_text(row: dict) -> str:
    """Build a single text chunk from an Open Food Facts row."""
    parts = []
    name = (row.get("product_name") or row.get("product_name_en") or "").strip()
    if name:
        parts.append(f"Product: {name}")
    brands = (row.get("brands") or "").strip()
    if brands:
        parts.append(f"Brands: {brands}")
    ingredients = (row.get("ingredients_text") or "").strip()
    if ingredients:
        parts.append(f"Ingredients: {ingredients[:1500]}")
    nutriscore = (row.get("nutriscore_grade") or "").strip()
    if nutriscore:
        parts.append(f"Nutri-score: {nutriscore}")
    categories = (row.get("categories") or "").strip()
    if categories:
        parts.append(f"Categories: {categories[:500]}")
    if not parts:
        return ""
    return "\n".join(parts)[:8000]


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
    logger.info("Loading openfoodfacts/product-database...")
    ds = load_dataset("openfoodfacts/product-database", trust_remote_code=True)
    if "train" in ds:
        ds = ds["train"]
    else:
        ds = ds[list(ds.keys())[0]]
    texts = []
    ids = []
    n = 0
    for i in range(min(MAX_ROWS, len(ds))):
        if n >= 500:
            break
        row = ds[i]
        if hasattr(row, "keys"):
            r = dict(row)
        else:
            r = dict(zip(ds.column_names, row)) if hasattr(ds, "column_names") else {}
        t = build_text(r)
        if not t or len(t) < 30:
            continue
        texts.append(t)
        ids.append(f"off_{n}")
        n += 1
    if not texts:
        logger.error("No valid texts from Open Food Facts")
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
