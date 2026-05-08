"""Tests for World Cup backtest script."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.backtest_world_cup import (
    TOURNAMENTS,
    _per_sample_log_loss,
    backtest_tournament,
)


def _cfg() -> dict:
    return {
        "project": {"random_state": 42},
        "features": {
            "form_window": 5,
            "elo_k_factor": 40.0,
            "elo_home_advantage": 100.0,
            "default_fifa_rank": 75,
            "time_decay_halflife_days": 730,
        },
        "model": {
            "logistic_max_iter": 200,
            "xgb": {
                "n_estimators": 10,
                "learning_rate": 0.1,
                "max_depth": 2,
                "subsample": 1.0,
                "colsample_bytree": 1.0,
                "min_child_weight": 1,
                "gamma": 0.0,
                "reg_alpha": 0.0,
                "reg_lambda": 1.0,
            },
        },
    }


def _make_wc_feature_df(wc_year: int = 2018, n_pre: int = 200, n_wc: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(wc_year)
    n = n_pre + n_wc
    pre_dates = pd.date_range("2010-01-01", periods=n_pre, freq="10D")
    wc_dates = pd.date_range(f"{wc_year}-06-15", periods=n_wc, freq="2D")
    dates = list(pre_dates) + list(wc_dates)
    competition = (["Friendly"] * n_pre) + (["FIFA World Cup"] * n_wc)
    tournament_stage = (["Unknown"] * n_pre) + (
        ["Group Stage"] * 18 + ["Round of 16"] * 8 + ["Quarter-final"] * 4
    )
    rest_days_home = rng.integers(1, 30, n).astype(float)
    rest_days_away = rng.integers(1, 30, n).astype(float)
    base_elo = 1500 + rng.normal(0, 100, n)
    elo_diff = rng.normal(0, 50, n)
    return pd.DataFrame({
        "date": dates,
        "home_team": rng.choice(["Brazil", "France", "Germany", "Spain"], n),
        "away_team": rng.choice(["Argentina", "England", "Italy", "Portugal"], n),
        "target": rng.choice(["H", "D", "A"], n, p=[0.45, 0.25, 0.30]),
        "neutral": [True] * n,
        "competition": competition,
        "home_confederation": rng.choice(["UEFA", "CONMEBOL", "CONCACAF"], n),
        "away_confederation": rng.choice(["UEFA", "CONMEBOL", "CONCACAF"], n),
        "tournament_stage": tournament_stage,
        "home_fifa_rank": rng.integers(1, 100, n),
        "away_fifa_rank": rng.integers(1, 100, n),
        "home_elo_pre": base_elo,
        "away_elo_pre": base_elo + elo_diff,
        "elo_diff_home_away": elo_diff,
        "elo_win_prob": 1 / (1 + 10 ** (-elo_diff / 400)),
        "home_form_last5": rng.uniform(0, 3, n),
        "away_form_last5": rng.uniform(0, 3, n),
        "home_goals_for_last5": rng.uniform(0, 3, n),
        "away_goals_for_last5": rng.uniform(0, 3, n),
        "home_goals_against_last5": rng.uniform(0, 3, n),
        "away_goals_against_last5": rng.uniform(0, 3, n),
        "home_rest_days_log": np.log1p(rest_days_home),
        "away_rest_days_log": np.log1p(rest_days_away),
        "home_long_break": (rest_days_home > 21).astype(int),
        "away_long_break": (rest_days_away > 21).astype(int),
        "form_diff_home_away": rng.normal(0, 1, n),
        "goal_balance_diff": rng.normal(0, 1, n),
        "rank_diff": rng.integers(-50, 50, n).astype(float),
        "competition_weight": rng.choice([1, 2, 3, 4, 5], n).astype(float),
        "is_same_confederation": rng.choice([0, 1], n),
        "match_weight": rng.uniform(0.5, 1.0, n),
        "home_score": rng.integers(0, 5, n),
        "away_score": rng.integers(0, 5, n),
    })


class TestPerSampleLogLoss(unittest.TestCase):
    def test_correct_outcome_gives_low_loss(self):
        y_true = np.array([2])
        y_prob = np.array([[0.05, 0.05, 0.90]])
        loss = _per_sample_log_loss(y_true, y_prob)
        self.assertLess(float(loss[0]), 0.2)

    def test_wrong_confident_outcome_gives_high_loss(self):
        y_true = np.array([2])
        y_prob = np.array([[0.90, 0.05, 0.05]])
        loss = _per_sample_log_loss(y_true, y_prob)
        self.assertGreater(float(loss[0]), 2.0)


class TestBacktestTournament(unittest.TestCase):
    def setUp(self):
        self.df = _make_wc_feature_df(wc_year=2018)
        self.cfg = _cfg()
        self.tournament = {"name": "WC2018", "cutoff": "2018-06-14", "year": 2018}

    def test_returns_expected_keys(self):
        result = backtest_tournament(self.df, self.cfg, self.tournament)
        self.assertNotIn("error", result, f"Unexpected error: {result.get('error')}")
        for key in ("name", "n_train", "n_test", "overall", "by_stage", "worst_predictions"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_overall_has_accuracy_and_log_loss(self):
        result = backtest_tournament(self.df, self.cfg, self.tournament)
        self.assertIn("accuracy", result["overall"])
        self.assertIn("log_loss", result["overall"])
        self.assertGreaterEqual(result["overall"]["accuracy"], 0.0)
        self.assertLessEqual(result["overall"]["accuracy"], 1.0)

    def test_by_stage_non_empty(self):
        result = backtest_tournament(self.df, self.cfg, self.tournament)
        self.assertGreater(len(result["by_stage"]), 0)

    def test_worst_predictions_at_most_10(self):
        result = backtest_tournament(self.df, self.cfg, self.tournament)
        self.assertLessEqual(len(result["worst_predictions"]), 10)

    def test_worst_predictions_have_required_fields(self):
        result = backtest_tournament(self.df, self.cfg, self.tournament)
        for w in result["worst_predictions"]:
            for field in ("home_team", "away_team", "date", "actual", "p_home", "p_draw", "p_away", "loss"):
                self.assertIn(field, w, f"Missing field '{field}' in worst prediction")

    def test_no_wc_matches_returns_error(self):
        df_no_wc = self.df[self.df["competition"] != "FIFA World Cup"].copy()
        result = backtest_tournament(df_no_wc, self.cfg, self.tournament)
        self.assertIn("error", result)

    def test_tournaments_constant_has_wc2018_and_wc2022(self):
        names = [t["name"] for t in TOURNAMENTS]
        self.assertIn("WC2018", names)
        self.assertIn("WC2022", names)


if __name__ == "__main__":
    unittest.main()
