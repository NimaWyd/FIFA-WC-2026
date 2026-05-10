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

    # For away_win, both LogReg (0.05) and MLP (0.05) are below the 0.15 per-class threshold.
    # Only XGB (0.9) is retained → CI collapses to a point (std=0), lo≈hi≈XGB away_win prob.
    lo, hi = ci["away_win"]
    assert hi - lo < 0.05, f"CI width {hi - lo:.3f} should be ~0 when only XGB is retained"
    assert 0.0 <= lo <= hi <= 1.0


def test_ci_filters_per_class_not_globally():
    """Models are filtered per outcome class: a model below threshold for class A is still
    included for class H if its H-class weight meets the threshold."""
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

    # MLP has low weight for A/D (0.05) but meaningful weight for H (0.30).
    # It gives 99% away_win — should NOT affect away_win CI (A class, weight=0.05).
    ensemble = EnsembleModel(
        xgb_pipeline=_make_pipeline([0.50, 0.25, 0.25]),
        mlp_pipeline=_make_pipeline([0.99, 0.005, 0.005]),   # extreme for A, low H weight
        logreg_pipeline=_make_pipeline([0.40, 0.30, 0.30]),
        draw_submodel=draw_sub,
        per_class_weights=np.array([[0.65, 0.65, 0.55],      # XGB
                                     [0.30, 0.30, 0.15],      # LogReg: above threshold for all
                                     [0.05, 0.05, 0.30]]),    # MLP: below for A/D, above for H
        draw_blend_weight=0.0,
        feature_cols=["elo_diff_home_away"],
    )
    X = pd.DataFrame([{"elo_diff_home_away": 0.0}])
    ci = _extract_ensemble_ci(ensemble, X)
    assert ci is not None

    # MLP excluded from away_win (A class, weight=0.05 < 0.15) — 99% outlier has no effect.
    lo_a, hi_a = ci["away_win"]
    assert hi_a <= 0.70, f"MLP outlier should be excluded from away_win; hi={hi_a:.3f}"
    assert 0.0 <= lo_a <= hi_a <= 1.0
