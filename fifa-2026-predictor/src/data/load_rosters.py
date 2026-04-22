"""
Loader for team roster data.

Rosters describe which players belong to a team during a given season/period.
Used by player_aggregator to determine available squad members when no
explicit expected lineup is provided.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from src.data.player_schema import ROSTER_COLUMNS, ensure_roster_schema

log = logging.getLogger(__name__)


def load_rosters(csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load team roster membership records.

    Returns an empty DataFrame when the file is absent so the pipeline
    degrades gracefully without player data.
    """
    if csv_path is None:
        return pd.DataFrame(columns=ROSTER_COLUMNS)
    p = Path(csv_path)
    if not p.exists():
        log.debug("Roster file not found: %s", csv_path)
        return pd.DataFrame(columns=ROSTER_COLUMNS)
    try:
        raw = pd.read_csv(p)
        return ensure_roster_schema(raw)
    except Exception as exc:
        log.warning(
            "Could not load rosters from %s: %s – returning empty frame", csv_path, exc
        )
        return pd.DataFrame(columns=ROSTER_COLUMNS)


def get_team_roster(
    rosters_df: pd.DataFrame,
    team: str,
    as_of_date: str,
) -> pd.DataFrame:
    """
    Return the roster rows for *team* that were active on *as_of_date*.

    A roster entry is active if:
      - ``joined_date`` is NaN or <= as_of_date, AND
      - ``left_date`` is NaN or > as_of_date.

    Returns an empty DataFrame (correct columns) when no rows match.
    """
    if rosters_df is None or rosters_df.empty:
        return pd.DataFrame(columns=ROSTER_COLUMNS)

    mask = rosters_df["team"].str.lower() == team.lower()
    team_rows = rosters_df[mask].copy()
    if team_rows.empty:
        return team_rows.reset_index(drop=True)

    joined = pd.to_datetime(team_rows["joined_date"], errors="coerce")
    left = pd.to_datetime(team_rows["left_date"], errors="coerce")
    ref = pd.Timestamp(as_of_date)

    active = (joined.isna() | (joined <= ref)) & (left.isna() | (left > ref))
    return team_rows[active].reset_index(drop=True)
