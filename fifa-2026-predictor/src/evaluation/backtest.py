"""Rolling-origin evaluation with configurable time windows.

Each window trains on all data strictly before the test period and evaluates
on a future chunk — no leakage from future matches into training.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.evaluation.metrics import compute_metrics

TARGET_MAP = {"A": 0, "D": 1, "H": 2}


@dataclass
class BacktestWindow:
    window_idx: int
    train_start_date: pd.Timestamp
    train_end_date: pd.Timestamp
    test_start_date: pd.Timestamp
    test_end_date: pd.Timestamp
    n_train: int
    n_test: int


def rolling_windows(
    df: pd.DataFrame,
    min_train_frac: float = 0.6,
    n_windows: int = 5,
    min_test_size: int = 50,
) -> list[tuple[pd.DataFrame, pd.DataFrame, BacktestWindow]]:
    """Generate rolling-origin (expanding-window) train/test splits.

    All data before each test window is used for training, so the training
    set grows with each window.  Strictly chronological — no future leakage.

    Parameters
    ----------
    df:
        Feature DataFrame sorted by date.
    min_train_frac:
        Minimum fraction of data used as the initial training set.
    n_windows:
        Number of chronological test windows to generate.
    min_test_size:
        Minimum number of rows required in a test window.
    """
    df = df.sort_values("date").reset_index(drop=True)
    n = len(df)

    initial_train_n = int(n * min_train_frac)
    available = n - initial_train_n

    # Reduce windows if data is too sparse
    if available < min_test_size:
        return []
    n_windows = min(n_windows, available // min_test_size)
    if n_windows < 1:
        n_windows = 1

    window_size = available // n_windows

    results: list[tuple[pd.DataFrame, pd.DataFrame, BacktestWindow]] = []
    for i in range(n_windows):
        test_start_idx = initial_train_n + i * window_size
        # Last window absorbs any leftover rows
        if i == n_windows - 1:
            test_end_idx = n
        else:
            test_end_idx = test_start_idx + window_size

        if test_end_idx - test_start_idx < max(1, min_test_size // 2):
            break

        train_df = df.iloc[:test_start_idx].copy()
        test_df = df.iloc[test_start_idx:test_end_idx].copy()

        window = BacktestWindow(
            window_idx=i,
            train_start_date=df["date"].iloc[0],
            train_end_date=df["date"].iloc[test_start_idx - 1],
            test_start_date=df["date"].iloc[test_start_idx],
            test_end_date=df["date"].iloc[test_end_idx - 1],
            n_train=len(train_df),
            n_test=len(test_df),
        )
        results.append((train_df, test_df, window))

    return results


def _recompute_weights(train_df: pd.DataFrame, halflife_days: float = 730.0) -> pd.DataFrame:
    """Recompute time-decay weights relative to the end of this training window."""
    train_df = train_df.copy()
    ref_date = train_df["date"].max()
    days_ago = (ref_date - train_df["date"]).dt.days.clip(lower=0)
    train_df["match_weight"] = (2.0 ** (-days_ago / halflife_days)).round(6)
    return train_df


def run_backtest(
    models: list,
    df: pd.DataFrame,
    min_train_frac: float = 0.6,
    n_windows: int = 5,
    halflife_days: float = 730.0,
) -> list[dict]:
    """Run rolling-origin backtest for every model.

    Returns a list of per-window result dicts (one per window).
    """
    windows = rolling_windows(df, min_train_frac=min_train_frac, n_windows=n_windows)
    if not windows:
        print("WARNING: No backtest windows generated — dataset too small.")
        return []

    all_results: list[dict] = []

    for train_df_raw, test_df, window in windows:
        train_df = _recompute_weights(train_df_raw, halflife_days=halflife_days)
        y_test = test_df["target"].map(TARGET_MAP).astype(int).values

        print(
            f"\nWindow {window.window_idx}: "
            f"train={window.n_train} ({window.train_start_date.date()} – "
            f"{window.train_end_date.date()}), "
            f"test={window.n_test} ({window.test_start_date.date()} – "
            f"{window.test_end_date.date()})"
        )

        window_result: dict = {
            "window_idx": window.window_idx,
            "train_start": str(window.train_start_date.date()),
            "train_end": str(window.train_end_date.date()),
            "test_start": str(window.test_start_date.date()),
            "test_end": str(window.test_end_date.date()),
            "n_train": window.n_train,
            "n_test": window.n_test,
            "models": {},
        }

        for model in models:
            try:
                model.fit(train_df)
                y_prob = model.predict_proba(test_df)
                m = compute_metrics(y_test, y_prob, model.name)
                window_result["models"][model.name] = {
                    "accuracy": m["accuracy"],
                    "log_loss": m["log_loss"],
                    "brier_score": m["brier_score"],
                }
                print(
                    f"  {model.name:<20}  "
                    f"acc={m['accuracy']:.3f}  "
                    f"ll={m['log_loss']:.3f}  "
                    f"bs={m['brier_score']:.3f}"
                )
            except Exception as exc:
                print(f"  {model.name}: ERROR — {exc}")
                window_result["models"][model.name] = {"error": str(exc)}

        all_results.append(window_result)

    return all_results


def aggregate_backtest_results(window_results: list[dict]) -> dict:
    """Aggregate per-window metrics across all backtest windows.

    Returns aggregate stats per model and a ranking by mean accuracy.
    """
    model_names: set[str] = set()
    for wr in window_results:
        model_names.update(wr["models"].keys())

    per_model: dict = {}
    for model_name in model_names:
        accs, lls, bss = [], [], []
        for wr in window_results:
            m = wr["models"].get(model_name, {})
            if "error" not in m:
                if "accuracy" in m:
                    accs.append(float(m["accuracy"]))
                if "log_loss" in m:
                    lls.append(float(m["log_loss"]))
                if "brier_score" in m:
                    bss.append(float(m["brier_score"]))

        per_model[model_name] = {
            "mean_accuracy": round(float(np.nanmean(accs)), 6) if accs else None,
            "std_accuracy": round(float(np.nanstd(accs)), 6) if accs else None,
            "mean_log_loss": round(float(np.nanmean(lls)), 6) if lls else None,
            "std_log_loss": round(float(np.nanstd(lls)), 6) if lls else None,
            "mean_brier_score": round(float(np.nanmean(bss)), 6) if bss else None,
            "std_brier_score": round(float(np.nanstd(bss)), 6) if bss else None,
            "n_windows": len(accs),
        }

    ranking = sorted(
        per_model.items(),
        key=lambda kv: kv[1].get("mean_accuracy") or 0.0,
        reverse=True,
    )

    return {
        "per_model": per_model,
        "ranking_by_accuracy": [r[0] for r in ranking],
        "ranking_by_log_loss": sorted(
            per_model.keys(),
            key=lambda k: per_model[k].get("mean_log_loss") or float("inf"),
        ),
    }
