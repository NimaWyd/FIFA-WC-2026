"""API route definitions.

Routes stay thin: validate input shape, call service functions, return
typed response objects.  No feature engineering or model logic here.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.concurrency import run_in_threadpool

log = logging.getLogger(__name__)

from src.api import schemas, services

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=schemas.HealthResponse, tags=["meta"])
def health() -> schemas.HealthResponse:
    """Confirm the service is up and report resource availability."""
    return schemas.HealthResponse(**services.get_health())


# ---------------------------------------------------------------------------
# /model-info
# ---------------------------------------------------------------------------

@router.get("/model-info", response_model=schemas.ModelInfo, tags=["meta"])
def model_info() -> schemas.ModelInfo:
    """Return backend/model metadata for frontend transparency."""
    return schemas.ModelInfo(**services.get_model_info())


# ---------------------------------------------------------------------------
# /teams
# ---------------------------------------------------------------------------

@router.get("/teams", response_model=list[schemas.TeamInfo], tags=["teams"])
def list_teams(
    confederation: Optional[str] = Query(
        None, description="Filter by confederation (UEFA, AFC, CAF, CONCACAF, CONMEBOL, OFC)"
    )
) -> list[schemas.TeamInfo]:
    """Return all canonical teams, optionally filtered by confederation."""
    teams = services.list_all_teams(confederation_filter=confederation)
    return [schemas.TeamInfo(**t) for t in teams]


@router.get("/teams/{team_name}", response_model=schemas.TeamInfo, tags=["teams"])
def get_team(team_name: str) -> schemas.TeamInfo:
    """Return canonical metadata for a single team (accepts any known alias)."""
    info = services.get_team_info(team_name)
    if not info["is_known"]:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")
    return schemas.TeamInfo(**info)


# ---------------------------------------------------------------------------
# /predict
# ---------------------------------------------------------------------------

@router.post("/predict", response_model=schemas.PredictResponse, tags=["prediction"])
@limiter.limit("30/minute")
def predict(
    request: Request,
    body: schemas.PredictRequest,
) -> schemas.PredictResponse:
    """Predict match outcome probabilities with optional scoreline distribution.

    Confederation, FIFA rank, competition, and stage are auto-filled from the
    canonical team registry when not provided — the caller only needs to supply
    ``home_team``, ``away_team``, and ``match_date`` for a basic prediction.
    """
    try:
        result = services.predict(
            home_team=body.home_team,
            away_team=body.away_team,
            match_date=body.match_date,
            competition=body.competition,
            neutral=body.neutral,
            home_confederation=body.home_confederation,
            away_confederation=body.away_confederation,
            home_fifa_rank=body.home_fifa_rank,
            away_fifa_rank=body.away_fifa_rank,
            tournament_stage=body.tournament_stage,
        )
    except RuntimeError as exc:
        log.error(
            "Prediction service unavailable — home=%s away=%s date=%s: %s",
            body.home_team, body.away_team, body.match_date, exc,
        )
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        log.error(
            "Prediction failed unexpectedly — home=%s away=%s date=%s: %s",
            body.home_team, body.away_team, body.match_date, exc,
        )
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    return schemas.PredictResponse(
        home_team=result["home_team"],
        away_team=result["away_team"],
        match_date=result["match_date"],
        probabilities=schemas.Probabilities(**result["probabilities"]),
        top_scorelines=[schemas.Scoreline(**s) for s in result["top_scorelines"]],
        expected_goals=result["expected_goals"],
        explanation=schemas.Explanation(**result["explanation"]),
        metadata=result["metadata"],
        confidence=schemas.ConfidenceInterval(**result["confidence"]) if result.get("confidence") else None,
    )


# ---------------------------------------------------------------------------
# /simulate
# ---------------------------------------------------------------------------

@router.get("/simulate", response_model=schemas.SimulationResponse, tags=["simulation"])
@limiter.limit("5/minute")
async def simulate_tournament(request: Request) -> schemas.SimulationResponse:
    """Run 1000 Monte Carlo WC2026 simulations (cached after first call).

    Returns per-team probabilities for each stage: group exit, R32, QF, SF,
    Final, and Champion.
    """
    try:
        result = await run_in_threadpool(services.simulate, n=1000)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        log.error("Simulation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}")

    return schemas.SimulationResponse(
        n_simulations=result["n_simulations"],
        teams=[schemas.TeamSimResult(**t) for t in result["teams"]],
        generated_at=result["generated_at"],
    )


# ---------------------------------------------------------------------------
# /bracket
# ---------------------------------------------------------------------------

@router.get("/bracket", response_model=schemas.BracketResponse, tags=["simulation"])
def predict_bracket() -> schemas.BracketResponse:
    """Deterministically predict the full WC2026 knockout bracket (cached after first call).

    Returns per-match win probabilities for every round from R32 to Final,
    plus expected group standings used to seed the bracket.
    """
    try:
        result = services.predict_bracket()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        log.error("Bracket prediction failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Bracket prediction failed: {exc}")

    return schemas.BracketResponse(
        rounds=[
            schemas.BracketRound(
                round=r["round"],
                matches=[schemas.BracketMatch(**m) for m in r["matches"]],
            )
            for r in result["rounds"]
        ],
        group_standings=result["group_standings"],
        champion=result["champion"],
        generated_at=result["generated_at"],
    )


# ---------------------------------------------------------------------------
# /matches
# ---------------------------------------------------------------------------

@router.get("/matches", response_model=schemas.LiveMatchesResponse, tags=["live"])
def live_matches() -> schemas.LiveMatchesResponse:
    """Return WC2026 match schedule with live status and scores from football-data.org.

    Falls back gracefully when FOOTBALL_DATA_API_KEY is not set.
    Results are cached for 60 s when matches are in play, 5 min otherwise.
    """
    result = services.get_live_matches()
    return schemas.LiveMatchesResponse(
        matches=[schemas.LiveMatch(**m) for m in result["matches"]],
        source=result["source"],
        fetched_at=result["fetched_at"],
        has_live=result["has_live"],
    )


# ---------------------------------------------------------------------------
# /refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", tags=["meta"])
def refresh_live_data(x_refresh_token: str | None = Header(None)) -> dict:
    """Fetch the latest match results from football-data.org and clear caches.

    Requires FOOTBALL_DATA_API_KEY in the server environment.
    The next prediction after this call replays updated Elo/form history.
    """
    refresh_secret = os.getenv("REFRESH_SECRET")
    is_production = os.getenv("ENV", "development").lower() == "production"
    if is_production and not refresh_secret:
        raise HTTPException(status_code=503, detail="REFRESH_SECRET is not configured")
    if refresh_secret and x_refresh_token != refresh_secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    from src.data.update_live_matches import fetch_and_append_new_results, DEFAULT_OUTPUT
    try:
        n = fetch_and_append_new_results(DEFAULT_OUTPUT)
        services.invalidate_data_caches()
        return {"status": "ok", "new_matches_added": n}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
