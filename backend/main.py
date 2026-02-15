"""Vita: AI-Powered Wellness & Nutrition Coach — FastAPI application."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router

app = FastAPI(title="Vita", description="AI-Powered Wellness & Nutrition Coach")
app.include_router(router)

# Serve frontend static files
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
