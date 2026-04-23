"""Baseline models and consistent ML model wrappers for unified evaluation."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.models.common import TARGET_MAP, build_preprocessor, to_xy


class BaseModel(ABC):
    """Common interface for every baseline and ML model."""

    name: str

    @abstractmethod
    def fit(self, train_df: pd.DataFrame) -> None:
        """Fit the model using the training split (full DataFrame with target column)."""

    @abstractmethod
    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Return (n, 3) probability array ordered [A=0, D=1, H=2]."""

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return np.argmax(self.predict_proba(df), axis=1)


# ---------------------------------------------------------------------------
# Simple baselines
# ---------------------------------------------------------------------------

class MostFrequentBaseline(BaseModel):
    """Always predicts the historically most common outcome class."""

    name = "most_frequent"

    def __init__(self) -> None:
        self._proba: np.ndarray | None = None

    def fit(self, train_df: pd.DataFrame) -> None:
        y = train_df["target"].map(TARGET_MAP).astype(int).values
        counts = np.bincount(y, minlength=3)
        most_frequent = int(np.argmax(counts))
        self._proba = np.zeros(3)
        self._proba[most_frequent] = 1.0

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        if self._proba is None:
            raise RuntimeError("Call fit() before predict_proba().")
        return np.tile(self._proba, (len(df), 1))


class ClassPriorBaseline(BaseModel):
    """Predicts class probabilities from training distribution for every sample."""

    name = "class_prior"

    def __init__(self) -> None:
        self._proba: np.ndarray | None = None

    def fit(self, train_df: pd.DataFrame) -> None:
        y = train_df["target"].map(TARGET_MAP).astype(int).values
        counts = np.bincount(y, minlength=3)
        self._proba = counts / counts.sum()

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        if self._proba is None:
            raise RuntimeError("Call fit() before predict_proba().")
        return np.tile(self._proba, (len(df), 1))


# ---------------------------------------------------------------------------
# Elo-only baseline
# ---------------------------------------------------------------------------

class EloOnlyBaseline(BaseModel):
    """Logistic regression using only the four Elo-derived features.

    Explicit feature path so there is no ambiguity about what information
    this baseline uses.  The four features are:
        home_elo_pre, away_elo_pre, elo_diff_home_away, elo_win_prob
    """

    name = "elo_only"
    ELO_FEATURES: list[str] = [
        "home_elo_pre",
        "away_elo_pre",
        "elo_diff_home_away",
        "elo_win_prob",
    ]

    def __init__(self, max_iter: int = 1000) -> None:
        self._max_iter = max_iter
        self._pipeline: Pipeline | None = None

    def fit(self, train_df: pd.DataFrame) -> None:
        missing = [c for c in self.ELO_FEATURES if c not in train_df.columns]
        if missing:
            raise ValueError(f"EloOnlyBaseline: missing columns {missing}")
        X = train_df[self.ELO_FEATURES]
        y = train_df["target"].map(TARGET_MAP).astype(int).values
        self._pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=self._max_iter, class_weight="balanced")),
        ])
        self._pipeline.fit(X, y)

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        if self._pipeline is None:
            raise RuntimeError("Call fit() before predict_proba().")
        missing = [c for c in self.ELO_FEATURES if c not in df.columns]
        if missing:
            raise ValueError(f"EloOnlyBaseline.predict_proba: missing columns {missing}")
        raw = self._pipeline.predict_proba(df[self.ELO_FEATURES])
        return _reorder_to_012(raw, self._pipeline.named_steps["clf"].classes_)


# ---------------------------------------------------------------------------
# Full-feature ML wrappers
# ---------------------------------------------------------------------------

