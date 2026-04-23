"""Build a single pre-match feature row from a TeamStateTracker snapshot.

This is the single source of truth for feature construction.  Both the
training pipeline (build_features.py) and the inference app (predict_match.py)
call build_match_row() so they are guaranteed to produce identical features.

Phase 4 additions
-----------------
- Recency-weighted form: home/away_form_rw5
- Multiple form horizons: w3 (last 3) and w10 (last 10) in addition to w5
- Attack / defense decomposition: home/away_attack_w5, home/away_defense_w5
  (also recency-weighted variants: _rw5)
- Opponent-strength-adjusted features: home/away_adj_form_w5,
  home/away_adj_attack_w5, home/away_adj_defense_w5
- Derived difference features: attack_diff_w5, defense_diff_w5,
  adj_form_diff_w5, form_diff_w3, form_diff_w10
- Tournament stage normalization + stage_importance numeric feature
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.features.competition_weights import (
    DEFAULT_COMPETITION_WEIGHT,
    get_competition_weight,
    get_stage_importance,
    normalize_tournament_stage,
)
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
    h2h_window: int = 10,
) -> dict[str, Any]:
    """Return a pre-match feature dict from the current tracker state.

    This function is *read-only* with respect to the tracker — it never
    mutates state.  Call tracker.update() separately after observing the
    match result (training) or not at all (inference).

    The returned dict is ready to be converted to a single-row DataFrame
    accepted by the sklearn pipeline.
    """
    # --- Existing Phase 1–3 features ---

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

    # --- Phase 4: multi-horizon form ---

    home_form_w3 = tracker.form_window(home_team, 3)
    away_form_w3 = tracker.form_window(away_team, 3)
    home_form_w10 = tracker.form_window(home_team, 10)
    away_form_w10 = tracker.form_window(away_team, 10)

    # --- Phase 4: recency-weighted form ---

    home_form_rw5 = tracker.form_recency_weighted(home_team, 5)
    away_form_rw5 = tracker.form_recency_weighted(away_team, 5)

    # --- Phase 4: attack / defense decomposition ---

    home_attack_w5 = tracker.attack_rating(home_team, 5, recency=False)
    away_attack_w5 = tracker.attack_rating(away_team, 5, recency=False)
    home_defense_w5 = tracker.defense_rating(home_team, 5, recency=False)
    away_defense_w5 = tracker.defense_rating(away_team, 5, recency=False)

    home_attack_rw5 = tracker.attack_rating(home_team, 5, recency=True)
    away_attack_rw5 = tracker.attack_rating(away_team, 5, recency=True)
    home_defense_rw5 = tracker.defense_rating(home_team, 5, recency=True)
    away_defense_rw5 = tracker.defense_rating(away_team, 5, recency=True)

    # --- Phase 4: opponent-adjusted features ---

    home_adj_form_w5 = tracker.opp_adjusted_form(home_team, 5)
    away_adj_form_w5 = tracker.opp_adjusted_form(away_team, 5)
    home_adj_attack_w5 = tracker.opp_adjusted_attack(home_team, 5)
    away_adj_attack_w5 = tracker.opp_adjusted_attack(away_team, 5)
    home_adj_defense_w5 = tracker.opp_adjusted_defense(home_team, 5)
    away_adj_defense_w5 = tracker.opp_adjusted_defense(away_team, 5)

    # --- Phase 4: tournament stage ---

    stage_norm = normalize_tournament_stage(tournament_stage)
    stage_imp = get_stage_importance(tournament_stage)

    # --- Phase 7: draw-rate features ---

    home_draw_rate_w5 = tracker.draw_rate(home_team, 5)
    away_draw_rate_w5 = tracker.draw_rate(away_team, 5)

    # --- Phase 7: head-to-head features ---

    h2h = tracker.h2h_stats(home_team, away_team, window=h2h_window)

    return {
        # Match metadata
        "date": match_date,
        "home_team": home_team,
        "away_team": away_team,
        "competition": competition,
        "neutral": int(neutral),
        "home_confederation": home_confederation,
        "away_confederation": away_confederation,
        "home_fifa_rank": int(home_fifa_rank),
        "away_fifa_rank": int(away_fifa_rank),
        # Tournament stage (normalized canonical form)
        "tournament_stage": stage_norm,
        "stage_importance": stage_imp,
        # Elo
        "home_elo_pre": home_elo,
        "away_elo_pre": away_elo,
        "elo_diff_home_away": home_elo - away_elo,
        "elo_win_prob": tracker.elo_win_prob(home_team, away_team, neutral),
        # Legacy form / goals (Phase 1–3 backward compat, window = form_window=5)
        "home_form_last5": home_form,
        "away_form_last5": away_form,
        "home_goals_for_last5": home_gf,
        "away_goals_for_last5": away_gf,
        "home_goals_against_last5": home_ga,
        "away_goals_against_last5": away_ga,
        "form_diff_home_away": home_form - away_form,
        "goal_balance_diff": (home_gf - home_ga) - (away_gf - away_ga),
        # Rest
        "home_rest_days": home_rest,
        "away_rest_days": away_rest,
        # Derived team context
        "rank_diff": int(home_fifa_rank) - int(away_fifa_rank),
        "competition_weight": get_competition_weight(competition),
        "is_same_confederation": int(home_confederation == away_confederation),
        # --- Phase 4 new features ---
        # Multi-horizon form
        "home_form_w3": home_form_w3,
        "away_form_w3": away_form_w3,
        "home_form_w10": home_form_w10,
        "away_form_w10": away_form_w10,
        # Recency-weighted form
        "home_form_rw5": home_form_rw5,
        "away_form_rw5": away_form_rw5,
        # Attack / defense decomposition
        "home_attack_w5": home_attack_w5,
        "away_attack_w5": away_attack_w5,
        "home_defense_w5": home_defense_w5,
        "away_defense_w5": away_defense_w5,
        "home_attack_rw5": home_attack_rw5,
        "away_attack_rw5": away_attack_rw5,
        "home_defense_rw5": home_defense_rw5,
        "away_defense_rw5": away_defense_rw5,
        # Opponent-adjusted features
        "home_adj_form_w5": home_adj_form_w5,
        "away_adj_form_w5": away_adj_form_w5,
        "home_adj_attack_w5": home_adj_attack_w5,
        "away_adj_attack_w5": away_adj_attack_w5,
        "home_adj_defense_w5": home_adj_defense_w5,
        "away_adj_defense_w5": away_adj_defense_w5,
        # Derived differences
        "attack_diff_w5": home_attack_w5 - away_attack_w5,
        "defense_diff_w5": away_defense_w5 - home_defense_w5,
        "adj_form_diff_w5": home_adj_form_w5 - away_adj_form_w5,
        "form_diff_w3": home_form_w3 - away_form_w3,
        "form_diff_w10": home_form_w10 - away_form_w10,
        # --- Phase 7: draw rate ---
        "home_draw_rate_w5": home_draw_rate_w5,
        "away_draw_rate_w5": away_draw_rate_w5,
        "draw_rate_diff": home_draw_rate_w5 - away_draw_rate_w5,
        # --- Phase 7: head-to-head ---
        "h2h_home_win_rate": h2h["home_win_rate"],
        "h2h_draw_rate": h2h["draw_rate"],
        "h2h_goal_diff": h2h["goal_diff"],
        "h2h_n_matches": float(h2h["n_matches"]),
    }
