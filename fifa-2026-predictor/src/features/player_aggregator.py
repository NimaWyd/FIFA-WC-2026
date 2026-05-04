"""
Player feature aggregator.

Converts player-level data sources (rosters, ratings, injuries, lineups)
into team-level numeric features that merge into the one-row-per-match
feature pipeline.

Design guarantees
-----------------
- All features are strictly pre-match (no post-match information used).
- Missing data never causes a crash; safe defaults from player_schema.DEFAULTS
  are returned when any data source is absent or empty.
- All returned keys are un-prefixed. Callers add "home_" / "away_" when
  merging into a match row.
- The aggregator is stateless; callers supply all data slices.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

import numpy as np
import pandas as pd

from src.data.player_schema import DEFAULTS

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature names produced (no side prefix)
# ---------------------------------------------------------------------------
PLAYER_FEATURE_NAMES: List[str] = [
    "squad_overall_rating",   # Mean overall rating across available squad
    "starting_xi_rating",     # Mean rating of expected starting XI
    "gk_rating",              # GK overall rating (or default if unknown)
    "attack_player_rating",   # Mean rating of FWD players
    "defense_player_rating",  # Mean rating of DEF players
    "missing_top3_count",     # Number of top-3 rated players who are absent
    "squad_continuity",       # Fraction of squad NOT injured/absent
    "has_lineup_data",        # 1.0 if expected lineup provided, else 0.0
    "has_injury_data",        # 1.0 if injury data provided, else 0.0
    "has_rating_data",        # 1.0 if rating data provided, else 0.0
]

# Home-/away-prefixed names for the combined match row
PLAYER_MATCH_FEATURE_NAMES: List[str] = (
    [f"home_{n}" for n in PLAYER_FEATURE_NAMES]
    + [f"away_{n}" for n in PLAYER_FEATURE_NAMES]
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _latest_ratings(
    ratings_df: pd.DataFrame,
    player_ids: List[str],
    as_of_date: str,
) -> pd.Series:
    """
    Return the most-recent overall_rating per player_id before *as_of_date*.

    Returns a Series indexed by player_id; absent players are missing (NaN).
    """
    if ratings_df is None or ratings_df.empty:
        return pd.Series(dtype=float)

    ref = pd.Timestamp(as_of_date)
    valid = ratings_df.copy()
    valid["rating_date"] = pd.to_datetime(valid["rating_date"], errors="coerce")
    valid = valid[valid["rating_date"] < ref]
    if valid.empty:
        return pd.Series(dtype=float)

    filtered = valid[valid["player_id"].isin(player_ids)]
    if filtered.empty:
        return pd.Series(dtype=float)

    latest = (
        filtered.sort_values("rating_date")
        .groupby("player_id")
        .last()["overall_rating"]
    )
    return latest


def _get_injured_players(
    injuries_df: pd.DataFrame,
    team: str,
    match_date: str,
) -> Set[str]:
    """Return the set of player_ids injured/unavailable for *team* on *match_date*."""
    if injuries_df is None or injuries_df.empty:
        return set()

    ref = pd.Timestamp(match_date)
    mask = injuries_df["team"].str.lower() == team.lower()
    team_inj = injuries_df[mask].copy()
    if team_inj.empty:
        return set()

    from_dates = pd.to_datetime(team_inj["from_date"], errors="coerce")
    to_dates = pd.to_datetime(team_inj["to_date"], errors="coerce")
    active = (from_dates <= ref) & (to_dates.isna() | (to_dates >= ref))
    return set(team_inj[active]["player_id"].tolist())


# ---------------------------------------------------------------------------
# Main public functions
# ---------------------------------------------------------------------------

def aggregate_team_player_features(
    team: str,
    match_date: str,
    *,
    rosters_df: Optional[pd.DataFrame] = None,
    ratings_df: Optional[pd.DataFrame] = None,
    injuries_df: Optional[pd.DataFrame] = None,
    lineups_df: Optional[pd.DataFrame] = None,
    match_id: Optional[str] = None,
) -> Dict[str, float]:
    """
    Aggregate player data for *team* on *match_date* into team-level features.

    All keyword arguments are optional. When absent, safe defaults from
    ``player_schema.DEFAULTS`` are returned so training and inference
    continue to work without any player data loaded.

    Returns a flat dict of feature_name -> float (no side prefix).
    """
    feats: Dict[str, float] = {
        "squad_overall_rating": DEFAULTS["squad_rating"],
        "starting_xi_rating": DEFAULTS["squad_rating"],
        "gk_rating": DEFAULTS["gk_rating"],
        "attack_player_rating": DEFAULTS["attack_rating"],
        "defense_player_rating": DEFAULTS["defense_rating"],
        "missing_top3_count": float(DEFAULTS["missing_top3_count"]),
        "squad_continuity": DEFAULTS["squad_continuity"],
        "has_lineup_data": 0.0,
        "has_injury_data": 0.0,
        "has_rating_data": 0.0,
    }

    # -----------------------------------------------------------------------
    # 1. Determine available player pool
    # -----------------------------------------------------------------------
    available_players: Set[str] = set()
    lineup_players: List[str] = []

    # Try expected lineup first (most precise)
    if lineups_df is not None and not lineups_df.empty:
        mask = lineups_df["team"].str.lower() == team.lower()
        if match_id:
            mask &= lineups_df["match_id"] == match_id
        else:
            mask &= lineups_df["date"] == match_date
        starters = lineups_df[mask & lineups_df["is_starter"]]
        lineup_players = starters["player_id"].tolist()
        if lineup_players:
            feats["has_lineup_data"] = 1.0
            available_players.update(lineup_players)

    # Fall back to roster when no lineup is available
    if not available_players and rosters_df is not None and not rosters_df.empty:
        from src.data.load_rosters import get_team_roster
        roster_rows = get_team_roster(rosters_df, team, match_date)
        roster_players = roster_rows["player_id"].tolist()
        available_players.update(roster_players)

    if not available_players:
        # No player data at all – return safe defaults
        return feats

    # -----------------------------------------------------------------------
    # 2. Ratings
    # -----------------------------------------------------------------------
    ratings: pd.Series = pd.Series(dtype=float)
    if ratings_df is not None and not ratings_df.empty:
        ratings = _latest_ratings(ratings_df, list(available_players), match_date)
        if not ratings.empty:
            feats["has_rating_data"] = 1.0
            feats["squad_overall_rating"] = float(ratings.mean())

    # -----------------------------------------------------------------------
    # 3. Injury / absence filtering
    # -----------------------------------------------------------------------
    injured: Set[str] = _get_injured_players(injuries_df, team, match_date)
    if injuries_df is not None and not injuries_df.empty:
        feats["has_injury_data"] = 1.0

    available_healthy = available_players - injured

    # -----------------------------------------------------------------------
    # 4. Squad continuity
    # -----------------------------------------------------------------------
    if available_players:
        feats["squad_continuity"] = (
            len(available_healthy) / len(available_players)
        )

    # -----------------------------------------------------------------------
    # 5. Missing top-3 players
    # -----------------------------------------------------------------------
    if not ratings.empty:
        top3 = set(ratings.nlargest(3).index)
        feats["missing_top3_count"] = float(len(top3.intersection(injured)))

    # -----------------------------------------------------------------------
    # 6. Starting-XI rating (from expected lineup, healthy players only)
    # -----------------------------------------------------------------------
    healthy_lineup = [p for p in lineup_players if p not in injured]
    if healthy_lineup and not ratings.empty:
        lineup_ratings = ratings.reindex(healthy_lineup).dropna()
        if not lineup_ratings.empty:
            feats["starting_xi_rating"] = float(lineup_ratings.mean())

    # -----------------------------------------------------------------------
    # 7. Position-specific ratings via player identity registry
    # -----------------------------------------------------------------------
    try:
        from src.data.player_identity import CANONICAL_PLAYERS
    except ImportError:
        return feats

    try:
        gk_ratings: List[float] = []
        fwd_ratings: List[float] = []
        def_ratings: List[float] = []

        for pid in available_healthy:
            record = CANONICAL_PLAYERS.get(pid, {})
            position = record.get("position", "")
            rating_val = float(ratings.get(pid, DEFAULTS["overall_rating"]))
            if position == "GK":
                gk_ratings.append(rating_val)
            elif position == "FWD":
                fwd_ratings.append(rating_val)
            elif position == "DEF":
                def_ratings.append(rating_val)

        if gk_ratings:
            feats["gk_rating"] = float(np.mean(gk_ratings))
        if fwd_ratings:
            feats["attack_player_rating"] = float(np.mean(fwd_ratings))
        if def_ratings:
            feats["defense_player_rating"] = float(np.mean(def_ratings))

    except (KeyError, TypeError, ValueError) as exc:
        log.warning("Position-specific rating aggregation failed: %s", exc)

    return feats


def build_player_match_features(
    home_team: str,
    away_team: str,
    match_date: str,
    *,
    match_id: Optional[str] = None,
    rosters_df: Optional[pd.DataFrame] = None,
    ratings_df: Optional[pd.DataFrame] = None,
    injuries_df: Optional[pd.DataFrame] = None,
    lineups_df: Optional[pd.DataFrame] = None,
) -> Dict[str, float]:
    """
    Build home- and away-prefixed player features for one match.

    Returns a flat dict ready to be merged into the match row dict produced
    by ``build_match_row()``. When all data arguments are None or empty,
    all features are set to their safe defaults so the match model still runs.
    """
    home_feats = aggregate_team_player_features(
        home_team, match_date,
        match_id=match_id,
        rosters_df=rosters_df,
        ratings_df=ratings_df,
        injuries_df=injuries_df,
        lineups_df=lineups_df,
    )
    away_feats = aggregate_team_player_features(
        away_team, match_date,
        match_id=match_id,
        rosters_df=rosters_df,
        ratings_df=ratings_df,
        injuries_df=injuries_df,
        lineups_df=lineups_df,
    )

    result: Dict[str, float] = {}
    for k, v in home_feats.items():
        result[f"home_{k}"] = v
    for k, v in away_feats.items():
        result[f"away_{k}"] = v
    return result
