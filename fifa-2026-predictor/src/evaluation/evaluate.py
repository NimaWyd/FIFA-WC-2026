"""Evaluate trained models with chronological test split."""

from __future__ import annotations

import argparse
import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import accuracy_score, log_loss

from src.models.common import (
    INV_TARGET_MAP,
    TARGET_MAP,
    build_preprocessor,
    load_feature_data,
    make_chronological_split,
    to_xy,
)
from src.utils import PROJECT_ROOT, ensure_parent_dir, load_config


def multiclass_brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    one_hot = np.eye(y_prob.shape[1])[y_true]
    return float(np.mean(np.sum((y_prob - one_hot) ** 2, axis=1)))


def align_predict_proba(y_prob: np.ndarray, classes: np.ndarray) -> np.ndarray:
    """Reorder sklearn/XGBoost `predict_proba` columns to ascending class label 0, 1, …"""
    classes = np.asarray(classes).astype(int).ravel()
    if classes.size != y_prob.shape[1]:
        raise ValueError("classes length must match number of probability columns.")
    order = np.argsort(classes)
    if np.array_equal(order, np.arange(len(classes))):
        return y_prob
    return y_prob[:, order]


def save_calibration_plot(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    output_png: str,
) -> None:
    plt.figure(figsize=(8, 6))
    for idx in range(y_prob.shape[1]):
        cls = INV_TARGET_MAP[idx]
        binary_true = (y_true == idx).astype(int)
        frac_pos, mean_pred = calibration_curve(binary_true, y_prob[:, idx], n_bins=5)
        plt.plot(mean_pred, frac_pos, marker="o", label=f"Class {cls}")

    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect calibration")
    plt.xlabel("Mean predicted probability")
    plt.ylabel("Observed frequency")
    plt.title("Calibration Curves")
    plt.legend()
    output_path = PROJECT_ROOT / output_png
    ensure_parent_dir(output_path)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate match prediction model.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    parser.add_argument("--model-path", default="src/models/artifacts/xgb.joblib")
    parser.add_argument("--output-json", default="data/processed/evaluation/metrics.json")
    parser.add_argument(
        "--calibration-plot",
        default="data/processed/evaluation/calibration.png",
    )
    args = parser.parse_args()

    cfg = load_config()
    df = load_feature_data(args.features_csv)
    _, _, test_df = make_chronological_split(
        df,
        val_size=float(cfg["model"]["val_size"]),
        test_size=float(cfg["model"]["test_size"]),
    )

    model = joblib.load(PROJECT_ROOT / args.model_path)
    _, feature_cols = build_preprocessor(df)
    x_test, y_test = to_xy(test_df, feature_cols)

    y_prob_raw = model.predict_proba(x_test)
    clf = model.named_steps["classifier"]
    y_prob = align_predict_proba(y_prob_raw, clf.classes_)
    y_pred = np.argmax(y_prob, axis=1)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "log_loss": float(log_loss(y_test, y_prob, labels=[0, 1, 2])),
        "brier_score": multiclass_brier_score(y_test, y_prob),
        "class_mapping": TARGET_MAP,
        "test_rows": len(test_df),
    }
    output_path = PROJECT_ROOT / args.output_json
    ensure_parent_dir(output_path)
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    save_calibration_plot(y_test, y_prob, args.calibration_plot)
    print(json.dumps(metrics, indent=2))
    print(f"Saved metrics to {output_path}")


if __name__ == "__main__":
    main()

