"""Year-based rolling-origin cross-validation for XGBoost.

Expands training window by 2 years per fold. Each fold trains on all
data strictly before the test window start date.

Usage
-----
    python -m src.evaluation.rolling_cv
    python -m src.evaluation.rolling_cv --features-csv data/processed/features.csv
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from src.evaluation.baselines import XGBoostModel
from src.evaluation.metrics import compute_metrics
from src.models.common import TARGET_MAP, load_feature_data
from src.utils import load_config

FOLD_TEST_YEARS = [2011, 2013, 2015, 2017, 2019, 2021, 2023]


def rolling_cv_folds(
    df: pd.DataFrame,
    test_years: list[int] = FOLD_TEST_YEARS,
    min_train_rows: int = 100,
    min_test_rows: int = 10,
) -> list[tuple[pd.DataFrame, pd.DataFrame, int]]:
    """Return expanding-window (train, test, year) tuples.

    Each test window covers [year-01-01, year+2-01-01).
    Training uses all rows strictly before the test window start.
    Folds with insufficient data are silently skipped.
    """
    folds: list[tuple[pd.DataFrame, pd.DataFrame, int]] = []
    for year in test_years:
        test_start = pd.Timestamp(f"{year}-01-01")
        test_end = pd.Timestamp(f"{year + 2}-01-01")
        train = df[df["date"] < test_start].copy()
        test = df[(df["date"] >= test_start) & (df["date"] < test_end)].copy()
        if len(train) < min_train_rows or len(test) < min_test_rows:
            continue
        folds.append((train, test, year))
    return folds


def run_rolling_cv(
    features_csv: str = "data/processed/features.csv",
) -> list[dict]:
    """Run year-based rolling-origin CV and return per-fold metrics."""
    cfg = load_config()
    df = load_feature_data(features_csv)

    folds = rolling_cv_folds(df)
    if not folds:
        print("No folds generated — dataset may be too small or not span enough years.")
        return []

    header = f"{'Fold':<10} {'Train end':<12} {'Test end':<12} {'n_train':>8} {'n_test':>7} {'Accuracy':>9} {'Log-loss':>9}"
    print(header)
    print("-" * len(header))

    results: list[dict] = []
    for train_df, test_df, year in folds:
        model = XGBoostModel(cfg=cfg)
        model.fit(train_df)
        y_test = test_df["target"].map(TARGET_MAP).astype(int).values
        y_prob = model.predict_proba(test_df)
        m = compute_metrics(y_test, y_prob, "xgboost")
        row = {
            "test_year_start": year,
            "test_year_end": year + 1,
            "train_end": str(train_df["date"].max().date()),
            "test_end": str(test_df["date"].max().date()),
            "n_train": len(train_df),
            "n_test": len(test_df),
            "accuracy": m["accuracy"],
            "log_loss": m["log_loss"],
        }
        results.append(row)
        print(
            f"{year}–{year + 1:<5} "
            f"{row['train_end']:<12} "
            f"{row['test_end']:<12} "
            f"{row['n_train']:>8} "
            f"{row['n_test']:>7} "
            f"{row['accuracy']:>9.3f} "
            f"{row['log_loss']:>9.3f}"
        )

    accs = [r["accuracy"] for r in results]
    lls = [r["log_loss"] for r in results]
    sep = "-" * len(header)
    print(sep)
    print(f"{'Mean':>51} {np.mean(accs):>9.3f} {np.mean(lls):>9.3f}")
    print(f"{'Std':>51} {np.std(accs):>9.3f} {np.std(lls):>9.3f}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Year-based rolling-origin CV for XGBoost.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    args = parser.parse_args()
    run_rolling_cv(args.features_csv)


if __name__ == "__main__":
    main()
