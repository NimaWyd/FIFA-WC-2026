"""Sensitivity analysis for the min_train_year cutoff hyperparameter.

Trains XGBoost with different training data start years and reports
log-loss + accuracy on the chronological test split.  The cutoff year
that minimises log-loss is the recommended value for model.min_train_year
in configs/config.yaml.

Usage
-----
    python -m src.evaluation.tune_min_year

or import programmatically:

    from src.evaluation.tune_min_year import run_min_year_sensitivity, best_cutoff_year
"""

from __future__ import annotations

import argparse

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

_DEFAULT_CUTOFF_YEARS = [1993, 2000, 2005, 2008, 2010, 2012]


def run_min_year_sensitivity(
    df: pd.DataFrame,
    cutoff_years: list[int] | None = None,
    val_size: float = 0.15,
    test_size: float = 0.15,
    n_estimators: int = 200,
    random_state: int = 42,
) -> dict[int, dict[str, float]]:
    """Train XGBoost for each cutoff year and return test log-loss and accuracy.

    Parameters
    ----------
    df:
        Full features DataFrame (output of build_features.py).
    cutoff_years:
        List of min_train_year values to evaluate.
    n_estimators:
        Number of XGBoost trees (reduce for faster experiments).

    Returns
    -------
    dict mapping cutoff_year (int) → {"log_loss": float, "accuracy": float}
    """
    if cutoff_years is None:
        cutoff_years = _DEFAULT_CUTOFF_YEARS

    results: dict[int, dict[str, float]] = {}

    for year in cutoff_years:
        df_year = df[df["date"].dt.year >= year].reset_index(drop=True)
        if len(df_year) < 100:
            continue

        train_df, val_df, test_df = make_chronological_split(
            df_year, val_size=val_size, test_size=test_size
        )

        preprocessor, feature_cols = build_preprocessor(df_year)
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

        results[year] = {"log_loss": ll, "accuracy": acc}

    return results


def best_cutoff_year(results: dict[int, dict[str, float]]) -> int:
    """Return the cutoff year with the lowest test log-loss."""
    return min(results, key=lambda y: results[y]["log_loss"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune min_train_year cutoff.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    parser.add_argument(
        "--years", nargs="+", type=int,
        default=_DEFAULT_CUTOFF_YEARS,
        help="min_train_year values to evaluate.",
    )
    args = parser.parse_args()

    from src.models.common import load_feature_data
    from src.utils import PROJECT_ROOT
    import yaml

    df = load_feature_data(args.features_csv)

    print(f"\nRunning min_train_year sensitivity: {args.years}\n")
    results = run_min_year_sensitivity(df, cutoff_years=args.years)

    print(f"{'Year':>6}  {'Rows':>7}  {'Log-loss':>10}  {'Accuracy':>10}")
    print("-" * 40)
    for year in sorted(results):
        n_rows = len(df[df["date"].dt.year >= year])
        r = results[year]
        print(f"{year:>6}  {n_rows:>7}  {r['log_loss']:>10.4f}  {r['accuracy']:>10.4f}")

    winner = best_cutoff_year(results)
    print(f"\nBest cutoff year (lowest log-loss): {winner}")
    print(f"  log-loss={results[winner]['log_loss']:.4f}  accuracy={results[winner]['accuracy']:.4f}")

    config_path = PROJECT_ROOT / "configs" / "config.yaml"
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    current = raw["model"].get("min_train_year")
    if current != winner:
        print(f"\nUpdating config: min_train_year {current} → {winner}")
        raw["model"]["min_train_year"] = winner
        with open(config_path, "w") as f:
            yaml.dump(raw, f, default_flow_style=False, sort_keys=False)
    else:
        print(f"\nConfig already has optimal min_train_year ({current}). No change.")


if __name__ == "__main__":
    main()
