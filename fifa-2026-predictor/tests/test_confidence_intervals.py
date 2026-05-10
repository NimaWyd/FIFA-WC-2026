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


def test_ci_values_are_valid_probabilities():
    """CI bounds should be valid probabilities with lo <= hi for each outcome."""
    from src.api.services import _extract_ensemble_ci
    ensemble = _make_dummy_ensemble()
    X = pd.DataFrame([{"elo_diff_home_away": 50.0}])
    ci = _extract_ensemble_ci(ensemble, X)
    assert ci is not None
    for outcome in ("home_win", "draw", "away_win"):
        lo, hi = ci[outcome]
        assert 0.0 <= lo <= hi <= 1.0, f"{outcome}: [{lo}, {hi}] is invalid"


def test_non_ensemble_returns_none():
    from src.api.services import _extract_ensemble_ci
    assert _extract_ensemble_ci(object(), pd.DataFrame()) is None


def test_ci_is_narrow_when_dominant_model_has_high_weight():
    """With XGB weight=0.9, CI should be narrow even if LogReg/MLP give extreme predictions."""
    from unittest.mock import MagicMock
    from src.api.services import _extract_ensemble_ci

    def _make_pipeline(probs):
        p = MagicMock()
        p.predict_proba.return_value = np.array([probs])
        clf = MagicMock()
        clf.classes_ = np.array([0, 1, 2])
        p.named_steps = {"classifier": clf}
        return p

    draw_sub = MagicMock()
    draw_sub.predict_proba.return_value = np.array([[0.3, 0.3]])

    # Scenario: XGB says 50/25/25, LogReg/MLP say away team wins 99%+
    ensemble = EnsembleModel(
        xgb_pipeline=_make_pipeline([0.50, 0.25, 0.25]),
        logreg_pipeline=_make_pipeline([0.99, 0.005, 0.005]),
        mlp_pipeline=_make_pipeline([0.98, 0.01, 0.01]),
        draw_submodel=draw_sub,
        per_class_weights=np.array([[0.9, 0.9, 0.9],
                                     [0.05, 0.05, 0.05],
                                     [0.05, 0.05, 0.05]]),
        draw_blend_weight=0.0,
        feature_cols=["elo_diff_home_away"],
    )
    X = pd.DataFrame([{"elo_diff_home_away": 50.0}])
    ci = _extract_ensemble_ci(ensemble, X)
    assert ci is not None

    # Old raw min/max would give away_win CI width = 0.99 - 0.50 = 0.49
    # New weighted-std should give width < 0.30
    lo, hi = ci["away_win"]
    assert hi - lo < 0.30, f"CI width {hi - lo:.3f} too wide; expected < 0.30 with XGB weight=0.9"
    assert 0.0 <= lo <= hi <= 1.0
