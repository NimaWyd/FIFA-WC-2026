"""Accuracy improvements evaluation entry point.

Evaluates the expanded model suite (including tuned XGBoost and MLP) against
all models from earlier phases, with special attention to draw-class performance.

Usage
-----
    python -m src.evaluation.run_accuracy_improvements
    python -m src.evaluation.run_accuracy_improvements --n-backtest-windows 8
    python -m src.evaluation.run_accuracy_improvements --skip-backtest
    python -m src.evaluation.run_accuracy_improvements --features-csv data/processed/features.csv

Prerequisites
-------------
    python -m src.features.build_features --input-csv data/raw/results.csv
    python -m src.models.tune_xgb  (optional, improves xgboost_tuned)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
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
from src.models.common import TARGET_MAP, load_feature_data, make_chronological_split, to_xy
from src.utils import PROJECT_ROOT, load_config

REPORTS_DIR = PROJECT_ROOT / "reports"


def _print_draw_performance(all_metrics: list[dict]) -> None:
    """Print draw-class precision/recall for every model — the hardest class."""
    print("\n=== Draw-class performance ===")
    print(f"{'Model':<22}  {'Prec_D':>7}  {'Rec_D':>7}  {'F1_D':>7}  {'Supp_D':>7}")
    print("-" * 58)
    for m in sorted(all_metrics, key=lambda x: -(x.get("per_class", {}).get("D", {}).get("recall", 0))):
        d = m.get("per_class", {}).get("D", {})
        print(
            f"{m['model']:<22}  "
            f"{d.get('precision', float('nan')):7.3f}  "
            f"{d.get('recall', float('nan')):7.3f}  "
            f"{d.get('f1', float('nan')):7.3f}  "
            f"{d.get('support', 0):7d}"
        )


def save_accuracy_improvements_report(
    all_metrics: list[dict],
    backtest_aggregate: dict | None,
    reports_dir: Path,
) -> None:
    """Save accuracy improvements summary to CSV and JSON."""
    reports_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for m in all_metrics:
        row: dict = {
            "model": m["model"],
            "accuracy": m.get("accuracy"),
            "log_loss": m.get("log_loss"),
            "brier_score": m.get("brier_score"),
            "n_samples": m.get("n_samples"),
        }
        for cls_name in ("A", "D", "H"):
            cls_m = m.get("per_class", {}).get(cls_name, {})
            row[f"precision_{cls_name}"] = cls_m.get("precision")
            row[f"recall_{cls_name}"] = cls_m.get("recall")
            row[f"f1_{cls_name}"] = cls_m.get("f1")
            row[f"support_{cls_name}"] = cls_m.get("support")
        row["macro_precision"] = m.get("macro", {}).get("precision")
        row["macro_recall"] = m.get("macro", {}).get("recall")
        rows.append(row)

    csv_path = reports_dir / "accuracy_improvements_summary.csv"
    json_path = reports_dir / "accuracy_improvements_summary.json"
    pd.DataFrame(rows).round(4).to_csv(csv_path, index=False)

    payload = {
        "static_eval": all_metrics,
        "backtest_aggregate": backtest_aggregate,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved accuracy improvements CSV  : {csv_path}")
    print(f"Saved accuracy improvements JSON : {json_path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Accuracy improvements evaluation.")
    p.add_argument("--features-csv", default="data/processed/features.csv")
    p.add_argument("--n-backtest-windows", type=int, default=5)
    p.add_argument("--min-train-frac", type=float, default=0.6)
    p.add_argument("--skip-backtest", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config()

    print("Loading feature data …")
    df = load_feature_data(args.features_csv)
    print(
        f"Total rows: {len(df)}"
        f"  |  date range: {df['date'].min().date()} – {df['date'].max().date()}"
    )

    # Log which new features are present
    new_feats = [c for c in (
        "home_draw_rate_w5", "away_draw_rate_w5", "draw_rate_diff",
        "h2h_home_win_rate", "h2h_draw_rate", "h2h_goal_diff", "h2h_n_matches",
    ) if c in df.columns]
    print(f"New features present: {new_feats if new_feats else 'none (rebuild features first)'}")

    train_df, val_df, test_df = make_chronological_split(
        df,
        val_size=float(cfg["model"]["val_size"]),
        test_size=float(cfg["model"]["test_size"]),
    )
    train_full = pd.concat([train_df, val_df]).reset_index(drop=True)
    print(
        f"\nStatic split — train+val: {len(train_full)}, test: {len(test_df)}"
        f"  ({test_df['date'].min().date()} – {test_df['date'].max().date()})"
    )

    y_test = test_df["target"].map(TARGET_MAP).astype(int).values

    # ------------------------------------------------------------------
    # Static test-split evaluation
    # ------------------------------------------------------------------
    print("\n=== Static test-split evaluation ===")
    models = all_models(cfg)
    all_metrics: list[dict] = []
    for model in models:
        try:
            print(f"  Fitting {model.name} …")
            model.fit(train_full)
            y_prob = model.predict_proba(test_df)
            metrics = compute_metrics(y_test, y_prob, model.name)
            all_metrics.append(metrics)
        except Exception as exc:
            print(f"  {model.name}: ERROR — {exc}")

    print_summary_table(all_metrics)
    _print_draw_performance(all_metrics)

    # ------------------------------------------------------------------
    # Rolling-origin backtest
    # ------------------------------------------------------------------
    backtest_aggregate: dict | None = None
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
            backtest_aggregate = aggregate_backtest_results(window_results)
            save_backtest_report(window_results, backtest_aggregate)
            print_backtest_aggregate(backtest_aggregate)
        else:
            print("No backtest windows generated — dataset may be too small.")

    # ------------------------------------------------------------------
    # Save reports
    # ------------------------------------------------------------------
    save_accuracy_improvements_report(all_metrics, backtest_aggregate, REPORTS_DIR)
    save_evaluation_report(all_metrics)
    save_calibration_plots(all_metrics)

    print("\nAccuracy improvements evaluation complete.")
    print("Reports saved in: reports/")


if __name__ == "__main__":
    main()
