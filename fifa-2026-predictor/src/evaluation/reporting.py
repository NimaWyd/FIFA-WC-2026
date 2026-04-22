"""Persist evaluation results to structured reports and figures."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless rendering
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.utils import PROJECT_ROOT

REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"


def _ensure_dirs(reports_dir: Path, figures_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Static evaluation report
# ---------------------------------------------------------------------------

def save_evaluation_report(
    all_metrics: list[dict],
    reports_dir: Path | None = None,
) -> None:
    """Save metrics for all models to CSV and JSON."""
    reports_dir = reports_dir or REPORTS_DIR
    figures_dir = reports_dir / "figures"
    _ensure_dirs(reports_dir, figures_dir)

    rows: list[dict] = []
    for m in all_metrics:
        row: dict = {
            "model": m["model"],
            "accuracy": m.get("accuracy"),
            "log_loss": m.get("log_loss"),
            "brier_score": m.get("brier_score"),
            "n_samples": m.get("n_samples"),
        }
        for cls_name, cls_m in m.get("per_class", {}).items():
            row[f"precision_{cls_name}"] = cls_m.get("precision")
            row[f"recall_{cls_name}"] = cls_m.get("recall")
            row[f"f1_{cls_name}"] = cls_m.get("f1")
            row[f"support_{cls_name}"] = cls_m.get("support")
        row["macro_precision"] = m.get("macro", {}).get("precision")
        row["macro_recall"] = m.get("macro", {}).get("recall")
        row["weighted_precision"] = m.get("weighted", {}).get("precision")
        row["weighted_recall"] = m.get("weighted", {}).get("recall")
        for cls_name, cal in m.get("calibration", {}).items():
            row[f"ece_{cls_name}"] = cal.get("ece")
        rows.append(row)

    csv_path = reports_dir / "evaluation_summary.csv"
    json_path = reports_dir / "evaluation_summary.json"
    pd.DataFrame(rows).round(4).to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(all_metrics, indent=2), encoding="utf-8")
    print(f"Saved evaluation CSV  : {csv_path}")
    print(f"Saved evaluation JSON : {json_path}")


def save_calibration_plots(
    all_metrics: list[dict],
    reports_dir: Path | None = None,
) -> None:
    """Save one calibration figure per model (one-vs-rest, three subplots)."""
    reports_dir = reports_dir or REPORTS_DIR
    figures_dir = reports_dir / "figures"
    _ensure_dirs(reports_dir, figures_dir)

    for m in all_metrics:
        model_name = m["model"]
        calibration = m.get("calibration", {})
        if not calibration:
            continue

        class_names = list(calibration.keys())
        n_classes = len(class_names)
        fig, axes = plt.subplots(1, n_classes, figsize=(5 * n_classes, 4), squeeze=False)

        for ax, cls_name in zip(axes[0], class_names):
            cal = calibration[cls_name]
            mean_pred = cal.get("mean_pred", [])
            frac_pos = cal.get("frac_pos", [])
            ece = cal.get("ece")
            overconfident = cal.get("overconfident")

            ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfect")
            if mean_pred and frac_pos:
                ax.plot(mean_pred, frac_pos, marker="o", color="steelblue",
                        label=f"Actual (ECE={ece:.3f})" if ece is not None else "Actual")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_xlabel("Mean predicted prob", fontsize=9)
            ax.set_ylabel("Observed freq", fontsize=9)
            direction = ""
            if overconfident is not None:
                direction = " (overconfident)" if overconfident else " (underconfident)"
            ax.set_title(f"Class {cls_name}{direction}", fontsize=10)
            ax.legend(fontsize=8)

        fig.suptitle(f"Calibration — {model_name}", fontsize=12)
        fig.tight_layout()
        out_path = figures_dir / f"calibration_{model_name}.png"
        fig.savefig(out_path, dpi=100)
        plt.close(fig)
        print(f"Saved calibration plot : {out_path}")


# ---------------------------------------------------------------------------
# Backtest report
# ---------------------------------------------------------------------------

def save_backtest_report(
    window_results: list[dict],
    aggregate: dict,
    reports_dir: Path | None = None,
) -> None:
    """Save per-window backtest metrics and aggregate summary."""
    reports_dir = reports_dir or REPORTS_DIR
    figures_dir = reports_dir / "figures"
    _ensure_dirs(reports_dir, figures_dir)

    rows: list[dict] = []
    for wr in window_results:
        for model_name, m in wr["models"].items():
            rows.append({
                "window_idx": wr["window_idx"],
                "train_start": wr["train_start"],
                "train_end": wr["train_end"],
                "test_start": wr["test_start"],
                "test_end": wr["test_end"],
                "n_train": wr["n_train"],
                "n_test": wr["n_test"],
                "model": model_name,
                "accuracy": m.get("accuracy"),
                "log_loss": m.get("log_loss"),
                "brier_score": m.get("brier_score"),
                "error": m.get("error"),
            })

    csv_path = reports_dir / "backtest_windows.csv"
    json_path = reports_dir / "backtest_summary.json"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    json_path.write_text(
        json.dumps({"window_results": window_results, "aggregate": aggregate}, indent=2),
        encoding="utf-8",
    )
    print(f"Saved backtest CSV  : {csv_path}")
    print(f"Saved backtest JSON : {json_path}")

    # Accuracy-over-windows line chart
    _save_backtest_accuracy_plot(window_results, figures_dir)


def _save_backtest_accuracy_plot(
    window_results: list[dict],
    figures_dir: Path,
) -> None:
    model_names: list[str] = []
    for wr in window_results:
        for k in wr["models"]:
            if k not in model_names:
                model_names.append(k)

    if not model_names or not window_results:
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    window_labels = [
        f"W{wr['window_idx']}\n{wr['test_start'][:7]}" for wr in window_results
    ]

    for model_name in model_names:
        accs = [
            wr["models"].get(model_name, {}).get("accuracy")
            for wr in window_results
        ]
        accs_clean = [a if a is not None else np.nan for a in accs]
        ax.plot(window_labels, accs_clean, marker="o", label=model_name)

    ax.set_xlabel("Test window")
    ax.set_ylabel("Accuracy")
    ax.set_title("Accuracy per backtest window")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out_path = figures_dir / "backtest_accuracy.png"
    fig.savefig(out_path, dpi=100)
    plt.close(fig)
    print(f"Saved backtest plot : {out_path}")


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def print_summary_table(all_metrics: list[dict]) -> None:
    header = f"{'Model':<20}  {'Acc':>6}  {'LogLoss':>8}  {'Brier':>7}  {'n':>6}"
    sep = "=" * 55
    print(f"\n{sep}")
    print("Evaluation on static test split")
    print(sep)
    print(header)
    print("-" * 55)
    for m in sorted(all_metrics, key=lambda x: -(x.get("accuracy") or 0)):
        print(
            f"{m['model']:<20}  "
            f"{m.get('accuracy', float('nan')):6.3f}  "
            f"{m.get('log_loss', float('nan')):8.3f}  "
            f"{m.get('brier_score', float('nan')):7.3f}  "
            f"{m.get('n_samples', 0):6d}"
        )
    print(sep)


def print_backtest_aggregate(aggregate: dict) -> None:
    per_model = aggregate.get("per_model", {})
    ranking = aggregate.get("ranking_by_accuracy", list(per_model.keys()))
    header = f"{'Model':<20}  {'MeanAcc':>8}  {'StdAcc':>7}  {'MeanLL':>7}  {'MeanBS':>7}"
    sep = "=" * 58
    print(f"\n{sep}")
    print("Rolling-origin backtest — aggregate")
    print(sep)
    print(header)
    print("-" * 58)
    for model_name in ranking:
        m = per_model.get(model_name, {})
        print(
            f"{model_name:<20}  "
            f"{m.get('mean_accuracy') or float('nan'):8.3f}  "
            f"{m.get('std_accuracy') or float('nan'):7.3f}  "
            f"{m.get('mean_log_loss') or float('nan'):7.3f}  "
            f"{m.get('mean_brier_score') or float('nan'):7.3f}"
        )
    print(sep)
