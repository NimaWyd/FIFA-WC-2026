"""
Schemas, constants, and validation helpers for all player-related data sources.

Player data is kept completely separate from the match pipeline.
The aggregation step (player_aggregator.py) is the only place where
player rows are converted into team-level match features.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Column-name constants (one list per logical table)
# ---------------------------------------------------------------------------

PLAYER_COLUMNS = [
    "player_id",      # str  – stable unique identifier
    "name",           # str  – display name
    "nationality",    # str  – canonical team name (matches team_identity)
    "position",       # str  – GK | DEF | MID | FWD
    "birth_date",     # str  – ISO YYYY-MM-DD (optional)
]

ROSTER_COLUMNS = [
    "team",           # str  – canonical team name
    "player_id",      # str  – FK → players.player_id
    "season",         # str  – e.g. "2025-2026"
    "squad_number",   # int  – shirt number (optional)
    "joined_date",    # str  – ISO YYYY-MM-DD (optional)
    "left_date",      # str  – ISO YYYY-MM-DD or NaN if still active
]

PLAYER_MATCH_STAT_COLUMNS = [
    "match_id",       # str  – FK → matches
    "team",           # str  – canonical team name
    "player_id",      # str  – FK → players
    "date",           # str  – ISO YYYY-MM-DD
    "minutes_played", # int
    "goals",          # int
    "assists",        # int
    "yellow_cards",   # int
    "red_cards",      # int
    "rating",         # float – match rating 1-10 (optional, may be NaN)
]

EXPECTED_LINEUP_COLUMNS = [
    "match_id",            # str
    "team",                # str
    "player_id",           # str
    "date",                # str  – ISO YYYY-MM-DD (match date)
    "formation_position",  # str  – e.g. "CB", "CAM", "ST" (optional)
    "is_starter",          # bool – True = expected starter
]

INJURY_COLUMNS = [
    "player_id",    # str
    "team",         # str
    "from_date",    # str  – ISO YYYY-MM-DD
    "to_date",      # str  – ISO YYYY-MM-DD or NaN (ongoing)
    "injury_type",  # str  – e.g. "muscle", "suspension" (optional)
    "severity",     # str  – "minor" | "moderate" | "major" (optional)
]

PLAYER_RATING_COLUMNS = [
    "player_id",      # str
    "rating_date",    # str   – ISO YYYY-MM-DD (date rating was valid from)
    "overall_rating", # float – 0-100
    "attack_rating",  # float – 0-100 (optional)
    "defense_rating", # float – 0-100 (optional)
    "source",         # str   – e.g. "FIFA", "SofaScore" (optional)
]

# Valid position codes across all tables
VALID_POSITIONS = {"GK", "DEF", "MID", "FWD"}

# Safe defaults returned by the aggregator when data is absent
DEFAULTS: dict = {
    "overall_rating": 70.0,
    "attack_rating": 70.0,
    "defense_rating": 70.0,
    "gk_rating": 70.0,
    "squad_rating": 70.0,
    "missing_top3_count": 0,
    "squad_continuity": 1.0,
}

# ---------------------------------------------------------------------------
# Dataclasses – typed representations of individual records
# ---------------------------------------------------------------------------

@dataclass
class PlayerRecord:
    player_id: str
    name: str
    nationality: str
    position: str            # GK | DEF | MID | FWD
    birth_date: Optional[str] = None

    def __post_init__(self) -> None:
        if self.position not in VALID_POSITIONS:
            raise ValueError(
                f"Invalid position '{self.position}'. Must be one of {VALID_POSITIONS}"
            )


@dataclass
class RosterEntry:
    team: str
    player_id: str
    season: str
    squad_number: Optional[int] = None
    joined_date: Optional[str] = None
    left_date: Optional[str] = None


@dataclass
class PlayerMatchStat:
    match_id: str
    team: str
    player_id: str
    date: str
    minutes_played: int = 0
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    rating: Optional[float] = None


@dataclass
class ExpectedLineupEntry:
    match_id: str
    team: str
    player_id: str
    date: str
    formation_position: Optional[str] = None
    is_starter: bool = True


@dataclass
class InjuryRecord:
    player_id: str
    team: str
    from_date: str
    to_date: Optional[str] = None
    injury_type: Optional[str] = None
    severity: Optional[str] = None


@dataclass
class PlayerRating:
    player_id: str
    rating_date: str
    overall_rating: float
    attack_rating: Optional[float] = None
    defense_rating: Optional[float] = None
    source: Optional[str] = None

# ---------------------------------------------------------------------------
# DataFrame schema validators
# ---------------------------------------------------------------------------

def ensure_player_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise a players DataFrame."""
    df = df.copy()
    for col in ["player_id", "name", "nationality", "position"]:
        if col not in df.columns:
            raise ValueError(f"Players table missing required column: '{col}'")
    if "birth_date" not in df.columns:
        df["birth_date"] = None
    df["position"] = df["position"].str.upper().str.strip()
    return df


def ensure_roster_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise a rosters DataFrame."""
    df = df.copy()
    for col in ["team", "player_id", "season"]:
        if col not in df.columns:
            raise ValueError(f"Rosters table missing required column: '{col}'")
    for col in ["squad_number", "joined_date", "left_date"]:
        if col not in df.columns:
            df[col] = None
    return df


def ensure_injury_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise an injuries DataFrame."""
    df = df.copy()
    for col in ["player_id", "team", "from_date"]:
        if col not in df.columns:
            raise ValueError(f"Injuries table missing required column: '{col}'")
    if "to_date" not in df.columns:
        df["to_date"] = None
    for col in ["injury_type", "severity"]:
        if col not in df.columns:
            df[col] = None
    return df


def ensure_rating_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise a player_ratings DataFrame."""
    df = df.copy()
    for col in ["player_id", "rating_date", "overall_rating"]:
        if col not in df.columns:
            raise ValueError(f"Ratings table missing required column: '{col}'")
    for col in ["attack_rating", "defense_rating", "source"]:
        if col not in df.columns:
            df[col] = None
    return df


def ensure_lineup_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalise an expected_lineups DataFrame."""
    df = df.copy()
    for col in ["match_id", "team", "player_id", "date"]:
        if col not in df.columns:
            raise ValueError(f"Lineups table missing required column: '{col}'")
    if "is_starter" not in df.columns:
        df["is_starter"] = True
    if "formation_position" not in df.columns:
        df["formation_position"] = None
    return df
