"""Time-safe historical FIFA ranking lookup (Issue 1).

Provides RankingLookup which returns the rank a team held *at or before* a
given match date — not a static 2025 snapshot.

Data format expected (CSV or DataFrame):
    date        : YYYY-MM-DD (the ranking publication date)
    team        : team name (aliases resolved via canonical registry)
    rank        : integer FIFA rank

If no historical ranking file is provided the module degrades to the
static ``get_fifa_rank()`` fallback used in earlier phases.  All callers
check ``lookup.has_data`` before using dynamic ranks.

Usage
-----
    lookup = RankingLookup.from_csv("data/raw/fifa_rankings.csv")
    rank = lookup.get_rank("France", pd.Timestamp("2022-11-01"))  # pre-Qatar WC rank
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from src.data.team_identity import get_fifa_rank, resolve_team


class RankingLookup:
    """Time-safe FIFA rank lookup backed by an optional historical dataset.

    When no data is loaded (``has_data == False``) every call to
    ``get_rank()`` returns the static 2025 snapshot via ``get_fifa_rank()``.
    This is the same behaviour as the pre-Phase-7 pipeline, so all existing
    code continues to work unchanged.
    """

    def __init__(self) -> None:
        self._df: Optional[pd.DataFrame] = None  # sorted by (team, date)

    @property
    def has_data(self) -> bool:
        return self._df is not None and len(self._df) > 0

    @classmethod
    def from_csv(cls, path: str | Path, default_rank: int = 75) -> "RankingLookup":
        """Load a historical rankings CSV.

        Expected columns: date, team, rank.
        Team names are resolved to canonical form on load.
        """
        lookup = cls()
        p = Path(path)
        if not p.exists():
            return lookup

        df = pd.read_csv(p)
        required = {"date", "team", "rank"}
        if not required.issubset(df.columns):
            raise ValueError(
                f"Rankings CSV must have columns {required}; got {list(df.columns)}"
            )
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["rank"] = pd.to_numeric(df["rank"], errors="coerce").fillna(default_rank).astype(int)
        df["team"] = df["team"].map(resolve_team)
        df = df.dropna(subset=["date"]).sort_values(["team", "date"]).reset_index(drop=True)
        lookup._df = df
        return lookup

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "RankingLookup":
        """Construct from an already-loaded DataFrame (same schema as from_csv)."""
        lookup = cls()
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["team"] = df["team"].map(resolve_team)
        df = df.dropna(subset=["date"]).sort_values(["team", "date"]).reset_index(drop=True)
        lookup._df = df
        return lookup

    def get_rank(
        self,
        team: str,
        match_date: pd.Timestamp,
        default: int = 75,
    ) -> int:
        """Return the team's rank as of *match_date* (most recent prior publication).

        Falls back to static 2025 snapshot when dynamic data is unavailable.
        Uses strictly < match_date to avoid any forward-looking leakage.
        """
        if not self.has_data:
            return get_fifa_rank(team, default=default)

        canonical = resolve_team(team)
        team_df = self._df[self._df["team"] == canonical]
        if team_df.empty:
            return get_fifa_rank(canonical, default=default)

        # Strictly before match date (no same-day leakage)
        prior = team_df[team_df["date"] < match_date]
        if prior.empty:
            # No ranking before this match — use earliest available rank
            return int(team_df.iloc[0]["rank"])

        return int(prior.iloc[-1]["rank"])

    def has_coverage(self, team: str) -> bool:
        """Return True if this team appears in the dynamic ranking dataset."""
        if not self.has_data:
            return False
        canonical = resolve_team(team)
        return canonical in self._df["team"].values


# Module-level singleton — loaded once if ranking data exists
_DEFAULT_PATH = "data/raw/fifa_rankings.csv"
_singleton: Optional[RankingLookup] = None


def get_ranking_lookup(path: str = _DEFAULT_PATH) -> RankingLookup:
    """Return (and cache) the global RankingLookup instance."""
    global _singleton
    if _singleton is None:
        _singleton = RankingLookup.from_csv(path)
    return _singleton
