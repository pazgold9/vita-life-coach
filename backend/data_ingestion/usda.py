"""Ingest USDA FoodData Central (CSV from Kaggle) into Pinecone namespace 'usda'."""
import csv
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend import config
from backend.rag.embedder import embed
from backend.rag.pinecone_client import get_index, upsert_vectors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
NAMESPACE = "usda"
BATCH_SIZE = 50
# Path to CSV: download from https://www.kaggle.com/datasets/joebeachcapital/fooddata-central
USDA_CSV = Path(__file__).resolve().parent.parent.parent / "data" / "fooddata-central.csv"
MAX_ROWS = 10000


def build_text(row: dict) -> str:
    """Build a single text chunk from a USDA row."""
    parts = []
    desc = (row.get("description") or row.get("description_upper") or row.get("food_description") or "").strip()
    if desc:
        parts.append(desc)
    fdc_id = row.get("fdc_id") or row.get("id") or ""
    if fdc_id:
        parts.append(f"FDC ID: {fdc_id}")
    # Common nutrient columns if present
    for key in ("protein", "carbohydrates", "fat", "energy", "fiber", "sugars"):
        if key in row and row[key] not in ("", None):
            parts.append(f"{key}: {row[key]}")
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
    if not USDA_CSV.exists():
        logger.error(
            "USDA CSV not found at %s. Download from https://www.kaggle.com/datasets/joebeachcapital/fooddata-central and place CSV as data/fooddata-central.csv",
            USDA_CSV,
        )
        return 1
    texts = []
    ids = []
    with open(USDA_CSV, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        for i, row in enumerate(reader):
            if i >= MAX_ROWS:
                break
            t = build_text(row)
            if not t or len(t) < 15:
                continue
            texts.append(t)
            ids.append(f"usda_{i}")
    if not texts:
        logger.error("No valid texts from USDA CSV (check column names: %s)", columns)
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
