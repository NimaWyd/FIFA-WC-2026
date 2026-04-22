"""Unified metrics computation for all models."""

from __future__ import annotations

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    log_loss,
    precision_recall_fscore_support,
)

from src.models.common import INV_TARGET_MAP

_EPS = 1e-10


def multiclass_brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    one_hot = np.eye(y_prob.shape[1])[y_true]
    return float(np.mean(np.sum((y_prob - one_hot) ** 2, axis=1)))


def _safe_log_loss(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Log loss with probability clipping to avoid log(0)."""
    clipped = np.clip(y_prob, _EPS, 1 - _EPS)
    row_sums = clipped.sum(axis=1, keepdims=True)
    clipped = clipped / row_sums
    return float(log_loss(y_true, clipped, labels=[0, 1, 2]))


def _calibration_summary(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    """One-vs-rest calibration for all three outcome classes."""
    result: dict = {}
    for i in range(3):
        cls_name = INV_TARGET_MAP[i]
        binary_true = (y_true == i).astype(int)
        # Skip if only one class present in binary_true
        if binary_true.sum() == 0 or binary_true.sum() == len(binary_true):
            result[cls_name] = {"ece": None, "mean_pred": [], "frac_pos": [],
                                "note": "degenerate — all samples same class"}
            continue
        try:
            frac_pos, mean_pred = calibration_curve(
                binary_true, y_prob[:, i], n_bins=5, strategy="uniform"
            )
            ece = float(np.mean(np.abs(frac_pos - mean_pred)))
            # Direction: positive ECE means overconfident if mean_pred > frac_pos on avg
            overconfident = float(np.mean(mean_pred - frac_pos)) > 0
            result[cls_name] = {
                "ece": round(ece, 6),
                "mean_pred": [round(float(v), 6) for v in mean_pred],
                "frac_pos": [round(float(v), 6) for v in frac_pos],
                "overconfident": overconfident,
            }
        except Exception as exc:
            result[cls_name] = {"ece": None, "mean_pred": [], "frac_pos": [],
                                "note": str(exc)}
    return result


def compute_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    model_name: str,
) -> dict:
    """Compute the full evaluation metric suite for one model.

    Parameters
    ----------
    y_true:
        Integer labels in {0=A, 1=D, 2=H}.
    y_prob:
        (n, 3) probability array ordered [A, D, H].
    model_name:
        Label used in reports.
    """
    y_pred = np.argmax(y_prob, axis=1)

    acc = float(accuracy_score(y_true, y_pred))
    ll = _safe_log_loss(y_true, y_prob)
    bs = multiclass_brier_score(y_true, y_prob)

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2], zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])

    per_class: dict = {}
    for i in range(3):
        cls_name = INV_TARGET_MAP[i]
        per_class[cls_name] = {
            "precision": round(float(precision[i]), 6),
            "recall": round(float(recall[i]), 6),
            "f1": round(float(f1[i]), 6),
            "support": int(support[i]),
        }

    total_support = int(sum(s for s in support))
    macro_precision = float(np.mean(precision))
    macro_recall = float(np.mean(recall))
    weighted_precision = (
        float(np.average(precision, weights=support)) if total_support > 0 else 0.0
    )
    weighted_recall = (
        float(np.average(recall, weights=support)) if total_support > 0 else 0.0
    )

    calibration = _calibration_summary(y_true, y_prob)

    return {
        "model": model_name,
        "accuracy": round(acc, 6),
        "log_loss": round(ll, 6),
        "brier_score": round(bs, 6),
        "per_class": per_class,
        "macro": {
            "precision": round(macro_precision, 6),
            "recall": round(macro_recall, 6),
        },
        "weighted": {
            "precision": round(weighted_precision, 6),
            "recall": round(weighted_recall, 6),
        },
        "confusion_matrix": cm.tolist(),
        "calibration": calibration,
        "n_samples": int(len(y_true)),
    }
