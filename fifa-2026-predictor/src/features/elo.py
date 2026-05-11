"""Simple Elo engine for national team ratings."""

from __future__ import annotations

from dataclasses import dataclass

# Elo range assigned to FIFA-ranked teams (rank 1 → MAX, rank ~210 → MIN).
_ELO_RANK_MAX = 1900.0
_ELO_RANK_MIN = 1500.0
_ELO_RANK_SPAN = 210  # approximate total number of FIFA-ranked nations


@dataclass
class EloConfig:
    k_factor: float = 40.0
    home_advantage: float = 100.0
    base_rating: float = 1500.0


def rank_to_starting_elo(rank: int | None) -> float:
    """Convert a FIFA rank to an initial Elo rating.

    Linear mapping: rank 1 → 1900, rank 210 → 1500.
    Unranked teams (rank=None) get 1450 (below the minimum for ranked nations).
    """
    if rank is None:
        return 1450.0
    rank = max(1, rank)
    elo = _ELO_RANK_MAX - (rank - 1) * (_ELO_RANK_MAX - _ELO_RANK_MIN) / _ELO_RANK_SPAN
    return max(_ELO_RANK_MIN, elo)


def expected_score(rating_a: float, rating_b: float) -> float:
    """Expected score of team A vs team B."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def actual_score(home_goals: int, away_goals: int) -> tuple[float, float]:
    """Return actual Elo points from final result."""
    if home_goals > away_goals:
        return 1.0, 0.0
    if home_goals < away_goals:
        return 0.0, 1.0
    return 0.5, 0.5


def goal_margin_multiplier(home_goals: int, away_goals: int) -> float:
    """Weight K by margin of victory — larger wins move ratings more."""
    gd = abs(home_goals - away_goals)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0


def update_ratings(
    home_rating: float,
    away_rating: float,
    home_goals: int,
    away_goals: int,
    neutral: bool,
    cfg: EloConfig,
    competition_k_multiplier: float = 1.0,
) -> tuple[float, float]:
    """Update two team ratings after a match.

    *competition_k_multiplier* scales the K-factor by competition importance:
    >1 for high-stakes tournaments, <1 for friendlies.
    """
    adjusted_home = home_rating + (0.0 if neutral else cfg.home_advantage)
    exp_home = expected_score(adjusted_home, away_rating)
    exp_away = 1.0 - exp_home
    act_home, act_away = actual_score(home_goals, away_goals)
    mult = goal_margin_multiplier(home_goals, away_goals)
    effective_k = cfg.k_factor * competition_k_multiplier

    new_home = home_rating + effective_k * mult * (act_home - exp_home)
    new_away = away_rating + effective_k * mult * (act_away - exp_away)
    return new_home, new_away