class LogRegModel(BaseModel):
    """Full-feature logistic regression (consistent with train_logreg.py)."""

    name = "logreg"

    def __init__(self, max_iter: int = 1500) -> None:
        self._max_iter = max_iter
        self._pipeline: Pipeline | None = None
        self._feature_cols: list[str] | None = None

    def fit(self, train_df: pd.DataFrame) -> None:
        preprocessor, feature_cols = build_preprocessor(train_df)
        self._feature_cols = feature_cols
        X, y = to_xy(train_df, feature_cols)
        weights = (
            train_df["match_weight"].values if "match_weight" in train_df.columns else None
        )
        self._pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(
                max_iter=self._max_iter,
                class_weight="balanced",
            )),
        ])
        fit_kwargs: dict = {}
        if weights is not None:
            fit_kwargs["classifier__sample_weight"] = weights
        self._pipeline.fit(X, y, **fit_kwargs)

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        if self._pipeline is None:
            raise RuntimeError("Call fit() before predict_proba().")
        X, _ = to_xy(df, self._feature_cols)  # type: ignore[arg-type]
        raw = self._pipeline.predict_proba(X)
        return _reorder_to_012(raw, self._pipeline.named_steps["classifier"].classes_)


class XGBoostModel(BaseModel):
    """Full-feature XGBoost (consistent with train_xgb.py; no early stopping in backtest)."""

    name = "xgboost"

    def __init__(self, cfg: dict | None = None) -> None:
        self._cfg = cfg or {}
        self._pipeline: Pipeline | None = None
        self._feature_cols: list[str] | None = None

    def fit(self, train_df: pd.DataFrame) -> None:
        from xgboost import XGBClassifier

        preprocessor, feature_cols = build_preprocessor(train_df)
        self._feature_cols = feature_cols
        X_train, y_train = to_xy(train_df, feature_cols)
        weights = (
            train_df["match_weight"].values if "match_weight" in train_df.columns else None
        )

        xgb_cfg = self._cfg.get("model", {}).get("xgb", {})
        classifier = XGBClassifier(
            n_estimators=int(xgb_cfg.get("n_estimators", 300)),
            learning_rate=float(xgb_cfg.get("learning_rate", 0.05)),
            max_depth=int(xgb_cfg.get("max_depth", 3)),
            subsample=float(xgb_cfg.get("subsample", 0.8)),
            colsample_bytree=float(xgb_cfg.get("colsample_bytree", 0.8)),
            min_child_weight=int(xgb_cfg.get("min_child_weight", 2)),
            gamma=float(xgb_cfg.get("gamma", 0.1)),
            reg_alpha=float(xgb_cfg.get("reg_alpha", 0.1)),
            reg_lambda=float(xgb_cfg.get("reg_lambda", 1.0)),
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            random_state=int(self._cfg.get("project", {}).get("random_state", 42)),
        )

        # Fit preprocessor on train, then fit classifier on transformed data.
        # This replicates train_xgb.py without requiring a separate val set.
        preprocessor.fit(X_train)
        X_train_t = preprocessor.transform(X_train)
        fit_kwargs: dict = {"verbose": False}
        if weights is not None:
            fit_kwargs["sample_weight"] = weights
        classifier.fit(X_train_t, y_train, **fit_kwargs)

        # Wrap in a Pipeline container for uniform predict_proba interface.
        self._pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ])

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        if self._pipeline is None:
            raise RuntimeError("Call fit() before predict_proba().")
        X, _ = to_xy(df, self._feature_cols)  # type: ignore[arg-type]
        raw = self._pipeline.predict_proba(X)
        return _reorder_to_012(raw, self._pipeline.named_steps["classifier"].classes_)


