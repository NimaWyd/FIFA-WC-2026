"""Tests for draw submodel and ensemble (issues #46, #43)."""
from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Shared fixture (reuses pattern from test_phase2.py)
# ---------------------------------------------------------------------------

def _make_feature_df(n: int = 300, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2010-01-01", periods=n, freq="3D")
    base_elo = 1500 + rng.normal(0, 100, n)
    elo_diff = rng.normal(0, 50, n)
    rest_days_home = rng.integers(1, 30, n).astype(float)
    rest_days_away = rng.integers(1, 30, n).astype(float)
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


def _split(df: pd.DataFrame, train_frac: float = 0.6, val_frac: float = 0.2):
    n = len(df)
    t = int(n * train_frac)
    v = int(n * (train_frac + val_frac))
    return df.iloc[:t].copy(), df.iloc[t:v].copy(), df.iloc[v:].copy()


# ---------------------------------------------------------------------------
# Task 1: Draw submodel
# ---------------------------------------------------------------------------

def test_draw_submodel_trains():
    """Draw submodel fits and produces p_draw in [0, 1] for each row."""
    from src.models.common import build_preprocessor, to_xy
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.utils.class_weight import compute_sample_weight

    df = _make_feature_df(300)
    train_df, val_df, _ = _split(df)

    preprocessor, feature_cols = build_preprocessor(df)
    X_train, _ = to_xy(train_df, feature_cols)
    y_train_binary = (train_df["target"] == "D").astype(int).values

    weights = compute_sample_weight("balanced", y_train_binary)
    preprocessor.fit(X_train)
    X_train_t = preprocessor.transform(X_train)
    clf = LogisticRegression(max_iter=200, random_state=42)
    clf.fit(X_train_t, y_train_binary, sample_weight=weights)

    model = Pipeline([("preprocessor", preprocessor), ("classifier", clf)])
    X_val, _ = to_xy(val_df, feature_cols)
    p_draw = model.predict_proba(X_val)[:, 1]

    assert p_draw.shape == (len(val_df),)
    assert (p_draw >= 0).all() and (p_draw <= 1).all()


# ---------------------------------------------------------------------------
# Task 2: EnsembleModel
# ---------------------------------------------------------------------------

def _make_fake_ensemble():
    """Build a minimal EnsembleModel with trained sub-models for testing."""
    from sklearn.linear_model import LogisticRegression as LR
    from sklearn.pipeline import Pipeline
    from src.models.ensemble_model import EnsembleModel
    from src.models.common import build_preprocessor, to_xy
    from src.evaluation.baselines import MLPModel

    df = _make_feature_df(300)
    train_df, val_df, _ = _split(df)

    preprocessor, feature_cols = build_preprocessor(df)
    X_train, y_train = to_xy(train_df, feature_cols)
    preprocessor.fit(X_train)
    X_train_t = preprocessor.transform(X_train)

    xgb_clf = LR(max_iter=200, random_state=0)
    xgb_clf.fit(X_train_t, y_train)
    xgb_pipeline = Pipeline([("preprocessor", copy.deepcopy(preprocessor)), ("classifier", xgb_clf)])

    logreg_clf = LR(max_iter=200, random_state=1)
    logreg_clf.fit(X_train_t, y_train)
    logreg_pipeline = Pipeline([("preprocessor", copy.deepcopy(preprocessor)), ("classifier", logreg_clf)])

    mlp = MLPModel()
    mlp.fit(train_df)

    y_draw = (train_df["target"] == "D").astype(int).values
    draw_clf = LR(max_iter=200, random_state=2)
    draw_clf.fit(X_train_t, y_draw)
    draw_submodel = Pipeline([("preprocessor", copy.deepcopy(preprocessor)), ("classifier", draw_clf)])

    per_class_weights = np.ones((3, 3)) / 3.0
    draw_blend_weight = 0.3

    return EnsembleModel(
        xgb_pipeline=xgb_pipeline,
        logreg_pipeline=logreg_pipeline,
        mlp_pipeline=mlp,
        draw_submodel=draw_submodel,
        per_class_weights=per_class_weights,
        draw_blend_weight=draw_blend_weight,
        feature_cols=feature_cols,
    ), val_df


def test_ensemble_predict_proba_shape():
    """EnsembleModel.predict_proba returns (n, 3) array."""
    ensemble, val_df = _make_fake_ensemble()
    proba = ensemble.predict_proba(val_df)
    assert proba.shape == (len(val_df), 3)


def test_ensemble_proba_sums_to_one():
    """All row probabilities sum to 1.0 within float tolerance."""
    ensemble, val_df = _make_fake_ensemble()
    proba = ensemble.predict_proba(val_df)
    np.testing.assert_allclose(proba.sum(axis=1), np.ones(len(val_df)), atol=1e-6)


def test_ensemble_blend_weight_bounds():
    """draw_blend_weight is stored and is in [0, 1]."""
    ensemble, _ = _make_fake_ensemble()
    assert 0.0 <= ensemble.draw_blend_weight <= 1.0


def test_ensemble_save_load_roundtrip():
    """Save and load EnsembleModel produces identical predict_proba output."""
    from src.models.ensemble_model import EnsembleModel

    ensemble, val_df = _make_fake_ensemble()
    proba_before = ensemble.predict_proba(val_df)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ensemble.joblib"
        ensemble.save(path)
        loaded = EnsembleModel.load(path)

    proba_after = loaded.predict_proba(val_df)
    np.testing.assert_allclose(proba_before, proba_after, atol=1e-9)


def test_ensemble_named_steps_compatibility():
    """EnsembleModel exposes named_steps['classifier'].classes_ for services.py compatibility."""
    ensemble, _ = _make_fake_ensemble()
    clf = ensemble.named_steps["classifier"]
    assert hasattr(clf, "classes_")
    assert list(clf.classes_) == [0, 1, 2]


# ---------------------------------------------------------------------------
# Task 4: services.py loads ensemble first
# ---------------------------------------------------------------------------

def test_services_loads_ensemble_first(tmp_path, monkeypatch):
    """_get_model() prefers ensemble.joblib when it exists."""
    import joblib
    from src.api import services as svc

    # Reset module-level singletons
    svc._model = None
    svc._model_artifact_name = "none"

    (tmp_path / "ensemble.joblib").write_bytes(b"fake")

    fake_model = object()
    monkeypatch.setattr(svc, "_get_cfg", lambda: {"paths": {"trained_model_dir": str(tmp_path)}})
    monkeypatch.setattr(joblib, "load", lambda p: fake_model)

    model = svc._get_model()

    assert model is fake_model
    assert svc._model_artifact_name == "ensemble.joblib"

    # Cleanup singletons
    svc._model = None
    svc._model_artifact_name = "none"
