# Draw Submodel + Ensemble Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a binary draw prediction submodel (#46) and an XGBoost+LogReg+MLP ensemble (#43) that becomes the default model served by the API.

**Architecture:** Option B — draw submodel is trained independently as a binary LogReg classifier, then blended post-hoc into the ensemble's draw probability at inference time. The ensemble optimizes per-class blend weights on the val set via SLSQP. `EnsembleModel` exposes the same `predict_proba` + `named_steps` interface as existing sklearn Pipelines so `services.py` needs only a one-line change.

**Tech Stack:** Python, scikit-learn, XGBoost, scipy.optimize, joblib, pytest

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `src/models/train_draw_submodel.py` | Create | Trains binary draw classifier, saves `draw_submodel.joblib` |
| `src/models/ensemble_model.py` | Create | `EnsembleModel` class — blends 3 base models + draw submodel |
| `src/models/train_ensemble.py` | Create | Loads base models, optimizes weights on val set, saves `ensemble.joblib` |
| `src/api/services.py` | Modify (1 line) | Add `ensemble.joblib` as first preference in `_get_model()` |
| `tests/test_ensemble.py` | Create | 7 tests covering all new components |

---

## Task 1: Draw Submodel Training Script

**Files:**
- Create: `fifa-2026-predictor/src/models/train_draw_submodel.py`
- Test: `fifa-2026-predictor/tests/test_ensemble.py`

- [ ] **Step 1: Write the failing test**

Create `fifa-2026-predictor/tests/test_ensemble.py`:

```python
"""Tests for draw submodel and ensemble (issues #46, #43)."""
from __future__ import annotations

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

    df = _make_feature_df(300)
    train_df, val_df, _ = _split(df)

    preprocessor, feature_cols = build_preprocessor(df)
    X_train, _ = to_xy(train_df, feature_cols)
    y_train_binary = (train_df["target"] == "D").astype(int).values

    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.utils.class_weight import compute_sample_weight

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
```

- [ ] **Step 2: Run test to confirm it passes (it tests logic, not the module)**

```bash
cd fifa-2026-predictor
pytest tests/test_ensemble.py::test_draw_submodel_trains -v
```

Expected: PASS (this test validates the logic directly, not the module yet)

- [ ] **Step 3: Create `src/models/train_draw_submodel.py`**

```python
"""Train binary draw/not-draw classifier for P(Draw)."""
from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight

from src.models.common import (
    build_preprocessor,
    ensure_artifact_dir,
    load_feature_data,
    make_chronological_split,
    to_xy,
)
from src.utils import load_config


def train_draw_submodel(df: pd.DataFrame, cfg: dict) -> Pipeline:
    """Fit a binary draw/not-draw LogReg pipeline on training split of df."""
    train_df, val_df, test_df = make_chronological_split(
        df,
        val_size=float(cfg["model"]["val_size"]),
        test_size=float(cfg["model"]["test_size"]),
    )
    preprocessor, feature_cols = build_preprocessor(df)
    X_train, _ = to_xy(train_df, feature_cols)
    y_train = (train_df["target"] == "D").astype(int).values

    weights = compute_sample_weight("balanced", y_train)
    preprocessor.fit(X_train)
    X_train_t = preprocessor.transform(X_train)

    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_train_t, y_train, sample_weight=weights)

    model = Pipeline([("preprocessor", preprocessor), ("classifier", clf)])
    print(f"Draw submodel — train: {len(train_df)} | val: {len(val_df)} | test: {len(test_df)}")
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train binary draw submodel.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    args = parser.parse_args()

    cfg = load_config()
    df = load_feature_data(args.features_csv)

    min_train_year = int(cfg["model"].get("min_train_year", 0))
    if min_train_year > 0:
        n_before = len(df)
        df = df[pd.to_datetime(df["date"]).dt.year >= min_train_year].reset_index(drop=True)
        print(f"Filtered to {min_train_year}+: {n_before} -> {len(df)} rows")

    model = train_draw_submodel(df, cfg)

    artifact_dir = ensure_artifact_dir(cfg["paths"]["trained_model_dir"])
    path = artifact_dir / "draw_submodel.joblib"
    joblib.dump(model, path)
    print(f"Saved draw submodel to {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Commit**

```bash
git add src/models/train_draw_submodel.py tests/test_ensemble.py
git commit -m "feat: add draw submodel training script (issue #46)"
```

---

## Task 2: EnsembleModel Class

**Files:**
- Create: `fifa-2026-predictor/src/models/ensemble_model.py`
- Modify: `fifa-2026-predictor/tests/test_ensemble.py`

- [ ] **Step 1: Add failing tests for EnsembleModel to `tests/test_ensemble.py`**

Append these tests to the file:

```python
# ---------------------------------------------------------------------------
# Task 2: EnsembleModel
# ---------------------------------------------------------------------------

