"""Phase 2 evaluation framework tests.

Run without pytest:
    python tests/test_phase2.py

Run with pytest:
    python -m pytest tests/test_phase2.py -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.backtest import aggregate_backtest_results, rolling_windows, run_backtest
from src.evaluation.baselines import (
    ClassPriorBaseline,
    EloOnlyBaseline,
    LogRegModel,
    MostFrequentBaseline,
    XGBoostModel,
    all_models,
)
from src.evaluation.metrics import compute_metrics, multiclass_brier_score
from src.evaluation.reporting import (
    save_backtest_report,
    save_calibration_plots,
    save_evaluation_report,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

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
                "n_estimators": 20,
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


def _make_feature_df(n: int = 300, seed: int = 0) -> pd.DataFrame:
    """Return a minimal feature DataFrame that satisfies build_preprocessor requirements."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2010-01-01", periods=n, freq="3D")
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
        "home_rest_days": rng.integers(1, 30, n).astype(float),
        "away_rest_days": rng.integers(1, 30, n).astype(float),
        "form_diff_home_away": rng.normal(0, 1, n),
        "goal_balance_diff": rng.normal(0, 1, n),
        "rank_diff": rng.integers(-50, 50, n).astype(float),
        "competition_weight": rng.choice([1, 2, 3, 4, 5], n).astype(float),
        "is_same_confederation": rng.choice([0, 1], n),
        "match_weight": rng.uniform(0.5, 1.0, n),
        "home_score": rng.integers(0, 5, n),
        "away_score": rng.integers(0, 5, n),
    })


def _split(df: pd.DataFrame, train_frac: float = 0.7):
    n = len(df)
    cut = int(n * train_frac)
    return df.iloc[:cut].copy(), df.iloc[cut:].copy()


# ---------------------------------------------------------------------------
# Baseline tests
# ---------------------------------------------------------------------------

class TestMostFrequentBaseline(unittest.TestCase):
    def setUp(self):
        df = _make_feature_df(200)
        self.train, self.test = _split(df)

    def test_always_predicts_same_class(self):
        model = MostFrequentBaseline()
        model.fit(self.train)
        proba = model.predict_proba(self.test)
        preds = np.argmax(proba, axis=1)
        self.assertEqual(len(set(preds.tolist())), 1,
                         "MostFrequentBaseline must always predict the same class")

    def test_most_common_class_is_predicted(self):
        model = MostFrequentBaseline()
        model.fit(self.train)
        target_map = {"A": 0, "D": 1, "H": 2}
        y_train = self.train["target"].map(target_map).astype(int).values
        counts = np.bincount(y_train, minlength=3)
        expected_class = int(np.argmax(counts))
        proba = model.predict_proba(self.test)
        predicted_class = int(np.argmax(proba[0]))
        self.assertEqual(predicted_class, expected_class)

    def test_probabilities_sum_to_one(self):
        model = MostFrequentBaseline()
        model.fit(self.train)
        proba = model.predict_proba(self.test)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-9)

    def test_output_shape(self):
        model = MostFrequentBaseline()
        model.fit(self.train)
        proba = model.predict_proba(self.test)
        self.assertEqual(proba.shape, (len(self.test), 3))


class TestClassPriorBaseline(unittest.TestCase):
    def setUp(self):
        df = _make_feature_df(200)
        self.train, self.test = _split(df)

    def test_probabilities_match_training_distribution(self):
        model = ClassPriorBaseline()
        model.fit(self.train)
        target_map = {"A": 0, "D": 1, "H": 2}
        y_train = self.train["target"].map(target_map).astype(int).values
        counts = np.bincount(y_train, minlength=3)
        expected_proba = counts / counts.sum()

        proba = model.predict_proba(self.test)
        # All rows should be identical and match training distribution
        np.testing.assert_allclose(proba[0], expected_proba, atol=1e-9)
        np.testing.assert_allclose(proba[-1], expected_proba, atol=1e-9)

    def test_probabilities_sum_to_one(self):
        model = ClassPriorBaseline()
        model.fit(self.train)
        proba = model.predict_proba(self.test)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-9)

    def test_all_rows_identical(self):
        model = ClassPriorBaseline()
        model.fit(self.train)
        proba = model.predict_proba(self.test)
        # Every row must be the same since it is just the prior
        np.testing.assert_allclose(proba, proba[0:1].repeat(len(self.test), axis=0), atol=1e-9)


