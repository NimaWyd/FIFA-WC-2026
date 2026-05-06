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

    print("Getting val-set predictions...")
    p_xgb_val = _pipeline_proba_ordered(xgb_pipeline, val_df, feature_cols)
    p_logreg_val = _pipeline_proba_ordered(logreg_pipeline, val_df, feature_cols)
    p_mlp_val = mlp.predict_proba(val_df)

    y_val = val_df["target"].map(TARGET_MAP).astype(int).values

    print("Optimizing per-class blend weights...")
    per_class_weights = _optimize_per_class_weights(p_xgb_val, p_logreg_val, p_mlp_val, y_val)
    print(f"Per-class weights (rows=XGB/LogReg/MLP, cols=A/D/H):\n{np.round(per_class_weights, 3)}")

    # Blended draw probability on val set (D = class index 1)
    blended_draw_val = np.zeros(len(val_df))
    for m_idx, p in enumerate([p_xgb_val, p_logreg_val, p_mlp_val]):
        blended_draw_val += per_class_weights[m_idx, 1] * p[:, 1]

    X_val_raw, _ = to_xy(val_df, feature_cols)
    p_draw_sub_val = draw_submodel.predict_proba(X_val_raw)[:, 1]

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
