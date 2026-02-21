"""Application configuration from environment variables."""
import os
from pathlib import Path

# Load .env from project root (vita_life_coach/) if present
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
except ImportError:
    pass

# Project
BASE_DIR = Path(__file__).resolve().parent.parent

# API / Team (fill in for submission)
GROUP_BATCH_ORDER_NUMBER = os.getenv("GROUP_BATCH_ORDER_NUMBER", "batch1_1")
TEAM_NAME = os.getenv("TEAM_NAME", "Vita Team")
STUDENTS = [
    {"name": os.getenv("STUDENT_1_NAME", "Student A"), "email": os.getenv("STUDENT_1_EMAIL", "a@example.com")},
    {"name": os.getenv("STUDENT_2_NAME", "Student B"), "email": os.getenv("STUDENT_2_EMAIL", "b@example.com")},
    {"name": os.getenv("STUDENT_3_NAME", "Student C"), "email": os.getenv("STUDENT_3_EMAIL", "c@example.com")},
    {"name": os.getenv("STUDENT_4_NAME", "Student D"), "email": os.getenv("STUDENT_4_EMAIL", "d@example.com")},
]

# LLMod.ai (OpenAI-compatible) — strip so no trailing space/newline in .env breaks the key
def _env(key, default=""):
    return (os.getenv(key) or default).strip()

# LLMod.ai (OpenAI-compatible)
LLMOD_API_KEY = _env("LLMOD_API_KEY")
LLMOD_BASE_URL = _env("LLMOD_BASE_URL") or "https://api.openai.com/v1"  # override with LLMod.ai URL
LLMOD_MODEL = _env("LLMOD_MODEL") or "gpt-4o-mini"
LLMOD_EMBEDDING_MODEL = _env("LLMOD_EMBEDDING_MODEL") or "text-embedding-3-small"

# Pinecone
PINECONE_API_KEY = _env("PINECONE_API_KEY")
PINECONE_INDEX_NAME = _env("PINECONE_INDEX_NAME") or "vita-rag"
PINECONE_ENV = _env("PINECONE_ENV") or "us-east-1"

# Supabase
SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_SERVICE_KEY = _env("SUPABASE_SERVICE_KEY")

# Assets
ARCHITECTURE_PNG_PATH = BASE_DIR / "assets" / "architecture.png"
