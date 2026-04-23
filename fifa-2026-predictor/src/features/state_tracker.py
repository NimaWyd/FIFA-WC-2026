"""Shared team-state management for training and inference.

Both build_features.py (training) and predict_match.py (inference) replay a
chronological match history through TeamStateTracker to derive consistent
pre-match features — Elo, form, goals, rest-day, attack/defense, and
opponent-adjusted ratings.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

import numpy as np
import pandas as pd

from src.features.competition_weights import (
    DEFAULT_COMPETITION_K_MULTIPLIER,
    get_competition_k_multiplier,
)
from src.features.elo import EloConfig, expected_score, update_ratings


class TeamStateTracker:
    """Accumulate rolling per-team state as matches are processed in order.

    Phase 4 additions
    -----------------
    - Extended per-team match history (maxlen=20) for multi-window and
      recency-weighted feature access.
    - Competition-aware Elo updates: K-factor is scaled by competition
      importance before each update.
    - New accessors: form_window, form_recency_weighted, attack_rating,
      defense_rating, opp_adjusted_form, opp_adjusted_attack,
      opp_adjusted_defense.

    Typical usage
    -------------
    Training:

        tracker = TeamStateTracker(cfg)
        for row in matches.itertuples():
            features = build_match_row(tracker, ...)   # snapshot BEFORE update
            tracker.update(..., competition=row.competition)

    Inference:

        tracker = TeamStateTracker(cfg)
        tracker.replay_history(history_before_match)
        features = build_match_row(tracker, ...)
    """

    # Entries in _history beyond _MAX_HISTORY are silently dropped.
    _MAX_HISTORY: int = 30
    # Separate H2H deque per canonical pair (sorted tuple of names).
    _MAX_H2H: int = 15

    def __init__(self, cfg: dict[str, Any]) -> None:
        form_window = int(cfg["features"]["form_window"])
        self.elo_cfg = EloConfig(
            k_factor=float(cfg["features"]["elo_k_factor"]),
            home_advantage=float(cfg["features"]["elo_home_advantage"]),
        )
        self._form_window = form_window
        self._recency_halflife = float(
            cfg["features"].get("recency_halflife_days", 180.0)
        )

        self._ratings: dict[str, float] = defaultdict(lambda: self.elo_cfg.base_rating)

        # Legacy deques (backward compat — drive form(), goals_for(), goals_against())
        self._form: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._form_window)
        )
        self._goals_for: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._form_window)
        )
        self._goals_against: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._form_window)
        )
        self._last_played: dict[str, pd.Timestamp] = {}

        # Extended history for Phase 4 features.
        # Each entry is a dict: {date, points, gf, ga, opp_elo_pre, opponent, is_draw}
        self._history: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._MAX_HISTORY)
        )

        # Head-to-head history per canonical pair (sorted tuple → deque).
        # Each entry: {date, home_team, away_team, home_goals, away_goals}
        # Stored once per match regardless of home/away assignment.
        self._h2h: dict[tuple, deque] = defaultdict(
            lambda: deque(maxlen=self._MAX_H2H)
        )

    # ------------------------------------------------------------------
    # Backward-compatible accessors (Phase 1–3 interface)
    # ------------------------------------------------------------------

    def elo(self, team: str) -> float:
        """Current Elo rating (base rating if unseen)."""
        return float(self._ratings[team])

    def form(self, team: str) -> float:
        """Mean points-per-game over last form_window matches (1.5 default)."""
        return float(np.mean(self._form[team])) if self._form[team] else 1.5

    def goals_for(self, team: str) -> float:
        """Mean goals scored per game over last form_window matches (1.0 default)."""
        return float(np.mean(self._goals_for[team])) if self._goals_for[team] else 1.0

    def goals_against(self, team: str) -> float:
        """Mean goals conceded per game over last form_window matches (1.0 default)."""
        return (
            float(np.mean(self._goals_against[team]))
            if self._goals_against[team]
            else 1.0
        )

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
    # Phase 4 internal helpers
    # ------------------------------------------------------------------

    def _history_slice(self, team: str, window: int) -> list[dict]:
        """Last N history entries for *team*."""
        h = self._history[team]
        return list(h)[-window:] if h else []

    def _recency_weights(
        self, history_slice: list[dict], halflife: float
    ) -> list[float]:
        """Exponential decay weights.  Most recent entry → weight 1.0."""
        if not history_slice:
            return []
        ref_date = history_slice[-1]["date"]
        return [
            0.5 ** (max(0, (ref_date - h["date"]).days) / halflife)
            for h in history_slice
        ]

    # ------------------------------------------------------------------
    # Phase 4 accessors
    # ------------------------------------------------------------------

    def form_window(self, team: str, window: int = 5) -> float:
        """Plain average points-per-game over last *window* matches."""
        hist = self._history_slice(team, window)
        if not hist:
            return 1.5
        return sum(h["points"] for h in hist) / len(hist)

    def form_recency_weighted(self, team: str, window: int = 5) -> float:
        """Exponentially recency-weighted points-per-game.

        More recent matches contribute more than older ones within the window.
        Halflife is configured via cfg['features']['recency_halflife_days'].
        """
        hist = self._history_slice(team, window)
        if not hist:
            return 1.5
        weights = self._recency_weights(hist, self._recency_halflife)
        total_w = sum(weights)
        if total_w == 0:
            return 1.5
        return sum(w * h["points"] for w, h in zip(weights, hist)) / total_w

    def attack_rating(
        self, team: str, window: int = 5, recency: bool = False
    ) -> float:
        """Goals scored per match over last *window* matches.

        When *recency=True* weights recent matches exponentially more.
        """
        hist = self._history_slice(team, window)
        if not hist:
            return 1.0
        if recency:
            weights = self._recency_weights(hist, self._recency_halflife)
            total_w = sum(weights)
            if total_w == 0:
                return 1.0
            return sum(w * h["gf"] for w, h in zip(weights, hist)) / total_w
        return sum(h["gf"] for h in hist) / len(hist)

    def defense_rating(
        self, team: str, window: int = 5, recency: bool = False
    ) -> float:
        """Goals conceded per match over last *window* matches (lower = better).

        When *recency=True* weights recent matches exponentially more.
        """
        hist = self._history_slice(team, window)
        if not hist:
            return 1.0
        if recency:
            weights = self._recency_weights(hist, self._recency_halflife)
            total_w = sum(weights)
            if total_w == 0:
                return 1.0
            return sum(w * h["ga"] for w, h in zip(weights, hist)) / total_w
        return sum(h["ga"] for h in hist) / len(hist)

    def opp_adjusted_form(self, team: str, window: int = 5) -> float:
        """Form adjusted proportionally by opponent Elo strength.

        Points earned against a team rated 1500 count at face value.
        Points against a team rated 2000 count 33% more (2000/1500).
        This rewards good results against strong opposition.
        """
        hist = self._history_slice(team, window)
        if not hist:
            return 1.5
        base = self.elo_cfg.base_rating
        return (
            sum(h["points"] * (h["opp_elo_pre"] / base) for h in hist) / len(hist)
        )

    def opp_adjusted_attack(self, team: str, window: int = 5) -> float:
        """Goals scored adjusted for opponent strength.

        More goals against a higher-rated opponent → higher adjusted value.
        """
        hist = self._history_slice(team, window)
        if not hist:
            return 1.0
        base = self.elo_cfg.base_rating
        return (
            sum(h["gf"] * (h["opp_elo_pre"] / base) for h in hist) / len(hist)
        )

    def opp_adjusted_defense(self, team: str, window: int = 5) -> float:
        """Goals conceded adjusted for opponent strength (lower = better defense).

        Conceding goals against a weak opponent is penalized more than
        conceding the same number against a strong opponent.
        """
        hist = self._history_slice(team, window)
        if not hist:
            return 1.0
        base = self.elo_cfg.base_rating
        return (
            sum(h["ga"] * (base / h["opp_elo_pre"]) for h in hist) / len(hist)
        )

    def draw_rate(self, team: str, window: int = 5) -> float:
        """Fraction of last *window* matches that ended in a draw.

        Returns 0.25 (historical average) when history is empty.
        """
        hist = self._history_slice(team, window)
        if not hist:
            return 0.25
        return sum(1 for h in hist if h.get("is_draw", False)) / len(hist)

    def h2h_stats(
        self,
        home_team: str,
        away_team: str,
        window: int = 10,
    ) -> dict:
        """Head-to-head stats for the pair in the last *window* encounters.

        Returns stats from the perspective of *home_team* (wins = home wins).
        When no h2h history exists all values fall back to sensible priors.
        """
        pair = tuple(sorted([home_team, away_team]))
        entries = list(self._h2h.get(pair, deque()))[-window:]

        if not entries:
            return {
                "home_win_rate": 0.45,
                "draw_rate": 0.25,
                "goal_diff": 0.0,
                "n_matches": 0,
            }

        home_wins = draws = 0
        goal_diff_total = 0.0
        for e in entries:
            hg, ag = e["home_goals"], e["away_goals"]
            # Reframe from home_team's perspective
            if e["home_team"] == home_team:
                team_goals, opp_goals = hg, ag
            else:
                team_goals, opp_goals = ag, hg
            goal_diff_total += team_goals - opp_goals
            if team_goals > opp_goals:
                home_wins += 1
            elif team_goals == opp_goals:
                draws += 1

        n = len(entries)
        return {
            "home_win_rate": home_wins / n,
            "draw_rate": draws / n,
            "goal_diff": goal_diff_total / n,
            "n_matches": n,
        }

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
        competition: str = "Unknown",
    ) -> None:
        """Advance state after a completed match result.

        *competition* drives the K-factor multiplier so World Cup matches
        move ratings more than friendlies.
        """
        # Capture pre-match Elos before update (needed for opp_elo_pre in history)
        home_elo_pre = float(self._ratings[home_team])
        away_elo_pre = float(self._ratings[away_team])

        # Competition-aware Elo update (normalise name before lookup)
        comp_k = get_competition_k_multiplier(competition)
        home_new, away_new = update_ratings(
            home_rating=home_elo_pre,
            away_rating=away_elo_pre,
            home_goals=home_goals,
            away_goals=away_goals,
            neutral=neutral,
            cfg=self.elo_cfg,
            competition_k_multiplier=comp_k,
        )
        self._ratings[home_team] = home_new
        self._ratings[away_team] = away_new

        hp = 3 if home_goals > away_goals else 1 if home_goals == away_goals else 0
        ap = 3 if away_goals > home_goals else 1 if home_goals == away_goals else 0

        # Legacy deques (backward compat)
        self._form[home_team].append(hp)
        self._form[away_team].append(ap)
        self._goals_for[home_team].append(home_goals)
        self._goals_for[away_team].append(away_goals)
        self._goals_against[home_team].append(away_goals)
        self._goals_against[away_team].append(home_goals)

        is_draw = home_goals == away_goals

        # Extended history with opponent Elo context + draw/opponent fields
        self._history[home_team].append(
            {
                "date": date,
                "points": hp,
                "gf": home_goals,
                "ga": away_goals,
                "opp_elo_pre": away_elo_pre,
                "opponent": away_team,
                "is_draw": is_draw,
            }
        )
        self._history[away_team].append(
            {
                "date": date,
                "points": ap,
                "gf": away_goals,
                "ga": home_goals,
                "opp_elo_pre": home_elo_pre,
                "opponent": home_team,
                "is_draw": is_draw,
            }
        )

        # Head-to-head history (canonical pair key, independent of home/away)
        pair = tuple(sorted([home_team, away_team]))
        self._h2h[pair].append(
            {
                "date": date,
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": home_goals,
                "away_goals": away_goals,
            }
        )

        self._last_played[home_team] = date
        self._last_played[away_team] = date

    def replay_history(self, history: pd.DataFrame) -> None:
        """Replay a chronologically-sorted match history to populate state.

        *history* must have columns: home_team, away_team, home_score,
        away_score, neutral, date.  The 'competition' column is used when
        present; otherwise the default K-multiplier applies.
        """
        for row in history.itertuples(index=False):
            competition = str(getattr(row, "competition", "Unknown"))
            self.update(
                home_team=str(row.home_team),
                away_team=str(row.away_team),
                home_goals=int(row.home_score),
                away_goals=int(row.away_score),
                neutral=bool(row.neutral),
                date=pd.Timestamp(row.date),
                competition=competition,
            )
