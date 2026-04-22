"""Explicit schema definitions and normalization helpers for match and team data.

Team name normalization is delegated to team_identity.py — this module exposes
the same public API as before so all callers continue to work unchanged.
"""

from __future__ import annotations

import pandas as pd

from src.data.team_identity import resolve_team

# ---------------------------------------------------------------------------
# Team name aliases — kept as a backward-compatible shim.
# The canonical alias table lives in team_identity.ALIAS_TO_CANONICAL.
# ---------------------------------------------------------------------------
from src.data.team_identity import ALIAS_TO_CANONICAL as TEAM_NAME_ALIASES  # noqa: F401

# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------
REQUIRED_MATCH_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
]

OPTIONAL_MATCH_DEFAULTS: dict[str, object] = {
    "competition": "Unknown",
    "neutral": False,
    "home_confederation": "UNKNOWN",
    "away_confederation": "UNKNOWN",
    "home_fifa_rank": 75,
    "away_fifa_rank": 75,
    "tournament_stage": "Unknown",
    "source": "unknown",
}

MATCH_NUMERIC_COLUMNS = ["home_score", "away_score", "home_fifa_rank", "away_fifa_rank"]

REQUIRED_TEAM_COLUMNS = ["team"]

OPTIONAL_TEAM_DEFAULTS: dict[str, object] = {
    "confederation": "UNKNOWN",
    "fifa_rank": 75,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_team_name(name: str) -> str:
    """Return the canonical team name, applying all registered aliases."""
    return resolve_team(name)


def fill_missing_defaults(df: pd.DataFrame, defaults: dict[str, object]) -> pd.DataFrame:
    """Add absent columns and fill NaN values using provided defaults."""
    df = df.copy()
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
        else:
            df[col] = df[col].fillna(default)
    return df


def _coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def ensure_match_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Validate, fill, and normalise a matches DataFrame.

    Raises ValueError if any required column is absent.
    """
    df = df.copy()
    missing = [c for c in REQUIRED_MATCH_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Matches DataFrame missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = _coerce_numeric(df, MATCH_NUMERIC_COLUMNS)
    df = fill_missing_defaults(df, OPTIONAL_MATCH_DEFAULTS)

    # Normalise neutral to bool regardless of source type
    neutral = df["neutral"]
    if neutral.dtype == object:
        df["neutral"] = neutral.astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        df["neutral"] = neutral.astype(bool)

    # Normalise team names through canonical identity registry
    df["home_team"] = df["home_team"].map(normalize_team_name)
    df["away_team"] = df["away_team"].map(normalize_team_name)

    return df


def ensure_team_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Validate, fill, and normalise a teams DataFrame.

    Raises ValueError if the required 'team' column is absent.
    """
    df = df.copy()
    missing = [c for c in REQUIRED_TEAM_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Teams DataFrame missing required columns: {missing}")

    df["team"] = df["team"].map(normalize_team_name)
    df = fill_missing_defaults(df, OPTIONAL_TEAM_DEFAULTS)
    df["fifa_rank"] = pd.to_numeric(df["fifa_rank"], errors="coerce").fillna(75).astype(int)

    return df
