"""Simple Elo engine for national team ratings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EloConfig:
    k_factor: float = 20.0
    home_advantage: float = 45.0
    base_rating: float = 1500.0


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


def update_ratings(
    home_rating: float,
    away_rating: float,
    home_goals: int,
    away_goals: int,
    neutral: bool,
    cfg: EloConfig,
) -> tuple[float, float]:
    """Update two team ratings after a match."""
    adjusted_home = home_rating + (0.0 if neutral else cfg.home_advantage)
    exp_home = expected_score(adjusted_home, away_rating)
    exp_away = 1.0 - exp_home
    act_home, act_away = actual_score(home_goals, away_goals)

    new_home = home_rating + cfg.k_factor * (act_home - exp_home)
    new_away = away_rating + cfg.k_factor * (act_away - exp_away)
    return new_home, new_away