def _make_fake_ensemble():
    """Build a minimal EnsembleModel with trained sub-models for testing."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from src.models.ensemble_model import EnsembleModel
    from src.models.common import build_preprocessor, to_xy
    from src.evaluation.baselines import MLPModel

    df = _make_feature_df(300)
    train_df, val_df, _ = _split(df)

    # Build and fit a shared preprocessor
    preprocessor, feature_cols = build_preprocessor(df)
    X_train, y_train = to_xy(train_df, feature_cols)
    preprocessor.fit(X_train)
    X_train_t = preprocessor.transform(X_train)

    # XGB-like pipeline (use LogReg as stand-in to avoid XGBoost dependency in unit tests)
    from sklearn.linear_model import LogisticRegression as LR
    import copy
    xgb_clf = LR(max_iter=200, random_state=0)
    xgb_clf.fit(X_train_t, y_train)
    xgb_pipeline = Pipeline([("preprocessor", copy.deepcopy(preprocessor)), ("classifier", xgb_clf)])

    logreg_clf = LR(max_iter=200, random_state=1)
    logreg_clf.fit(X_train_t, y_train)
    logreg_pipeline = Pipeline([("preprocessor", copy.deepcopy(preprocessor)), ("classifier", logreg_clf)])

    mlp = MLPModel()
    mlp.fit(train_df)

    # Draw submodel (binary)
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
    """All row probabilities sum to 1.0 (within float tolerance)."""
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd fifa-2026-predictor
pytest tests/test_ensemble.py::test_ensemble_predict_proba_shape -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.models.ensemble_model'`

- [ ] **Step 3: Create `src/models/ensemble_model.py`**

```python
"""EnsembleModel: blends XGBoost + LogReg + MLP with a draw submodel adjustment."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


