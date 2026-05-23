"""FastAPI application entry point for the FIFA WC 2026 Predictor API."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

log = logging.getLogger(__name__)


def _warmup_caches() -> None:
    """Pre-warm simulation and bracket caches. Errors are swallowed so a missing
    model artifact at startup doesn't crash the server."""
    try:
        from src.api.services import simulate, predict_bracket
        log.info("Cache warmup: starting simulation...")
        simulate()
        log.info("Cache warmup: building bracket...")
        predict_bracket()
        log.info("Cache warmup: complete.")
    except Exception as exc:
        log.warning("Cache warmup failed (server still healthy): %s", exc)


def _start_warmup_thread() -> None:
    t = threading.Thread(target=_warmup_caches, daemon=True, name="cache-warmup")
    t.start()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _start_warmup_thread()
    yield


app = FastAPI(
    title="FIFA WC 2026 Predictor API",
    description=(
        "Match outcome prediction backend built on chronologically-validated "
        "Elo + form features and an XGBoost/LogReg classifier."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"message": "FIFA WC 2026 Predictor API", "docs": "/docs"}
