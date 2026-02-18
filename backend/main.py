"""Vita: AI-Powered Wellness & Nutrition Coach — FastAPI application."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router

app = FastAPI(title="Vita", description="AI-Powered Wellness & Nutrition Coach")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Serve frontend static files (prefer Next.js static export, fallback to legacy)
_root = Path(__file__).resolve().parent.parent
frontend_next_dir = _root / "frontend-next" / "out"
frontend_legacy_dir = _root / "frontend"

if frontend_next_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_next_dir), html=True), name="frontend")
elif frontend_legacy_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_legacy_dir), html=True), name="frontend")
