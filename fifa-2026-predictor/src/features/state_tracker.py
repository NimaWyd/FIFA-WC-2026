"""Shared team-state management for training and inference.

Both build_features.py (training) and predict_match.py (inference) replay a
chronological match history through TeamStateTracker to derive consistent
pre-match Elo, form, goals and rest-day features.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

import numpy as np
import pandas as pd

from src.features.elo import EloConfig, expected_score, update_ratings


class TeamStateTracker:
    """Accumulate rolling per-team state as matches are processed in order.

    Typical usage
    -------------
    Training (one pass over all historical matches):

        tracker = TeamStateTracker(cfg)
        for row in matches.itertuples():
            features = build_match_row(tracker, ...)   # snapshot BEFORE update
            tracker.update(...)                         # advance state

    Inference (replay history, then read state for the target fixture):

        tracker = TeamStateTracker(cfg)
        tracker.replay_history(history_before_match_date)
        features = build_match_row(tracker, ...)
    """

    def __init__(self, cfg: dict[str, Any]) -> None:
        form_window = int(cfg["features"]["form_window"])
        self.elo_cfg = EloConfig(
            k_factor=float(cfg["features"]["elo_k_factor"]),
            home_advantage=float(cfg["features"]["elo_home_advantage"]),
        )
        self._form_window = form_window
        # Use lambdas so new teams get sensible defaults on first access
        self._ratings: dict[str, float] = defaultdict(lambda: self.elo_cfg.base_rating)
        self._form: dict[str, deque] = defaultdict(lambda: deque(maxlen=self._form_window))
        self._goals_for: dict[str, deque] = defaultdict(lambda: deque(maxlen=self._form_window))
        self._goals_against: dict[str, deque] = defaultdict(lambda: deque(maxlen=self._form_window))
        self._last_played: dict[str, pd.Timestamp] = {}

    # ------------------------------------------------------------------
    # Read-only accessors (pre-match snapshot)
    # ------------------------------------------------------------------

    def elo(self, team: str) -> float:
        """Current Elo rating for *team* (base rating if unseen)."""
        return float(self._ratings[team])

    def form(self, team: str) -> float:
        """Mean points-per-game over last N matches (1.5 default if no history)."""
        return float(np.mean(self._form[team])) if self._form[team] else 1.5

    def goals_for(self, team: str) -> float:
        """Mean goals scored per game over last N matches (1.0 default)."""
        return float(np.mean(self._goals_for[team])) if self._goals_for[team] else 1.0

    def goals_against(self, team: str) -> float:
        """Mean goals conceded per game over last N matches (1.0 default)."""
        return float(np.mean(self._goals_against[team])) if self._goals_against[team] else 1.0

    def rest_days(self, team: str, match_date: pd.Timestamp) -> int:
        """Days since team's last match (7 default if no history)."""
        if team not in self._last_played:
            return 7
        return max(0, (match_date - self._last_played[team]).days)

    def elo_win_prob(self, home_team: str, away_team: str, neutral: bool) -> float:
        """P(home win) from Elo, applying home advantage when not neutral."""
        adj = self.elo(home_team) + (0.0 if neutral else self.elo_cfg.home_advantage)
        return float(expected_score(adj, self.elo(away_team)))

    # ------------------------------------------------------------------
    # State mutation
    # ------------------------------------------------------------------

    def update(
        self,
        home_team: str,
        away_team: str,
        home_goals: int,
        away_goals: int,
        neutral: bool,
        date: pd.Timestamp,
    ) -> None:
        """Advance state after a completed match result."""
        home_new, away_new = update_ratings(
            home_rating=self._ratings[home_team],
            away_rating=self._ratings[away_team],
            home_goals=home_goals,
            away_goals=away_goals,
            neutral=neutral,
            cfg=self.elo_cfg,
        )
        self._ratings[home_team] = home_new
        self._ratings[away_team] = away_new

        hp = 3 if home_goals > away_goals else 1 if home_goals == away_goals else 0
        ap = 3 if away_goals > home_goals else 1 if home_goals == away_goals else 0
        self._form[home_team].append(hp)
        self._form[away_team].append(ap)

        self._goals_for[home_team].append(home_goals)
        self._goals_for[away_team].append(away_goals)
        self._goals_against[home_team].append(away_goals)
        self._goals_against[away_team].append(home_goals)

        self._last_played[home_team] = date
        self._last_played[away_team] = date

    def replay_history(self, history: pd.DataFrame) -> None:
        """Replay a chronologically-sorted match history to populate state.

        *history* must have columns: home_team, away_team, home_score,
        away_score, neutral, date.
        """
        for row in history.itertuples(index=False):
            self.update(
                home_team=str(row.home_team),
                away_team=str(row.away_team),
                home_goals=int(row.home_score),
                away_goals=int(row.away_score),
                neutral=bool(row.neutral),
                date=pd.Timestamp(row.date),
            )
