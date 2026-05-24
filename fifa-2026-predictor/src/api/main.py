"""FastAPI application entry point for the FIFA WC 2026 Predictor API."""

from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from dotenv import load_dotenv

from src.api.routes import limiter, router

log = logging.getLogger(__name__)

load_dotenv()
ENV = os.getenv("ENV", "development").lower()


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


def _validate_required_artifacts() -> None:
    """Fail startup immediately when required model/data artifacts are missing."""
    from src.utils import PROJECT_ROOT
    from src.api.services import _get_history, _get_model

    if ENV == "production":
        ensemble_path = PROJECT_ROOT / "src/models/artifacts/ensemble.joblib"
        history_path = PROJECT_ROOT / "data/processed/matches_clean.csv"
        if not ensemble_path.exists():
            raise RuntimeError("No ensemble model artifact found - aborting startup.")
        if not history_path.exists():
            raise RuntimeError("No processed match history CSV found - aborting startup.")

    if _get_model() is None:
        raise RuntimeError("No trained model artifact found - aborting startup.")
    if _get_history() is None:
        raise RuntimeError("No match history CSV found - aborting startup.")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _validate_required_artifacts()
    _start_warmup_thread()
    yield


app = FastAPI(
    title="FIFA WC 2026 Predictor API",
    description=(
        "Match outcome prediction backend built on chronologically-validated "
        "Elo + form features and an XGBoost/LogReg classifier."
    ),
    version="1.0.0",
    docs_url="/docs" if ENV != "production" else None,
    redoc_url="/redoc" if ENV != "production" else None,
    lifespan=_lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGIN", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"message": "FIFA WC 2026 Predictor API", "docs": "/docs"}
