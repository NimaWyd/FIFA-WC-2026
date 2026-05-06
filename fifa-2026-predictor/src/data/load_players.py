"""
Loaders for player-related data sources.

Each loader follows the same pattern as the existing match/team loaders:
  - Accepts an optional file path
  - Returns an empty DataFrame with the correct columns if the file is absent
  - Validates the schema via player_schema helpers

No source is required to exist. All loaders degrade gracefully so the
pipeline continues to work even when player data is unavailable.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from src.data.player_schema import (
    EXPECTED_LINEUP_COLUMNS,
    INJURY_COLUMNS,
    PLAYER_COLUMNS,
    PLAYER_MATCH_STAT_COLUMNS,
    PLAYER_RATING_COLUMNS,
    ensure_injury_schema,
    ensure_lineup_schema,
    ensure_player_schema,
    ensure_rating_schema,
)

log = logging.getLogger(__name__)


def _read_csv_safe(path: Optional[str], label: str) -> Optional[pd.DataFrame]:
    """Return a DataFrame or None if path is absent or unreadable."""
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        log.debug("Player data file not found (%s): %s", label, path)
        return None
    try:
        return pd.read_csv(p)
    except Exception as exc:
        log.warning("Could not read %s from %s: %s", label, path, exc)
        return None


def load_players(csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load canonical player records.

    Returns an empty DataFrame with correct columns when the file is absent.
    """
    raw = _read_csv_safe(csv_path, "players")
    if raw is None:
        return pd.DataFrame(columns=PLAYER_COLUMNS)
    try:
        return ensure_player_schema(raw)
    except ValueError as exc:
        log.warning("Player schema validation failed: %s – returning empty frame", exc)
        return pd.DataFrame(columns=PLAYER_COLUMNS)


def load_injuries(csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load injury / absence / suspension records.

    Returns an empty DataFrame when data is unavailable.
    """
    raw = _read_csv_safe(csv_path, "injuries")
    if raw is None:
        return pd.DataFrame(columns=INJURY_COLUMNS)
    try:
        return ensure_injury_schema(raw)
    except ValueError as exc:
        log.warning("Injury schema validation failed: %s – returning empty frame", exc)
        return pd.DataFrame(columns=INJURY_COLUMNS)


def load_player_ratings(csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load player rating history.

    Returns an empty DataFrame when data is unavailable.
    """
    raw = _read_csv_safe(csv_path, "player_ratings")
    if raw is None:
        return pd.DataFrame(columns=PLAYER_RATING_COLUMNS)
    try:
        return ensure_rating_schema(raw)
    except ValueError as exc:
        log.warning("Rating schema validation failed: %s – returning empty frame", exc)
        return pd.DataFrame(columns=PLAYER_RATING_COLUMNS)


def load_expected_lineups(csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load expected pre-match lineup data.

    Returns an empty DataFrame when data is unavailable.
    """
    raw = _read_csv_safe(csv_path, "expected_lineups")
    if raw is None:
        return pd.DataFrame(columns=EXPECTED_LINEUP_COLUMNS)
    try:
        return ensure_lineup_schema(raw)
    except ValueError as exc:
        log.warning("Lineup schema validation failed: %s – returning empty frame", exc)
        return pd.DataFrame(columns=EXPECTED_LINEUP_COLUMNS)


def load_player_match_stats(csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load per-player per-match statistics.

    Returns an empty DataFrame when data is unavailable.
    """
    raw = _read_csv_safe(csv_path, "player_match_stats")
    if raw is None:
        return pd.DataFrame(columns=PLAYER_MATCH_STAT_COLUMNS)
    missing = [c for c in ["match_id", "team", "player_id", "date"] if c not in raw.columns]
    if missing:
        log.warning("Player match stats missing columns %s – returning empty frame", missing)
        return pd.DataFrame(columns=PLAYER_MATCH_STAT_COLUMNS)
    stat_cols = ["minutes_played", "goals", "assists", "yellow_cards", "red_cards"]
    missing_stats = [c for c in stat_cols if c not in raw.columns]
    if missing_stats:
        log.warning(
            "Player match stats missing stat columns %s — these will be NaN", missing_stats
        )
    for col in PLAYER_MATCH_STAT_COLUMNS:
        if col not in raw.columns:
            raw[col] = None
    return raw[PLAYER_MATCH_STAT_COLUMNS]
