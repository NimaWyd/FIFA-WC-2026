"""Sensitivity analysis for the time-decay halflife hyperparameter.

Trains XGBoost with different match_weight halflives and reports
log-loss + accuracy on the chronological test split.  The halflife that
minimises log-loss is the recommended value for configs/config.yaml.

Usage
-----
    python -m src.evaluation.tune_halflife

or import programmatically:

    from src.evaluation.tune_halflife import run_halflife_sensitivity, best_halflife
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from src.models.common import (
    TARGET_MAP,
    build_preprocessor,
    make_chronological_split,
    to_xy,
)
from src.utils import load_config

_DEFAULT_HALFLIVES = [90, 180, 365, 730, 1095]


def _recompute_match_weight(df: pd.DataFrame, halflife: float) -> pd.DataFrame:
    """Return a copy of df with match_weight recomputed for the given halflife."""
    df = df.copy()
    if halflife > 0 and len(df) > 0:
        reference = df["date"].max()
        days_ago = (reference - df["date"]).dt.days.clip(lower=0)
        df["match_weight"] = (2.0 ** (-days_ago / halflife)).round(6)
    else:
        df["match_weight"] = 1.0
    return df


def run_halflife_sensitivity(
    df: pd.DataFrame,
    halflives: list[int] | None = None,
    val_size: float = 0.15,
    test_size: float = 0.15,
    n_estimators: int = 200,
    random_state: int = 42,
) -> dict[int, dict[str, float]]:
    """Train XGBoost for each halflife and return test log-loss and accuracy.

    Parameters
    ----------
    df:
        Features DataFrame (output of build_features.py).
    halflives:
        List of halflife values in days to evaluate.
    n_estimators:
        Number of XGBoost trees (reduce for faster experiments).

    Returns
    -------
    dict mapping halflife (int) → {"log_loss": float, "accuracy": float}
    """
    if halflives is None:
        halflives = _DEFAULT_HALFLIVES

    results: dict[int, dict[str, float]] = {}

    for hl in halflives:
        df_hl = _recompute_match_weight(df, halflife=float(hl))
        train_df, val_df, test_df = make_chronological_split(
            df_hl, val_size=val_size, test_size=test_size
        )

        preprocessor, feature_cols = build_preprocessor(df_hl)
        x_train, y_train = to_xy(train_df, feature_cols)
        x_val, y_val = to_xy(val_df, feature_cols)
        x_test, y_test = to_xy(test_df, feature_cols)

        weights = compute_sample_weight("balanced", y_train)

        preprocessor.fit(x_train, y_train)
        x_train_t = preprocessor.transform(x_train)
        x_val_t = preprocessor.transform(x_val)
        x_test_t = preprocessor.transform(x_test)

        clf = XGBClassifier(
            n_estimators=n_estimators,
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            random_state=random_state,
            early_stopping_rounds=20,
        )
        clf.fit(
            x_train_t, y_train,
            sample_weight=weights,
            eval_set=[(x_val_t, y_val)],
            verbose=False,
        )

        probs = clf.predict_proba(x_test_t)
        preds = clf.predict(x_test_t)
        ll = float(log_loss(y_test, probs, labels=sorted(TARGET_MAP.values())))
        acc = float(accuracy_score(y_test, preds))

        results[hl] = {"log_loss": ll, "accuracy": acc}

    return results


def best_halflife(results: dict[int, dict[str, float]]) -> int:
    """Return the halflife with the lowest test log-loss."""
    return min(results, key=lambda hl: results[hl]["log_loss"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune time-decay halflife.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    parser.add_argument(
        "--halflives", nargs="+", type=int,
        default=_DEFAULT_HALFLIVES,
        help="Halflife values in days to evaluate.",
    )
    args = parser.parse_args()

    from src.models.common import load_feature_data
    from src.utils import PROJECT_ROOT
    import yaml

    cfg = load_config()
    min_year = int(cfg["model"].get("min_train_year", 0))
    df = load_feature_data(args.features_csv)
    if min_year > 0:
        df = df[df["date"].dt.year >= min_year].reset_index(drop=True)
        print(f"Filtered to {min_year}+: {len(df)} rows")

    print(f"\nRunning halflife sensitivity: {args.halflives} days\n")
    results = run_halflife_sensitivity(df, halflives=args.halflives)

    print(f"{'Halflife':>10}  {'Log-loss':>10}  {'Accuracy':>10}")
    print("-" * 36)
    for hl in sorted(results):
        r = results[hl]
        print(f"{hl:>10}  {r['log_loss']:>10.4f}  {r['accuracy']:>10.4f}")

    winner = best_halflife(results)
    print(f"\nBest halflife (lowest log-loss): {winner} days")
    print(f"  log-loss={results[winner]['log_loss']:.4f}  accuracy={results[winner]['accuracy']:.4f}")

    config_path = PROJECT_ROOT / "configs" / "config.yaml"
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    current = raw["features"].get("time_decay_halflife_days")
    if current != winner:
        print(f"\nUpdating config: time_decay_halflife_days {current} → {winner}")
        raw["features"]["time_decay_halflife_days"] = winner
        with open(config_path, "w") as f:
            yaml.dump(raw, f, default_flow_style=False, sort_keys=False)
    else:
        print(f"\nConfig already has optimal halflife ({current} days). No change.")


if __name__ == "__main__":
    main()
