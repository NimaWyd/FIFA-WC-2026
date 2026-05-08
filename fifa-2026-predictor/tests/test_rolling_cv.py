"""Tests for year-based rolling-origin cross-validation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.rolling_cv import rolling_cv_folds


def _make_long_feature_df() -> pd.DataFrame:
    """Feature DataFrame spanning 2005–2024 for fold generation testing."""
    rng = np.random.default_rng(0)
    n = 800
    dates = pd.date_range("2005-01-01", periods=n, freq="10D")
    rest_days_home = rng.integers(1, 30, n).astype(float)
    rest_days_away = rng.integers(1, 30, n).astype(float)
    base_elo = 1500 + rng.normal(0, 100, n)
    elo_diff = rng.normal(0, 50, n)
    return pd.DataFrame({
        "date": dates,
        "home_team": rng.choice(["Brazil", "France", "Germany", "Spain"], n),
        "away_team": rng.choice(["Argentina", "England", "Italy", "Portugal"], n),
        "target": rng.choice(["H", "D", "A"], n, p=[0.45, 0.25, 0.30]),
        "neutral": rng.choice([True, False], n).astype(bool),
        "competition": rng.choice(["FIFA World Cup", "Friendly", "Qualifier"], n),
        "home_confederation": rng.choice(["UEFA", "CONMEBOL", "CONCACAF"], n),
        "away_confederation": rng.choice(["UEFA", "CONMEBOL", "CONCACAF"], n),
        "tournament_stage": rng.choice(["Group Stage", "Unknown", "Final"], n),
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


class TestRollingCvFolds(unittest.TestCase):

    def setUp(self):
        self.df = _make_long_feature_df()

    def test_returns_at_least_one_fold(self):
        folds = rolling_cv_folds(self.df)
        self.assertGreater(len(folds), 0, "Expected at least one fold for 2005–2024 data")

    def test_train_strictly_before_test(self):
        for train, test, year in rolling_cv_folds(self.df):
            self.assertLess(
                train["date"].max(),
                test["date"].min(),
                f"Fold {year}: training data overlaps test window",
            )

    def test_test_window_covers_correct_years(self):
        for train, test, year in rolling_cv_folds(self.df):
            test_years = pd.to_datetime(test["date"]).dt.year.unique()
            self.assertTrue(
                any(y in [year, year + 1] for y in test_years),
                f"Fold {year}: test years {sorted(test_years)} don't include {year} or {year+1}",
            )

    def test_custom_test_years(self):
        folds = rolling_cv_folds(self.df, test_years=[2013, 2017])
        fold_years = [y for _, _, y in folds]
        self.assertEqual(sorted(fold_years), [2013, 2017])

    def test_skips_folds_with_insufficient_data(self):
        tiny_df = self.df.iloc[:50].copy()
        folds = rolling_cv_folds(tiny_df, test_years=[2023])
        self.assertEqual(len(folds), 0, "Should skip fold when train < 100 rows")


if __name__ == "__main__":
    unittest.main()
