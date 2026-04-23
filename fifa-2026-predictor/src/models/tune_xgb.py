"""Time-aware XGBoost hyperparameter tuning (Issue 4).

Uses the rolling-origin backtest framework for validation — no random
cross-validation, no test-set contamination.

Tuning is run on the train+val portion only (first 1-test_size of the data).
The held-out test set is never touched during search.

Usage
-----
    python -m src.models.tune_xgb
    python -m src.models.tune_xgb --n-trials 50
    python -m src.models.tune_xgb --features-csv data/processed/features.csv
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.backtest import rolling_windows, _recompute_weights
from src.models.common import (
    TARGET_MAP,
    build_preprocessor,
    load_feature_data,
    make_chronological_split,
    to_xy,
)
from src.utils import PROJECT_ROOT, load_config

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    _OPTUNA_AVAILABLE = True
except ImportError:
    _OPTUNA_AVAILABLE = False


def _evaluate_params(
    params: dict[str, Any],
    tune_df: pd.DataFrame,
    cfg: dict,
    n_windows: int = 3,
    halflife_days: float = 730.0,
) -> float:
    """Run rolling-origin backtest with given XGBoost params; return mean log-loss."""
    from xgboost import XGBClassifier

    windows = rolling_windows(tune_df, min_train_frac=0.65, n_windows=n_windows)
    if not windows:
        return float("inf")

    log_losses: list[float] = []
    for train_df_raw, test_df, _ in windows:
        train_df = _recompute_weights(train_df_raw, halflife_days=halflife_days)

        preprocessor, feature_cols = build_preprocessor(train_df)
        X_train, y_train = to_xy(train_df, feature_cols)
        X_test, y_test = to_xy(test_df, feature_cols)
        weights = (
            train_df["match_weight"].values if "match_weight" in train_df.columns else None
        )

        clf = XGBClassifier(
            n_estimators=int(params.get("n_estimators", 300)),
            learning_rate=float(params.get("learning_rate", 0.05)),
            max_depth=int(params.get("max_depth", 3)),
            subsample=float(params.get("subsample", 0.8)),
            colsample_bytree=float(params.get("colsample_bytree", 0.8)),
            min_child_weight=int(params.get("min_child_weight", 2)),
            gamma=float(params.get("gamma", 0.1)),
            reg_alpha=float(params.get("reg_alpha", 0.1)),
            reg_lambda=float(params.get("reg_lambda", 1.0)),
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            random_state=int(cfg.get("project", {}).get("random_state", 42)),
        )

        preprocessor.fit(X_train)
        X_train_t = preprocessor.transform(X_train)
        X_test_t = preprocessor.transform(X_test)

        fit_kwargs: dict = {"verbose": False}
        if weights is not None:
            fit_kwargs["sample_weight"] = weights
        clf.fit(X_train_t, y_train, **fit_kwargs)

        y_prob = clf.predict_proba(X_test_t)
        # Clip for numerical safety
        y_prob = np.clip(y_prob, 1e-10, 1 - 1e-10)
        y_prob /= y_prob.sum(axis=1, keepdims=True)

        from sklearn.metrics import log_loss
        ll = log_loss(y_test, y_prob, labels=[0, 1, 2])
        log_losses.append(ll)

    return float(np.mean(log_losses)) if log_losses else float("inf")


def _optuna_search(
    tune_df: pd.DataFrame,
    cfg: dict,
    n_trials: int,
    n_windows: int,
    halflife_days: float,
) -> tuple[dict, float]:
    """Run Optuna TPE search. Returns (best_params, best_score)."""

    def objective(trial: "optuna.Trial") -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 600, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 6),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0.0, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 2.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 5.0),
        }
        return _evaluate_params(params, tune_df, cfg, n_windows=n_windows,
                                halflife_days=halflife_days)

    study = optuna.create_study(direction="minimize")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    return study.best_params, study.best_value


def _random_search(
    tune_df: pd.DataFrame,
    cfg: dict,
    n_trials: int,
    n_windows: int,
    halflife_days: float,
    rng: np.random.Generator,
) -> tuple[dict, float]:
    """Randomised grid search fallback when Optuna is not installed."""
    search_space: list[dict] = []
    for _ in range(n_trials):
        search_space.append({
            "n_estimators": int(rng.choice([100, 150, 200, 300, 400, 500])),
            "learning_rate": float(rng.choice([0.01, 0.02, 0.05, 0.1, 0.15, 0.2])),
            "max_depth": int(rng.choice([2, 3, 4, 5])),
            "subsample": float(rng.choice([0.6, 0.7, 0.8, 0.9, 1.0])),
            "colsample_bytree": float(rng.choice([0.6, 0.7, 0.8, 0.9, 1.0])),
            "min_child_weight": int(rng.choice([1, 2, 3, 5])),
            "gamma": float(rng.choice([0.0, 0.05, 0.1, 0.2, 0.5])),
            "reg_alpha": float(rng.choice([0.0, 0.05, 0.1, 0.5, 1.0])),
            "reg_lambda": float(rng.choice([0.5, 1.0, 1.5, 2.0, 3.0])),
        })

    best_params: dict = search_space[0]
    best_score = float("inf")
    for i, params in enumerate(search_space):
        score = _evaluate_params(params, tune_df, cfg, n_windows=n_windows,
                                  halflife_days=halflife_days)
        print(f"  trial {i+1}/{n_trials}: ll={score:.4f}  params={params}")
        if score < best_score:
            best_score = score
            best_params = params

    return best_params, best_score


def run_tuning(
    features_csv: str = "data/processed/features.csv",
    n_trials: int = 40,
    n_windows: int = 3,
    output_json: str = "reports/xgb_tuning_results.json",
) -> dict:
    """Run time-aware hyperparameter tuning and save results.

    Tuning uses only the train+val portion (first 85% of data) so the
    test set is never contaminated.
    """
    cfg = load_config()
    halflife_days = float(cfg["features"].get("time_decay_halflife_days", 730))
    random_state = int(cfg["project"].get("random_state", 42))

    df = load_feature_data(features_csv)
    print(f"Loaded {len(df)} rows  ({df['date'].min().date()} – {df['date'].max().date()})")

    # Exclude the held-out test set from tuning entirely
    test_size = float(cfg["model"]["test_size"])
    tune_cutoff = int(len(df) * (1.0 - test_size))
    tune_df = df.iloc[:tune_cutoff].copy()
    test_df = df.iloc[tune_cutoff:].copy()
    print(f"Tuning on {len(tune_df)} rows | test reserved: {len(test_df)} rows (untouched)")

    default_params = {k: v for k, v in cfg["model"]["xgb"].items()
                      if k != "early_stopping_rounds"}

    print(f"\nBaseline log-loss (default params) …")
    baseline_score = _evaluate_params(default_params, tune_df, cfg,
                                       n_windows=n_windows, halflife_days=halflife_days)
    print(f"  baseline mean log-loss: {baseline_score:.4f}")

    if _OPTUNA_AVAILABLE:
        print(f"\nRunning Optuna TPE search ({n_trials} trials) …")
        best_params, best_score = _optuna_search(
            tune_df, cfg, n_trials=n_trials, n_windows=n_windows,
            halflife_days=halflife_days,
        )
        search_method = "optuna_tpe"
    else:
        print(f"\nOptuna not found — using random search ({n_trials} trials) …")
        rng = np.random.default_rng(random_state)
        best_params, best_score = _random_search(
            tune_df, cfg, n_trials=n_trials, n_windows=n_windows,
            halflife_days=halflife_days, rng=rng,
        )
        search_method = "random_search"

    improvement = baseline_score - best_score
    print(f"\nBest log-loss : {best_score:.4f}  (Δ {improvement:+.4f} vs baseline)")
    print(f"Best params   : {best_params}")

    results = {
        "search_method": search_method,
        "n_trials": n_trials,
        "n_backtest_windows": n_windows,
        "features_csv": features_csv,
        "tune_rows": len(tune_df),
        "baseline_log_loss": round(baseline_score, 6),
        "best_log_loss": round(best_score, 6),
        "improvement": round(improvement, 6),
        "default_params": default_params,
        "best_params": best_params,
        "optuna_available": _OPTUNA_AVAILABLE,
    }

    out_path = PROJECT_ROOT / output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved tuning results to: {out_path}")
    return results


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Time-aware XGBoost hyperparameter tuning.")
    p.add_argument("--features-csv", default="data/processed/features.csv")
    p.add_argument("--n-trials", type=int, default=40,
                   help="Number of search trials (default 40).")
    p.add_argument("--n-windows", type=int, default=3,
                   help="Rolling-origin windows used during each trial evaluation.")
    p.add_argument("--output-json", default="reports/xgb_tuning_results.json")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    run_tuning(
        features_csv=args.features_csv,
        n_trials=args.n_trials,
        n_windows=args.n_windows,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    main()
