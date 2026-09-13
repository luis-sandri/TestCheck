"""Ponto de entrada serverless da API FastAPI na Vercel."""

from pathlib import Path
import sys

from fastapi import FastAPI


BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app as api_app  # noqa: E402


# O rewrite da Vercel mantém o prefixo /api da URL original.
app = FastAPI()
app.mount("/api", api_app)
