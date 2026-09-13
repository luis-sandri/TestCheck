"""Ponto de entrada serverless da API FastAPI na Vercel."""

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
