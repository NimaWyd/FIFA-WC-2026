"""FastAPI application entry point for the FIFA WC 2026 Predictor API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

app = FastAPI(
    title="FIFA WC 2026 Predictor API",
    description=(
        "Match outcome prediction backend built on chronologically-validated "
        "Elo + form features and an XGBoost/LogReg classifier."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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
