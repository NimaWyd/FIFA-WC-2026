"""SHAP feature importance analysis for the trained XGBoost model (issue #82).

Usage
-----
    python -m src.evaluation.feature_importance

Outputs top-20 features by mean |SHAP| and flags near-zero contributors
as candidates for removal. Results are printed to stdout and optionally
saved to a JSON file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import shap

from src.models.common import TARGET_MAP, load_feature_data
from src.utils import PROJECT_ROOT, load_config


def _get_feature_names(preprocessor) -> list[str]:
    """Return post-transform feature names from a fitted ColumnTransformer."""
    return [
        name.split("__", 1)[-1]
        for name in preprocessor.get_feature_names_out()
    ]


def _get_input_columns(preprocessor) -> list[str]:
    """Return the original input column names from a fitted ColumnTransformer."""
    cols: list[str] = []
    for name, _, columns in preprocessor.transformers_:
        if name == "remainder":
            continue
        cols.extend(columns)
    return cols


def compute_shap_importance(
    model_path: Path,
    features_csv: Path,
    top_n: int = 20,
    low_importance_threshold: float = 0.001,
    sample_n: Optional[int] = 2000,
    output_json: Optional[Path] = None,
) -> dict:
    """Compute SHAP feature importance for a trained XGBoost pipeline.

    Parameters
    ----------
    model_path:               Path to xgb.joblib
    features_csv:             Path to features.csv (used to reconstruct preprocessor)
    top_n:                    Number of top features to report
    low_importance_threshold: Features with mean |SHAP| below this are candidates
                              for removal
    sample_n:                 Subsample rows for speed (None = use all)
    output_json:              If provided, write results to this JSON file

    Returns
    -------
    dict with keys:
      top_features            — list of {feature, mean_abs_shap}, sorted desc
      low_importance_candidates — list of feature names below threshold
      n_features_analyzed     — total number of post-transform features
      n_samples               — number of rows used for SHAP computation
    """
    pipeline = joblib.load(model_path)
    preprocessor = pipeline.named_steps["preprocessor"]
    xgb_clf = pipeline.named_steps["classifier"].classifier  # unwrap IsotonicCalibrationWrapper

    df = load_feature_data(str(features_csv))
    cfg = load_config()
    min_year = int(cfg["model"].get("min_train_year", 0))
    if min_year > 0:
        df = df[pd.to_datetime(df["date"]).dt.year >= min_year].reset_index(drop=True)

    feature_cols = _get_input_columns(preprocessor)
    # Fill columns absent from this CSV with 0 (optional features added after training)
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0
    X = df[feature_cols].copy()
    y_series = df["target"].map(TARGET_MAP)
    X = X[y_series.notna()]

    if sample_n is not None and len(X) > sample_n:
        rng = np.random.default_rng(42)
        idx = rng.choice(len(X), sample_n, replace=False)
        X = X.iloc[idx]

    X_t = preprocessor.transform(X)
    feature_names = _get_feature_names(preprocessor)

    explainer = shap.TreeExplainer(xgb_clf)
    shap_values = explainer.shap_values(X_t)

    # shap_values is either a list of (n_samples, n_features) arrays (one per
    # class) or a single (n_samples, n_features, n_classes) array.
    if isinstance(shap_values, list):
        mean_abs = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
    elif shap_values.ndim == 3:
        mean_abs = np.abs(shap_values).mean(axis=(0, 2))
    else:
        mean_abs = np.abs(shap_values).mean(axis=0)

    importance_df = (
        pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_abs.tolist()})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )

    top_features = importance_df.head(top_n).to_dict("records")
    low_candidates = importance_df.loc[
        importance_df["mean_abs_shap"] < low_importance_threshold, "feature"
    ].tolist()

    result = {
        "top_features": top_features,
        "low_importance_candidates": low_candidates,
        "n_features_analyzed": len(feature_names),
        "n_samples": len(X),
    }

    if output_json is not None:
        output_json = Path(output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


def _print_report(result: dict) -> None:
    print(f"\n{'='*60}")
    print(f"SHAP Feature Importance  ({result['n_samples']} samples, "
          f"{result['n_features_analyzed']} features)")
    print(f"{'='*60}")
    print(f"\nTop {len(result['top_features'])} features:\n")
    for i, entry in enumerate(result["top_features"], 1):
        bar = "#" * int(entry["mean_abs_shap"] / result["top_features"][0]["mean_abs_shap"] * 30)
        print(f"  {i:>2}. {entry['feature']:<40} {entry['mean_abs_shap']:.5f}  {bar}")

    candidates = result["low_importance_candidates"]
    print(f"\nLow-importance candidates for removal ({len(candidates)}):")
    if candidates:
        for name in candidates:
            print(f"  - {name}")
    else:
        print("  (none below threshold)")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="SHAP feature importance analysis.")
    parser.add_argument("--model-path", default="src/models/artifacts/xgb.joblib")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--threshold", type=float, default=0.001,
                        help="Mean |SHAP| below this → candidate for removal")
    parser.add_argument("--sample-n", type=int, default=2000,
                        help="Rows to sample for SHAP (0 = all)")
    parser.add_argument("--output-json", default=None,
                        help="Optional path to save JSON results")
    args = parser.parse_args()

    result = compute_shap_importance(
        model_path=PROJECT_ROOT / args.model_path,
        features_csv=PROJECT_ROOT / args.features_csv,
        top_n=args.top_n,
        low_importance_threshold=args.threshold,
        sample_n=args.sample_n if args.sample_n > 0 else None,
        output_json=Path(args.output_json) if args.output_json else None,
    )
    _print_report(result)


if __name__ == "__main__":
    main()
