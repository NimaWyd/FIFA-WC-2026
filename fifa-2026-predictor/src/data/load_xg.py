"""Expected goals (xG) data interface with raw-goal fallback (Issue 7).

Real xG data provides a cleaner team-strength signal than raw goals because
it adjusts for shot quality.  However, consistent xG coverage for national
teams across historical data is extremely limited.

This module provides:
- ``XGDataLoader``: loads real xG data when available
- ``get_xg_features()``: returns per-match xG values, falling back to raw goals

All callers should use ``get_xg_features()`` and check ``source`` in the
result to know whether real xG or a raw-goal proxy was used.

Fallback behaviour
------------------
When no real xG data is available, the proxy is simply the rolling
recency-weighted goals scored/conceded (attack_rw5 / defense_rw5) already
computed by the tracker.  These are named ``*_xg_proxy`` to be explicit
that they are NOT real xG values.

Data format expected (CSV or DataFrame):
    date        : YYYY-MM-DD
    home_team   : canonical or alias
    away_team   : canonical or alias
    home_xg     : float (expected goals for home team)
    away_xg     : float (expected goals for away team)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from src.data.team_identity import resolve_team


class XGDataLoader:
    """Loads and provides per-match xG values with raw-goal fallback.

    When ``has_data == False`` every call to ``get_match_xg()`` returns
    ``(None, None)`` and callers should use the raw-goal proxy instead.
    """

    def __init__(self) -> None:
        self._df: Optional[pd.DataFrame] = None
        self._index: Optional[dict] = None  # (date, home, away) → (home_xg, away_xg)

    @property
    def has_data(self) -> bool:
        return self._df is not None and len(self._df) > 0

    @classmethod
    def from_csv(cls, path: str | Path) -> "XGDataLoader":
        """Load xG data from a CSV file."""
        loader = cls()
        p = Path(path)
        if not p.exists():
            return loader

        df = pd.read_csv(p)
        required = {"date", "home_team", "away_team", "home_xg", "away_xg"}
        if not required.issubset(df.columns):
            raise ValueError(
                f"xG CSV must have columns {required}; got {list(df.columns)}"
            )
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["home_team"] = df["home_team"].map(resolve_team)
        df["away_team"] = df["away_team"].map(resolve_team)
        df = df.dropna(subset=["date", "home_xg", "away_xg"])

        loader._df = df
        loader._index = {
            (str(r.date.date()), r.home_team, r.away_team): (float(r.home_xg), float(r.away_xg))
            for r in df.itertuples(index=False)
        }
        return loader

    def get_match_xg(
        self,
        home_team: str,
        away_team: str,
        match_date: pd.Timestamp,
    ) -> tuple[Optional[float], Optional[float]]:
        """Return (home_xg, away_xg) for the match, or (None, None) if not found."""
        if self._index is None:
            return None, None
        key = (str(match_date.date()), resolve_team(home_team), resolve_team(away_team))
        result = self._index.get(key)
        if result is None:
            return None, None
        return result


def get_xg_features(
    loader: Optional[XGDataLoader],
    home_team: str,
    away_team: str,
    match_date: pd.Timestamp,
    home_attack_rw5: float,
    away_attack_rw5: float,
) -> dict:
    """Return xG-style features for a match, with transparent fallback.

    When real xG data is available the values are labelled ``source='real_xg'``.
    When falling back to recency-weighted raw goals they are labelled
    ``source='raw_goal_proxy'`` so callers and reports can distinguish them.

    Returns
    -------
    dict with keys:
        home_xg_proxy   : float
        away_xg_proxy   : float
        xg_diff_proxy   : float
        xg_source       : 'real_xg' | 'raw_goal_proxy'
    """
    if loader is not None and loader.has_data:
        hxg, axg = loader.get_match_xg(home_team, away_team, match_date)
        if hxg is not None and axg is not None:
            return {
                "home_xg_proxy": hxg,
                "away_xg_proxy": axg,
                "xg_diff_proxy": hxg - axg,
                "xg_source": "real_xg",
            }

    # Fall back to recency-weighted rolling attack rating (raw goals)
    return {
        "home_xg_proxy": home_attack_rw5,
        "away_xg_proxy": away_attack_rw5,
        "xg_diff_proxy": home_attack_rw5 - away_attack_rw5,
        "xg_source": "raw_goal_proxy",
    }
