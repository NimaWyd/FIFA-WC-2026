"""Pydantic schemas for all API request and response types."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# /predict
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    home_team: str = Field(..., description="Home team name or alias (e.g. 'USA', 'France')")
    away_team: str = Field(..., description="Away team name or alias")
    match_date: str = Field(..., description="Fixture date in YYYY-MM-DD format")
    competition: Optional[str] = Field(None, description="Competition name; defaults to WC Qualification")
    neutral: Optional[bool] = Field(None, description="True if played on neutral ground")
    # Optional overrides — auto-filled from canonical registry when omitted
    home_confederation: Optional[str] = Field(None, description="Override home team confederation")
    away_confederation: Optional[str] = Field(None, description="Override away team confederation")
    home_fifa_rank: Optional[int] = Field(None, ge=1, description="Override home team FIFA rank")
    away_fifa_rank: Optional[int] = Field(None, ge=1, description="Override away team FIFA rank")
    tournament_stage: Optional[str] = Field(None, description="Match stage (e.g. 'Group Stage', 'Final')")


class Probabilities(BaseModel):
    home_win: float
    draw: float
    away_win: float


class ConfidenceInterval(BaseModel):
    home_win: tuple[float, float]
    draw: tuple[float, float]
    away_win: tuple[float, float]


class Scoreline(BaseModel):
    scoreline: str
    probability: float


class Explanation(BaseModel):
    elo_diff: float = Field(..., description="Elo rating difference (home minus away)")
    home_elo: float
    away_elo: float
    form_diff: float = Field(..., description="Recent form difference (home minus away, points per game)")
    home_form: float
    away_form: float
    rank_diff: int = Field(..., description="FIFA rank difference (home minus away; lower = better-ranked)")
    home_rank: int
    away_rank: int
    elo_win_prob: float = Field(..., description="Raw Elo-derived home win probability")
    competition_weight: float
    is_same_confederation: bool
    data_note: str


class VenueInfo(BaseModel):
    name: str
    city: str
    country: str
    capacity: int
    altitude_m: int
    surface: str
    is_dome: bool
    image_url: Optional[str] = None
    wikipedia_url: Optional[str] = None


class PredictResponse(BaseModel):
    home_team: str
    away_team: str
    match_date: str
    probabilities: Probabilities
    top_scorelines: list[Scoreline]
    expected_goals: dict[str, float]
    explanation: Explanation
    metadata: dict[str, Any]
    confidence: Optional[ConfidenceInterval] = None
    venue: Optional[VenueInfo] = None


# ---------------------------------------------------------------------------
# /teams
# ---------------------------------------------------------------------------

class TeamInfo(BaseModel):
    canonical_name: str
    display_name: str
    confederation: str
    fifa_rank: Optional[int]
    aliases: list[str]
    is_known: bool
    default_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata the backend uses by default for this team (no user input needed)",
    )


# ---------------------------------------------------------------------------
# /model-info
# ---------------------------------------------------------------------------

class AccuracyMetrics(BaseModel):
    accuracy: float
    brier_score: float
    log_loss: float
    test_rows: int


class ModelInfo(BaseModel):
    model_version: str
    model_type: str
    training_cutoff: str
    feature_set_version: str
    enabled_features: list[str]
    scoreline_model_status: str
    config_summary: dict[str, Any]
    accuracy_metrics: AccuracyMetrics | None = None


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    model_available: bool
    data_available: bool
    version: str
    timestamp: str


# ---------------------------------------------------------------------------
# /simulate
# ---------------------------------------------------------------------------

class TeamSimResult(BaseModel):
    team: str
    group: str
    group_exit: float
    round_of_32: float
    round_of_16: float
    quarter_final: float
    semi_final: float
    third_place: float
    final: float
    champion: float


class SimulationResponse(BaseModel):
    n_simulations: int
    teams: list[TeamSimResult]
    generated_at: str


# ---------------------------------------------------------------------------
# /bracket
# ---------------------------------------------------------------------------

class BracketMatch(BaseModel):
    match_id: str
    round: str
    team1: str
    team2: str
    team1_win_prob: float
    team2_win_prob: float
    predicted_winner: str


class BracketRound(BaseModel):
    round: str
    matches: list[BracketMatch]


class BracketResponse(BaseModel):
    rounds: list[BracketRound]
    group_standings: dict[str, list[str]]
    champion: str
    generated_at: str


# ---------------------------------------------------------------------------
# /matches
# ---------------------------------------------------------------------------

class LiveMatch(BaseModel):
    id: str
    utc_date: str
    local_date: str
    status: str
    minute: Optional[int] = None
    stage: str
    group: Optional[str] = None
    matchday: Optional[int] = None
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    halftime_home: Optional[int] = None
    halftime_away: Optional[int] = None
    venue: Optional[str] = None


class LiveMatchesResponse(BaseModel):
    matches: list[LiveMatch]
    source: str
    fetched_at: str
    has_live: bool
