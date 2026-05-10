"""Tests for ensemble confidence interval extraction (issue #20)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.ensemble_model import EnsembleModel


def _make_dummy_ensemble() -> EnsembleModel:
    from unittest.mock import MagicMock

    def _make_pipeline(probs: list[float]):
        pipeline = MagicMock()
        pipeline.predict_proba.return_value = np.array([probs])
        clf = MagicMock()
        clf.classes_ = np.array([0, 1, 2])
        pipeline.named_steps = {"classifier": clf}
        return pipeline

    draw_sub = MagicMock()
    draw_sub.predict_proba.return_value = np.array([[0.3, 0.3]])

    return EnsembleModel(
        xgb_pipeline=_make_pipeline([0.2, 0.3, 0.5]),
        logreg_pipeline=_make_pipeline([0.3, 0.3, 0.4]),
        mlp_pipeline=_make_pipeline([0.25, 0.35, 0.40]),
        draw_submodel=draw_sub,
        per_class_weights=np.array([[1/3, 1/3, 1/3], [1/3, 1/3, 1/3], [1/3, 1/3, 1/3]]),
        draw_blend_weight=0.3,
        feature_cols=["elo_diff_home_away"],
    )


def test_extract_per_model_probas_returns_correct_shape():
    from src.api.services import _extract_ensemble_ci
    ensemble = _make_dummy_ensemble()
    X = pd.DataFrame([{"elo_diff_home_away": 50.0}])
    ci = _extract_ensemble_ci(ensemble, X)
    assert ci is not None
    assert "home_win" in ci and "draw" in ci and "away_win" in ci
    lo, hi = ci["home_win"]
    assert 0.0 <= lo <= hi <= 1.0


def test_ci_bounds_bracket_blended_value():
    from src.api.services import _extract_ensemble_ci
    ensemble = _make_dummy_ensemble()
    X = pd.DataFrame([{"elo_diff_home_away": 50.0}])
    ci = _extract_ensemble_ci(ensemble, X)
    blended = ensemble.predict_proba(X)[0]  # [A, D, H]
    assert ci["home_win"][0] <= blended[2] <= ci["home_win"][1]
    assert ci["draw"][0] <= blended[1] <= ci["draw"][1]
    assert ci["away_win"][0] <= blended[0] <= ci["away_win"][1]


def test_non_ensemble_returns_none():
    from src.api.services import _extract_ensemble_ci
    assert _extract_ensemble_ci(object(), pd.DataFrame()) is None