class EnsembleModel:
    """Blends 3 base classifiers with per-class weights + post-hoc draw submodel adjustment.

    Exposes the same predict_proba interface and named_steps property as a
    sklearn Pipeline so services.py requires no changes beyond preference order.
    """

    def __init__(
        self,
        xgb_pipeline: Any,
        logreg_pipeline: Any,
        mlp_pipeline: Any,
        draw_submodel: Any,
        per_class_weights: np.ndarray,
        draw_blend_weight: float,
        feature_cols: list[str],
    ) -> None:
        self.xgb_pipeline = xgb_pipeline
        self.logreg_pipeline = logreg_pipeline
        self.mlp_pipeline = mlp_pipeline
        self.draw_submodel = draw_submodel
        self.per_class_weights = np.asarray(per_class_weights)  # shape (3, 3): [model, class]
        self.draw_blend_weight = float(draw_blend_weight)
        self.feature_cols = feature_cols
        self.classes_ = np.array([0, 1, 2])

    @property
    def named_steps(self) -> dict[str, Any]:
        """Compatibility shim: services.py does model.named_steps['classifier'].classes_."""
        return {"classifier": self}

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return (n, 3) probability array ordered [A=0, D=1, H=2]."""
        p_xgb = self._get_base_proba(self.xgb_pipeline, X)
        p_logreg = self._get_base_proba(self.logreg_pipeline, X)
        p_mlp = self._get_base_proba(self.mlp_pipeline, X)

        # Weighted blend per class; per_class_weights[model_idx, class_idx]
        blended = np.zeros((len(X), 3))
        for m_idx, p in enumerate([p_xgb, p_logreg, p_mlp]):
            for c_idx in range(3):
                blended[:, c_idx] += self.per_class_weights[m_idx, c_idx] * p[:, c_idx]

        # Draw submodel post-hoc adjustment (D=class index 1)
        p_draw_sub = self.draw_submodel.predict_proba(X)[:, 1]
        w = self.draw_blend_weight
        p_draw_final = w * p_draw_sub + (1.0 - w) * blended[:, 1]

        # Redistribute remaining probability between A and H in their original ratio
        ha_sum = blended[:, 0] + blended[:, 2]
        safe_ha = np.where(ha_sum < 1e-9, 1.0, ha_sum)
        remaining = 1.0 - p_draw_final
        p_A = (blended[:, 0] / safe_ha) * remaining
        p_H = (blended[:, 2] / safe_ha) * remaining

        result = np.column_stack([p_A, p_draw_final, p_H])
        # Renormalize to guard against floating-point drift
        row_sums = result.sum(axis=1, keepdims=True)
        return result / np.maximum(row_sums, 1e-9)

    def _get_base_proba(self, model: Any, X: pd.DataFrame) -> np.ndarray:
        """Get (n, 3) probabilities ordered [A=0, D=1, H=2] from any model type."""
        from src.evaluation.baselines import MLPModel
        if isinstance(model, MLPModel):
            # MLPModel.predict_proba already reorders to [A=0, D=1, H=2]
            return model.predict_proba(X)
        # sklearn Pipeline: reorder by classes_ to guarantee [A=0, D=1, H=2]
        raw = model.predict_proba(X)
        classes = np.asarray(model.named_steps["classifier"].classes_).astype(int).ravel()
        order = np.argsort(classes)
        if np.array_equal(order, np.arange(len(classes))):
            return raw
        return raw[:, order]

    def save(self, path: Path) -> None:
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> "EnsembleModel":
        return joblib.load(path)
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd fifa-2026-predictor
pytest tests/test_ensemble.py::test_ensemble_predict_proba_shape tests/test_ensemble.py::test_ensemble_proba_sums_to_one tests/test_ensemble.py::test_ensemble_blend_weight_bounds tests/test_ensemble.py::test_ensemble_save_load_roundtrip tests/test_ensemble.py::test_ensemble_named_steps_compatibility -v
```

Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/models/ensemble_model.py tests/test_ensemble.py
git commit -m "feat: add EnsembleModel class with draw blend and named_steps shim (issues #43, #46)"
```

---

## Task 3: Ensemble Training Script

**Files:**
- Create: `fifa-2026-predictor/src/models/train_ensemble.py`

- [ ] **Step 1: Create `src/models/train_ensemble.py`**

```python
"""Train ensemble of XGBoost + LogReg + MLP with draw submodel blend."""
from __future__ import annotations

import argparse

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.evaluation.baselines import MLPModel
from src.models.common import (
    TARGET_MAP,
    build_preprocessor,
    ensure_artifact_dir,
    load_feature_data,
    make_chronological_split,
    to_xy,
)
from src.models.ensemble_model import EnsembleModel
from src.utils import load_config


def _pipeline_proba_ordered(pipeline, df: pd.DataFrame, feature_cols: list[str]) -> np.ndarray:
    """Get (n, 3) probabilities ordered [A=0, D=1, H=2] from a sklearn Pipeline."""
    X, _ = to_xy(df, feature_cols)
    raw = pipeline.predict_proba(X)
    classes = np.asarray(pipeline.named_steps["classifier"].classes_).astype(int).ravel()
    order = np.argsort(classes)
    if np.array_equal(order, np.arange(len(classes))):
        return raw
    return raw[:, order]


def _optimize_per_class_weights(
    p_xgb: np.ndarray,
    p_logreg: np.ndarray,
    p_mlp: np.ndarray,
    y_val: np.ndarray,
) -> np.ndarray:
    """Return per_class_weights (3, 3) minimizing val log-loss via SLSQP.

    per_class_weights[model_idx, class_idx]: weight of model_idx on class_idx.
    For each class, weights across models sum to 1 and are >= 0.
    """
    n_models, n_classes = 3, 3
    x0 = np.ones(n_models * n_classes) / n_models

    def objective(w_flat: np.ndarray) -> float:
        w = w_flat.reshape(n_models, n_classes)
        blended = np.zeros((len(y_val), n_classes))
        for m_idx, p in enumerate([p_xgb, p_logreg, p_mlp]):
            for c_idx in range(n_classes):
                blended[:, c_idx] += w[m_idx, c_idx] * p[:, c_idx]
        row_sums = blended.sum(axis=1, keepdims=True)
        blended = blended / np.maximum(row_sums, 1e-9)
        blended = np.clip(blended, 1e-9, 1.0)
        return float(-np.mean(np.log(blended[np.arange(len(y_val)), y_val])))

    constraints = [
        {"type": "eq", "fun": lambda w, c=c: w.reshape(n_models, n_classes)[:, c].sum() - 1.0}
        for c in range(n_classes)
    ]
    bounds = [(0.0, 1.0)] * (n_models * n_classes)
    result = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    return result.x.reshape(n_models, n_classes)


def _optimize_draw_blend_weight(
    p_draw_sub: np.ndarray,
    p_draw_ensemble: np.ndarray,
    y_val: np.ndarray,
) -> float:
    """Return scalar w minimizing binary cross-entropy on draw labels."""
    y_draw = (y_val == TARGET_MAP["D"]).astype(int)

    def objective(w: np.ndarray) -> float:
        p = np.clip(w[0] * p_draw_sub + (1.0 - w[0]) * p_draw_ensemble, 1e-9, 1.0 - 1e-9)
        return float(-np.mean(y_draw * np.log(p) + (1 - y_draw) * np.log(1 - p)))

    result = minimize(objective, [0.5], method="SLSQP", bounds=[(0.0, 1.0)])
    return float(result.x[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ensemble model.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    args = parser.parse_args()

    cfg = load_config()
    df = load_feature_data(args.features_csv)

    min_train_year = int(cfg["model"].get("min_train_year", 0))
    if min_train_year > 0:
        n_before = len(df)
        df = df[pd.to_datetime(df["date"]).dt.year >= min_train_year].reset_index(drop=True)
        print(f"Filtered to {min_train_year}+: {n_before} -> {len(df)} rows")

    train_df, val_df, test_df = make_chronological_split(
        df,
        val_size=float(cfg["model"]["val_size"]),
        test_size=float(cfg["model"]["test_size"]),
    )
    print(f"Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")

    _, feature_cols = build_preprocessor(df)

    artifact_dir = ensure_artifact_dir(cfg["paths"]["trained_model_dir"])

    print("Loading xgb.joblib and logreg.joblib...")
    xgb_pipeline = joblib.load(artifact_dir / "xgb.joblib")
    logreg_pipeline = joblib.load(artifact_dir / "logreg.joblib")

    print("Training MLP on train split...")
    mlp = MLPModel(min_train_year=min_train_year)
    mlp.fit(train_df)

    print("Loading draw submodel...")
    draw_submodel = joblib.load(artifact_dir / "draw_submodel.joblib")

    # Val-set probabilities from all 3 base models
    print("Getting val-set predictions...")
    p_xgb_val = _pipeline_proba_ordered(xgb_pipeline, val_df, feature_cols)
    p_logreg_val = _pipeline_proba_ordered(logreg_pipeline, val_df, feature_cols)
    p_mlp_val = mlp.predict_proba(val_df)

    y_val = val_df["target"].map(TARGET_MAP).astype(int).values

    # Optimize per-class blend weights
    print("Optimizing per-class blend weights...")
    per_class_weights = _optimize_per_class_weights(p_xgb_val, p_logreg_val, p_mlp_val, y_val)
    print(f"Per-class weights (rows=models, cols=A/D/H):\n{np.round(per_class_weights, 3)}")

    # Blended draw probability on val set
    blended_draw_val = np.zeros(len(val_df))
    for m_idx, p in enumerate([p_xgb_val, p_logreg_val, p_mlp_val]):
        blended_draw_val += per_class_weights[m_idx, 1] * p[:, 1]  # D=class index 1

    # Val-set draw submodel predictions
    X_val_raw, _ = to_xy(val_df, feature_cols)
    p_draw_sub_val = draw_submodel.predict_proba(X_val_raw)[:, 1]

    # Optimize draw blend weight
    print("Optimizing draw blend weight...")
    draw_blend_weight = _optimize_draw_blend_weight(p_draw_sub_val, blended_draw_val, y_val)
    print(f"Draw blend weight: {draw_blend_weight:.4f}")

    ensemble = EnsembleModel(
        xgb_pipeline=xgb_pipeline,
        logreg_pipeline=logreg_pipeline,
        mlp_pipeline=mlp,
        draw_submodel=draw_submodel,
        per_class_weights=per_class_weights,
        draw_blend_weight=draw_blend_weight,
        feature_cols=feature_cols,
    )

    path = artifact_dir / "ensemble.joblib"
    ensemble.save(path)
    print(f"Saved ensemble to {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
cd fifa-2026-predictor
python -c "from src.models.train_ensemble import main; print('import ok')"
```

Expected: `import ok`

- [ ] **Step 3: Commit**

```bash
git add src/models/train_ensemble.py
git commit -m "feat: add ensemble training script with per-class weight optimization (issue #43)"
```

---

## Task 4: Wire Ensemble into services.py + Test

**Files:**
- Modify: `fifa-2026-predictor/src/api/services.py` (line ~60)
- Modify: `fifa-2026-predictor/tests/test_ensemble.py`

- [ ] **Step 1: Add failing test for services preference order**

Append to `tests/test_ensemble.py`:

```python
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

    # Create a fake ensemble.joblib in tmp_path
    (tmp_path / "ensemble.joblib").write_bytes(b"fake")

    fake_model = object()
    monkeypatch.setattr(svc, "_get_cfg", lambda: {"paths": {"trained_model_dir": str(tmp_path)}})
    monkeypatch.setattr(joblib, "load", lambda p: fake_model)

    model = svc._get_model()

    assert model is fake_model
    assert svc._model_artifact_name == "ensemble.joblib"

    # Cleanup singletons so other tests are not affected
    svc._model = None
    svc._model_artifact_name = "none"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd fifa-2026-predictor
pytest tests/test_ensemble.py::test_services_loads_ensemble_first -v
```

Expected: FAIL — `ensemble.joblib` not in preference list yet, `_model_artifact_name` will be `"none"` since no xgb/logreg in tmp_path.

- [ ] **Step 3: Edit `src/api/services.py` — change the preference order (one line)**

Find line ~60 in `src/api/services.py`:
```python
    for name in ("xgb.joblib", "logreg.joblib"):
```

Change to:
```python
    for name in ("ensemble.joblib", "xgb.joblib", "logreg.joblib"):
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
cd fifa-2026-predictor
pytest tests/test_ensemble.py::test_services_loads_ensemble_first -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/services.py tests/test_ensemble.py
git commit -m "feat: serve ensemble as default model in API (issues #43, #46)"
```

---

## Task 5: Full Test Suite + Train Artifacts

**Files:** None (verification only)

- [ ] **Step 1: Run the full test suite to confirm no regressions**

```bash
cd fifa-2026-predictor
pytest tests/ -v
```

Expected: All existing 327 tests PASS + 7 new tests PASS = 334 total

- [ ] **Step 2: Train the draw submodel artifact**

```bash
cd fifa-2026-predictor
python -m src.models.train_draw_submodel
```

Expected output ends with: `Saved draw submodel to .../draw_submodel.joblib`

- [ ] **Step 3: Train the ensemble artifact**

```bash
cd fifa-2026-predictor
python -m src.models.train_ensemble
```

Expected output ends with: `Saved ensemble to .../ensemble.joblib`

- [ ] **Step 4: Smoke-test the API prediction path**

```bash
cd fifa-2026-predictor
python -m src.app.predict_match --home-team Brazil --away-team France --match-date 2026-06-15 --model-path src/models/artifacts/ensemble.joblib
```

Expected: JSON with `probabilities.home_win + probabilities.draw + probabilities.away_win ≈ 1.0` and values all in [0, 1].

- [ ] **Step 5: Commit artifacts**

```bash
git add src/models/artifacts/draw_submodel.joblib src/models/artifacts/ensemble.joblib
git commit -m "chore: add trained draw_submodel and ensemble artifacts (issues #43, #46)"
```

- [ ] **Step 6: Close issues on GitHub**

```bash
gh issue close 46 --comment "Implemented in src/models/train_draw_submodel.py + EnsembleModel draw blend. Artifacts saved."
gh issue close 43 --comment "Implemented in src/models/ensemble_model.py + train_ensemble.py. ensemble.joblib is now the default API model."
```