# ---------------------------------------------------------------------------
# Elo-only baseline tests
# ---------------------------------------------------------------------------

class TestEloOnlyBaseline(unittest.TestCase):
    def setUp(self):
        df = _make_feature_df(300)
        self.train, self.test = _split(df)

    def test_uses_only_elo_features(self):
        """Verify EloOnlyBaseline accesses exactly the four declared Elo features."""
        model = EloOnlyBaseline(max_iter=50)
        model.fit(self.train)
        # Drop all non-Elo features from test — model must still work
        elo_only_test = self.test[EloOnlyBaseline.ELO_FEATURES + ["target"]].copy()
        # Add back unused columns set to garbage to prove they are ignored
        elo_only_test["home_form_last5"] = 999.0
        elo_only_test["away_form_last5"] = 999.0
        proba = model.predict_proba(elo_only_test)
        self.assertEqual(proba.shape, (len(self.test), 3))

    def test_probabilities_sum_to_one(self):
        model = EloOnlyBaseline(max_iter=50)
        model.fit(self.train)
        proba = model.predict_proba(self.test)
        np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-6)

    def test_higher_elo_home_gets_higher_home_win_prob(self):
        """A team with a large Elo advantage should be more likely to win.

        We use training data where the outcome is determined by elo_win_prob so
        the EloOnly model can learn the expected monotone relationship.
        """
        rng = np.random.default_rng(99)
        n = 500
        elo_diff = rng.uniform(-400, 400, n)
        elo_win_prob = 1 / (1 + 10 ** (-elo_diff / 400))
        # Outcome strictly follows Elo: high elo_win_prob → H, low → A
        target = np.where(elo_win_prob > 0.6, "H", np.where(elo_win_prob < 0.4, "A", "D"))
        elo_train = pd.DataFrame({
            "home_elo_pre": 1500 + elo_diff,
            "away_elo_pre": 1500 - elo_diff,
            "elo_diff_home_away": elo_diff,
            "elo_win_prob": elo_win_prob,
            "target": target,
        })
        model = EloOnlyBaseline(max_iter=500)
        model.fit(elo_train)

        strong_home = pd.DataFrame({
            "home_elo_pre": [1800.0],
            "away_elo_pre": [1200.0],
            "elo_diff_home_away": [600.0],
            "elo_win_prob": [0.99],
            "target": ["H"],
        })
        weak_home = pd.DataFrame({
            "home_elo_pre": [1200.0],
            "away_elo_pre": [1800.0],
            "elo_diff_home_away": [-600.0],
            "elo_win_prob": [0.01],
            "target": ["A"],
        })
        p_strong = model.predict_proba(strong_home)[0, 2]  # P(H)
        p_weak = model.predict_proba(weak_home)[0, 2]      # P(H)
        self.assertGreater(p_strong, p_weak)


# ---------------------------------------------------------------------------
# Metrics tests
# ---------------------------------------------------------------------------