class XGBoostTunedModel(BaseModel):
    """XGBoost with hyperparameters loaded from tuning results (Issue 4).

    Falls back to default config params when no tuning results file exists.
    """

    name = "xgboost_tuned"
    _TUNING_RESULTS_PATH = "reports/xgb_tuning_results.json"

    def __init__(self, cfg: dict | None = None, tuning_path: str | None = None) -> None:
        from src.utils import PROJECT_ROOT
        self._cfg = cfg or {}
        path = PROJECT_ROOT / (tuning_path or self._TUNING_RESULTS_PATH)
        self._tuned_params: dict = {}
        if path.exists():
            import json
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                self._tuned_params = data.get("best_params", {})
            except Exception:
                pass
        self._pipeline = None
        self._feature_cols = None

    def _merged_params(self) -> dict:
        """Merge tuned params on top of config defaults."""
        base = dict(self._cfg.get("model", {}).get("xgb", {}))
        base.update(self._tuned_params)
        return base

    def fit(self, train_df: pd.DataFrame) -> None:
        from xgboost import XGBClassifier

        preprocessor, feature_cols = build_preprocessor(train_df)
        self._feature_cols = feature_cols
        X_train, y_train = to_xy(train_df, feature_cols)
        weights = (
            train_df["match_weight"].values if "match_weight" in train_df.columns else None
        )

        p = self._merged_params()
        classifier = XGBClassifier(
            n_estimators=int(p.get("n_estimators", 300)),
            learning_rate=float(p.get("learning_rate", 0.05)),
            max_depth=int(p.get("max_depth", 3)),
            subsample=float(p.get("subsample", 0.8)),
            colsample_bytree=float(p.get("colsample_bytree", 0.8)),
            min_child_weight=int(p.get("min_child_weight", 2)),
            gamma=float(p.get("gamma", 0.1)),
            reg_alpha=float(p.get("reg_alpha", 0.1)),
            reg_lambda=float(p.get("reg_lambda", 1.0)),
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            random_state=int(self._cfg.get("project", {}).get("random_state", 42)),
        )

        preprocessor.fit(X_train)
        X_train_t = preprocessor.transform(X_train)
        fit_kwargs: dict = {"verbose": False}
        if weights is not None:
            fit_kwargs["sample_weight"] = weights
        classifier.fit(X_train_t, y_train, **fit_kwargs)

        self._pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ])

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        if self._pipeline is None:
            raise RuntimeError("Call fit() before predict_proba().")
        X, _ = to_xy(df, self._feature_cols)
        raw = self._pipeline.predict_proba(X)
        return _reorder_to_012(raw, self._pipeline.named_steps["classifier"].classes_)


class MLPModel(BaseModel):
    """Multi-layer perceptron classifier (Issue 6).

    Uses sklearn MLPClassifier with two hidden layers.  Class-balanced
    sample weights are applied when available.
    """

    name = "mlp"

    def __init__(self) -> None:
        self._pipeline = None
        self._feature_cols = None

    def fit(self, train_df: pd.DataFrame) -> None:
        from sklearn.neural_network import MLPClassifier

        preprocessor, feature_cols = build_preprocessor(train_df)
        self._feature_cols = feature_cols
        X_train, y_train = to_xy(train_df, feature_cols)
        weights = (
            train_df["match_weight"].values if "match_weight" in train_df.columns else None
        )

        clf = MLPClassifier(
            hidden_layer_sizes=(128, 64),
            activation="relu",
            solver="adam",
            alpha=0.01,
            learning_rate_init=0.001,
            max_iter=300,
            early_stopping=True,
            validation_fraction=0.1,
            random_state=42,
        )

        preprocessor.fit(X_train)
        X_train_t = preprocessor.transform(X_train)
        fit_kwargs: dict = {}
        if weights is not None:
            fit_kwargs["sample_weight"] = weights
        clf.fit(X_train_t, y_train, **fit_kwargs)

        self._pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", clf),
        ])

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        if self._pipeline is None:
            raise RuntimeError("Call fit() before predict_proba().")
        X, _ = to_xy(df, self._feature_cols)
        raw = self._pipeline.predict_proba(X)
        return _reorder_to_012(raw, self._pipeline.named_steps["classifier"].classes_)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reorder_to_012(raw: np.ndarray, classes: np.ndarray) -> np.ndarray:
    """Reorder probability columns to ascending class index [0, 1, 2]."""
    classes = np.asarray(classes).astype(int).ravel()
    order = np.argsort(classes)
    if np.array_equal(order, np.arange(len(classes))):
        return raw
    return raw[:, order]


def all_models(cfg: dict | None = None) -> list[BaseModel]:
    """Return one fresh instance of every model in the evaluation suite."""
    max_iter = int((cfg or {}).get("model", {}).get("logistic_max_iter", 1500))
    return [
        MostFrequentBaseline(),
        ClassPriorBaseline(),
        EloOnlyBaseline(),
        LogRegModel(max_iter=max_iter),
        XGBoostModel(cfg=cfg),
        XGBoostTunedModel(cfg=cfg),
        MLPModel(),
    ]
