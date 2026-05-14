"""API route definitions.

Routes stay thin: validate input shape, call service functions, return
typed response objects.  No feature engineering or model logic here.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

log = logging.getLogger(__name__)

from src.api import schemas, services

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
    return schemas.TeamInfo(**info)


# ---------------------------------------------------------------------------
# /predict
# ---------------------------------------------------------------------------

@router.post("/predict", response_model=schemas.PredictResponse, tags=["prediction"])
def predict(request: schemas.PredictRequest) -> schemas.PredictResponse:
    """Predict match outcome probabilities with optional scoreline distribution.

    Confederation, FIFA rank, competition, and stage are auto-filled from the
    canonical team registry when not provided — the caller only needs to supply
    ``home_team``, ``away_team``, and ``match_date`` for a basic prediction.
    """
    try:
        result = services.predict(
            home_team=request.home_team,
            away_team=request.away_team,
            match_date=request.match_date,
            competition=request.competition,
            neutral=request.neutral,
            home_confederation=request.home_confederation,
            away_confederation=request.away_confederation,
            home_fifa_rank=request.home_fifa_rank,
            away_fifa_rank=request.away_fifa_rank,
            tournament_stage=request.tournament_stage,
        )
    except RuntimeError as exc:
        log.error(
            "Prediction service unavailable — home=%s away=%s date=%s: %s",
            request.home_team, request.away_team, request.match_date, exc,
        )
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        log.error(
            "Prediction failed unexpectedly — home=%s away=%s date=%s: %s",
            request.home_team, request.away_team, request.match_date, exc,
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
def simulate_tournament() -> schemas.SimulationResponse:
    """Run 1000 Monte Carlo WC2026 simulations (cached after first call).

    Returns per-team probabilities for each stage: group exit, R32, QF, SF,
    Final, and Champion.
    """
    try:
        result = services.simulate(n=1000)
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
# /refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", tags=["meta"])
def refresh_live_data() -> dict:
    """Fetch the latest match results from football-data.org and clear caches.

    Requires FOOTBALL_DATA_API_KEY in the server environment.
    The next prediction after this call replays updated Elo/form history.
    """
    from src.data.update_live_matches import fetch_and_append_new_results, DEFAULT_OUTPUT
    try:
        n = fetch_and_append_new_results(DEFAULT_OUTPUT)
        services.invalidate_data_caches()
        return {"status": "ok", "new_matches_added": n}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