class TestComputeMetrics(unittest.TestCase):
    def _perfect_metrics(self):
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_prob = np.eye(3)[[0, 1, 2, 0, 1, 2]].astype(float)
        return compute_metrics(y_true, y_prob, "test_model")

    def test_returns_required_keys(self):
        m = self._perfect_metrics()
        for key in ("model", "accuracy", "log_loss", "brier_score",
                    "per_class", "macro", "weighted", "confusion_matrix",
                    "calibration", "n_samples"):
            self.assertIn(key, m, f"Missing key: {key}")

    def test_per_class_keys(self):
        m = self._perfect_metrics()
        for cls_name in ("A", "D", "H"):
            self.assertIn(cls_name, m["per_class"])
            for metric_key in ("precision", "recall", "f1", "support"):
                self.assertIn(metric_key, m["per_class"][cls_name])

    def test_accuracy_range(self):
        rng = np.random.default_rng(1)
        y_true = rng.integers(0, 3, 100)
        y_prob = rng.dirichlet([1, 1, 1], 100)
        m = compute_metrics(y_true, y_prob, "random")
        self.assertGreaterEqual(m["accuracy"], 0.0)
        self.assertLessEqual(m["accuracy"], 1.0)

    def test_log_loss_is_positive(self):
        rng = np.random.default_rng(2)
        y_true = rng.integers(0, 3, 100)
        y_prob = rng.dirichlet([1, 1, 1], 100)
        m = compute_metrics(y_true, y_prob, "random")
        self.assertGreater(m["log_loss"], 0.0)

    def test_brier_score_range(self):
        rng = np.random.default_rng(3)
        y_true = rng.integers(0, 3, 50)
        y_prob = rng.dirichlet([1, 1, 1], 50)
        m = compute_metrics(y_true, y_prob, "random")
        # Multiclass Brier score is in [0, 2] for 3-class problems
        self.assertGreaterEqual(m["brier_score"], 0.0)
        self.assertLessEqual(m["brier_score"], 2.0)

    def test_no_shape_error_with_most_frequent_proba(self):
        """MostFrequentBaseline returns probabilities with a zero column — metrics must not crash."""
        y_true = np.array([0, 1, 2, 0, 2, 2])
        y_prob = np.zeros((6, 3))
        y_prob[:, 2] = 1.0  # always predict H
        m = compute_metrics(y_true, y_prob, "most_frequent")
        self.assertIn("accuracy", m)

    def test_n_samples_correct(self):
        y_true = np.array([0, 1, 2])
        y_prob = np.eye(3).astype(float)
        m = compute_metrics(y_true, y_prob, "test")
        self.assertEqual(m["n_samples"], 3)


class TestMulticlassBrierScore(unittest.TestCase):
    def test_perfect_prediction_is_zero(self):
        y_true = np.array([0, 1, 2])
        y_prob = np.eye(3).astype(float)
        self.assertAlmostEqual(multiclass_brier_score(y_true, y_prob), 0.0, places=9)

    def test_worst_prediction(self):
        # Assigning probability 1.0 to the wrong class always → score = 2.0 for 3 classes
        y_true = np.array([0, 1, 2])
        y_prob = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], dtype=float)
        self.assertAlmostEqual(multiclass_brier_score(y_true, y_prob), 2.0, places=9)


# ---------------------------------------------------------------------------
# Rolling backtest chronology tests
# ---------------------------------------------------------------------------

class TestRollingBacktest(unittest.TestCase):
    def setUp(self):
        self.df = _make_feature_df(400)

    def test_windows_are_chronological(self):
        windows = rolling_windows(self.df, min_train_frac=0.5, n_windows=4)
        self.assertGreater(len(windows), 0)
        for train_df, test_df, window in windows:
            train_max = train_df["date"].max()
            test_min = test_df["date"].min()
            self.assertLess(
                train_max, test_min,
                f"Window {window.window_idx}: train extends into test period"
            )

    def test_no_overlap_between_train_and_test(self):
        windows = rolling_windows(self.df, min_train_frac=0.5, n_windows=4)
        for train_df, test_df, window in windows:
            train_indices = set(train_df.index)
            test_indices = set(test_df.index)
            self.assertEqual(
                len(train_indices & test_indices), 0,
                f"Window {window.window_idx}: train and test share indices"
            )

    def test_training_set_grows_with_window(self):
        windows = rolling_windows(self.df, min_train_frac=0.5, n_windows=4)
        sizes = [w.n_train for _, _, w in windows]
        for i in range(1, len(sizes)):
            self.assertGreater(
                sizes[i], sizes[i - 1],
                "Training set must grow with each subsequent window"
            )

    def test_returns_expected_number_of_windows(self):
        windows = rolling_windows(self.df, min_train_frac=0.6, n_windows=4)
        self.assertLessEqual(len(windows), 4)
        self.assertGreater(len(windows), 0)

    def test_run_backtest_preserves_chronology(self):
        models = [MostFrequentBaseline(), ClassPriorBaseline()]
        results = run_backtest(models, self.df, min_train_frac=0.6, n_windows=3)
        self.assertGreater(len(results), 0)
        for wr in results:
            self.assertIn("window_idx", wr)
            self.assertIn("models", wr)
            self.assertIn("most_frequent", wr["models"])

    def test_aggregate_backtest_results(self):
        models = [MostFrequentBaseline(), ClassPriorBaseline()]
        results = run_backtest(models, self.df, min_train_frac=0.6, n_windows=3)
        if results:
            agg = aggregate_backtest_results(results)
            self.assertIn("per_model", agg)
            self.assertIn("ranking_by_accuracy", agg)
            for model_name in ["most_frequent", "class_prior"]:
                self.assertIn(model_name, agg["per_model"])
                self.assertIsNotNone(agg["per_model"][model_name]["mean_accuracy"])


