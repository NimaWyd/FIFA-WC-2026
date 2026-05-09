"""Tests for src/evaluation/feature_importance.py (issue #82)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.models.common import IsotonicCalibrationWrapper


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _build_tiny_pipeline(tmp_path: Path) -> tuple[Path, Path]:
    """Build a minimal 3-feature XGBoost pipeline and return (model_path, csv_path)."""
    rng = np.random.default_rng(0)
    n = 300
    df = pd.DataFrame({
        "date": pd.date_range("2000-01-01", periods=n, freq="7D"),
        "competition": rng.choice(["Friendly", "World Cup"], n),
        "home_confederation": rng.choice(["UEFA", "CONMEBOL"], n),
        "away_confederation": rng.choice(["UEFA", "CONMEBOL"], n),
        "tournament_stage": rng.choice(["Group", "Final"], n),
        "elo_diff": rng.normal(0, 200, n),
        "form": rng.uniform(0, 1, n),
        "rank_diff": rng.integers(-100, 100, n).astype(float),
        "target": rng.choice(["H", "D", "A"], n),
    })

    categorical = ["competition", "home_confederation", "away_confederation", "tournament_stage"]
    numeric = ["elo_diff", "form", "rank_diff"]
    feature_cols = categorical + numeric

    preprocessor = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", StandardScaler(), numeric),
    ])

    from src.models.common import TARGET_MAP
    X = df[feature_cols]
    y = df["target"].map(TARGET_MAP).astype(int).values

    preprocessor.fit(X)
    X_t = preprocessor.transform(X)

    clf = XGBClassifier(n_estimators=10, max_depth=3, objective="multi:softprob",
                        num_class=3, random_state=0, eval_metric="mlogloss")
    clf.fit(X_t, y)

    cal = IsotonicCalibrationWrapper(clf)
    cal.fit(X_t, y)

    model = Pipeline([("preprocessor", preprocessor), ("classifier", cal)])

    model_path = tmp_path / "tiny_xgb.joblib"
    joblib.dump(model, model_path)

    csv_path = tmp_path / "features.csv"
    df["neutral"] = 0
    df["match_weight"] = 1.0
    df.to_csv(csv_path, index=False)

    return model_path, csv_path, feature_cols


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeShapImportance(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.model_path, self.csv_path, self.feature_cols = _build_tiny_pipeline(self.tmp)

    def _run(self, **kwargs):
        from src.evaluation.feature_importance import compute_shap_importance
        return compute_shap_importance(self.model_path, self.csv_path, **kwargs)

    def test_output_has_required_keys(self):
        result = self._run()
        for key in ("top_features", "low_importance_candidates", "n_features_analyzed", "n_samples"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_top_features_are_dicts_with_feature_and_shap(self):
        result = self._run()
        for entry in result["top_features"]:
            self.assertIn("feature", entry)
            self.assertIn("mean_abs_shap", entry)

    def test_top_features_sorted_descending(self):
        result = self._run()
        shap_vals = [e["mean_abs_shap"] for e in result["top_features"]]
        self.assertEqual(shap_vals, sorted(shap_vals, reverse=True))

    def test_top_n_caps_output(self):
        result = self._run(top_n=3)
        self.assertLessEqual(len(result["top_features"]), 3)

    def test_mean_abs_shap_non_negative(self):
        result = self._run()
        for entry in result["top_features"]:
            self.assertGreaterEqual(entry["mean_abs_shap"], 0.0)

    def test_low_importance_candidates_below_threshold(self):
        result = self._run(low_importance_threshold=999.0)
        # With a huge threshold everything should be a candidate
        all_features = {e["feature"] for e in result["top_features"]}
        all_features |= set(result["low_importance_candidates"])
        self.assertGreater(len(result["low_importance_candidates"]), 0)

    def test_n_features_analyzed_positive(self):
        result = self._run()
        self.assertGreater(result["n_features_analyzed"], 0)

    def test_n_samples_positive(self):
        result = self._run()
        self.assertGreater(result["n_samples"], 0)

    def test_output_json_written_when_path_provided(self):
        out_path = self.tmp / "importance.json"
        self._run(output_json=out_path)
        self.assertTrue(out_path.exists())
        data = json.loads(out_path.read_text())
        self.assertIn("top_features", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
