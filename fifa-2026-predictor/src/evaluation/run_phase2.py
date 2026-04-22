"""Phase 2 evaluation entry point.

Evaluates all five models (two baselines + Elo-only + LogReg + XGBoost) on:
  1. A static chronological test split
  2. A rolling-origin backtest across multiple time windows

Usage
-----
    python -m src.evaluation.run_phase2
    python -m src.evaluation.run_phase2 --n-backtest-windows 8
    python -m src.evaluation.run_phase2 --skip-backtest
"""

from __future__ import annotations

import argparse

import pandas as pd

from src.evaluation.backtest import aggregate_backtest_results, run_backtest
from src.evaluation.baselines import all_models
from src.evaluation.metrics import compute_metrics
from src.evaluation.reporting import (
    print_backtest_aggregate,
    print_summary_table,
    save_backtest_report,
    save_calibration_plots,
    save_evaluation_report,
)
from src.models.common import load_feature_data, make_chronological_split, to_xy
from src.utils import load_config

TARGET_MAP = {"A": 0, "D": 1, "H": 2}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 2 evaluation pipeline.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    parser.add_argument("--n-backtest-windows", type=int, default=5,
                        help="Number of rolling-origin test windows.")
    parser.add_argument("--min-train-frac", type=float, default=0.6,
                        help="Minimum fraction of data used as initial training window.")
    parser.add_argument("--skip-backtest", action="store_true",
                        help="Skip rolling-origin backtest (faster, static split only).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config()

    print("Loading feature data …")
    df = load_feature_data(args.features_csv)
    print(f"Total rows: {len(df)}  |  date range: {df['date'].min().date()} – {df['date'].max().date()}")

    train_df, val_df, test_df = make_chronological_split(
        df,
        val_size=float(cfg["model"]["val_size"]),
        test_size=float(cfg["model"]["test_size"]),
    )
    # Train on train+val so XGBoost gets more data (no early stopping needed here)
    train_full = pd.concat([train_df, val_df]).reset_index(drop=True)
    print(
        f"Static split — train+val: {len(train_full)}, test: {len(test_df)}"
        f"  ({test_df['date'].min().date()} – {test_df['date'].max().date()})"
    )

    y_test = test_df["target"].map(TARGET_MAP).astype(int).values

    # ------------------------------------------------------------------
    # 1. Static test-split evaluation
    # ------------------------------------------------------------------
    print("\n=== Static test-split evaluation ===")
    models = all_models(cfg)
    all_metrics: list[dict] = []
    for model in models:
        print(f"  Fitting {model.name} …")
        model.fit(train_full)
        y_prob = model.predict_proba(test_df)
        metrics = compute_metrics(y_test, y_prob, model.name)
        all_metrics.append(metrics)

    print_summary_table(all_metrics)
    save_evaluation_report(all_metrics)
    save_calibration_plots(all_metrics)

    # ------------------------------------------------------------------
    # 2. Rolling-origin backtest
    # ------------------------------------------------------------------
    if not args.skip_backtest:
        print("\n=== Rolling-origin backtest ===")
        backtest_models = all_models(cfg)
        halflife = float(cfg["features"].get("time_decay_halflife_days", 730))

        window_results = run_backtest(
            models=backtest_models,
            df=df,
            min_train_frac=args.min_train_frac,
            n_windows=args.n_backtest_windows,
            halflife_days=halflife,
        )
        if window_results:
            aggregate = aggregate_backtest_results(window_results)
            save_backtest_report(window_results, aggregate)
            print_backtest_aggregate(aggregate)
        else:
            print("No backtest windows generated — dataset may be too small.")

    print("\nPhase 2 complete.")
    print("Reports saved in: reports/")


if __name__ == "__main__":
    main()