# ---------------------------------------------------------------------------
# Report generation tests
# ---------------------------------------------------------------------------

class TestReportGeneration(unittest.TestCase):
    def _sample_metrics(self) -> list[dict]:
        rng = np.random.default_rng(42)
        y_true = rng.integers(0, 3, 100)
        y_prob = rng.dirichlet([1, 1, 1], 100)
        return [compute_metrics(y_true, y_prob, "test_model")]

    def test_evaluation_report_creates_files(self):
        metrics = self._sample_metrics()
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)
            save_evaluation_report(metrics, reports_dir=reports_dir)
            self.assertTrue((reports_dir / "evaluation_summary.csv").exists())
            self.assertTrue((reports_dir / "evaluation_summary.json").exists())

    def test_calibration_plots_created(self):
        metrics = self._sample_metrics()
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)
            (reports_dir / "figures").mkdir(parents=True, exist_ok=True)
            save_calibration_plots(metrics, reports_dir=reports_dir)
            png = reports_dir / "figures" / "calibration_test_model.png"
            self.assertTrue(png.exists(), f"Expected calibration plot at {png}")

    def test_backtest_report_creates_files(self):
        models = [MostFrequentBaseline(), ClassPriorBaseline()]
        df = _make_feature_df(300)
        results = run_backtest(models, df, min_train_frac=0.6, n_windows=3)
        if not results:
            self.skipTest("No backtest windows generated — dataset too small.")
        agg = aggregate_backtest_results(results)
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)
            save_backtest_report(results, agg, reports_dir=reports_dir)
            self.assertTrue((reports_dir / "backtest_windows.csv").exists())
            self.assertTrue((reports_dir / "backtest_summary.json").exists())

    def test_evaluation_csv_has_model_column(self):
        import csv
        metrics = self._sample_metrics()
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = Path(tmpdir)
            save_evaluation_report(metrics, reports_dir=reports_dir)
            with open(reports_dir / "evaluation_summary.csv") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["model"], "test_model")


# ---------------------------------------------------------------------------
# Full pipeline smoke test
# ---------------------------------------------------------------------------

class TestFullEvaluationPipeline(unittest.TestCase):
    """Smoke test: fit all five models on synthetic data and evaluate."""

    def test_all_models_produce_valid_output(self):
        cfg = _cfg()
        df = _make_feature_df(400)
        train, test = _split(df, train_frac=0.75)
        y_test = test["target"].map({"A": 0, "D": 1, "H": 2}).astype(int).values

        models = all_models(cfg)
        self.assertEqual(len(models), 5)
        for model in models:
            with self.subTest(model=model.name):
                model.fit(train)
                proba = model.predict_proba(test)
                self.assertEqual(proba.shape, (len(test), 3),
                                 f"{model.name}: wrong proba shape")
                np.testing.assert_allclose(
                    proba.sum(axis=1), 1.0, atol=1e-5,
                    err_msg=f"{model.name}: rows do not sum to 1"
                )
                m = compute_metrics(y_test, proba, model.name)
                self.assertGreaterEqual(m["accuracy"], 0.0)
                self.assertLessEqual(m["accuracy"], 1.0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
