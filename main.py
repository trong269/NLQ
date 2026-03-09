"""
main.py
───────
FastAPI application entry point.

Run locally:
    uvicorn main:app --reload
    # or
    bash start.sh

Endpoints
---------
GET /health  – liveness / readiness probe
GET /docs    – Swagger UI (auto-generated)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from src.routers import register_routers
from src.utils import load_config

# Load environment variables from .env (no-op if file doesn't exist)
load_dotenv()

_config = load_config()
_app_cfg = _config.get("app", {})

logging.basicConfig(
    level=getattr(logging, _app_cfg.get("log_level", "INFO"), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle hooks."""
    logger.info("Starting %s v%s", app.title, app.version)
    yield
    logger.info("Shutting down %s", app.title)


app = FastAPI(
    title=_app_cfg.get("name", "NLQ Multi-Agent"),
    version=_app_cfg.get("version", "0.1.0"),
    lifespan=lifespan,
)

register_routers(app)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    """Liveness probe – returns 200 when the server is running."""
    return {"status": "ok", "version": app.version}
