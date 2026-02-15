"""Application configuration from environment variables."""
import os
from pathlib import Path

# Project
BASE_DIR = Path(__file__).resolve().parent.parent

# API / Team (fill in for submission)
GROUP_BATCH_ORDER_NUMBER = os.getenv("GROUP_BATCH_ORDER_NUMBER", "batch1_1")
TEAM_NAME = os.getenv("TEAM_NAME", "Vita Team")
STUDENTS = [
    {"name": os.getenv("STUDENT_1_NAME", "Student A"), "email": os.getenv("STUDENT_1_EMAIL", "a@example.com")},
    {"name": os.getenv("STUDENT_2_NAME", "Student B"), "email": os.getenv("STUDENT_2_EMAIL", "b@example.com")},
    {"name": os.getenv("STUDENT_3_NAME", "Student C"), "email": os.getenv("STUDENT_3_EMAIL", "c@example.com")},
]

# LLMod.ai (OpenAI-compatible)
LLMOD_API_KEY = os.getenv("LLMOD_API_KEY", "")
LLMOD_BASE_URL = os.getenv("LLMOD_BASE_URL", "https://api.openai.com/v1")  # override with LLMod.ai URL
LLMOD_MODEL = os.getenv("LLMOD_MODEL", "gpt-4o-mini")
LLMOD_EMBEDDING_MODEL = os.getenv("LLMOD_EMBEDDING_MODEL", "text-embedding-3-small")

# Pinecone
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "vita-rag")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Assets
ARCHITECTURE_PNG_PATH = BASE_DIR / "assets" / "architecture.png"
