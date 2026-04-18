"""Build a single pre-match feature row from a TeamStateTracker snapshot.

This is the single source of truth for feature construction.  Both the
training pipeline (build_features.py) and the inference app (predict_match.py)
call build_match_row() so they are guaranteed to produce identical features.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.features.competition_weights import COMPETITION_WEIGHTS, DEFAULT_COMPETITION_WEIGHT
from src.features.state_tracker import TeamStateTracker


def build_match_row(
    tracker: TeamStateTracker,
    home_team: str,
    away_team: str,
    match_date: pd.Timestamp,
    competition: str,
    neutral: bool,
    home_confederation: str,
    away_confederation: str,
    home_fifa_rank: int,
    away_fifa_rank: int,
    tournament_stage: str,
) -> dict[str, Any]:
    """Return a pre-match feature dict from the current tracker state.

    This function is *read-only* with respect to the tracker — it never
    mutates state.  Call tracker.update() separately after observing the
    match result (training) or not at all (inference).

    The returned dict is ready to be converted to a single-row DataFrame
    accepted by the sklearn pipeline.
    """
    home_form = tracker.form(home_team)
    away_form = tracker.form(away_team)
    home_gf = tracker.goals_for(home_team)
    away_gf = tracker.goals_for(away_team)
    home_ga = tracker.goals_against(home_team)
    away_ga = tracker.goals_against(away_team)
    home_elo = tracker.elo(home_team)
    away_elo = tracker.elo(away_team)
    home_rest = tracker.rest_days(home_team, match_date)
    away_rest = tracker.rest_days(away_team, match_date)

    return {
        "date": match_date,
        "home_team": home_team,
        "away_team": away_team,
        "competition": competition,
        "neutral": int(neutral),
        "home_confederation": home_confederation,
        "away_confederation": away_confederation,
        "home_fifa_rank": int(home_fifa_rank),
        "away_fifa_rank": int(away_fifa_rank),
        "tournament_stage": tournament_stage,
        "home_form_last5": home_form,
        "away_form_last5": away_form,
        "home_goals_for_last5": home_gf,
        "away_goals_for_last5": away_gf,
        "home_goals_against_last5": home_ga,
        "away_goals_against_last5": away_ga,
        "home_rest_days": home_rest,
        "away_rest_days": away_rest,
        "home_elo_pre": home_elo,
        "away_elo_pre": away_elo,
        "elo_diff_home_away": home_elo - away_elo,
        "elo_win_prob": tracker.elo_win_prob(home_team, away_team, neutral),
        "form_diff_home_away": home_form - away_form,
        "goal_balance_diff": (home_gf - home_ga) - (away_gf - away_ga),
        "rank_diff": int(home_fifa_rank) - int(away_fifa_rank),
        "competition_weight": COMPETITION_WEIGHTS.get(competition, DEFAULT_COMPETITION_WEIGHT),
        "is_same_confederation": int(home_confederation == away_confederation),
    }
