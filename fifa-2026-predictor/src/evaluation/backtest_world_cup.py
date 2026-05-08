"""Out-of-sample backtest on FIFA World Cup 2018 and 2022."""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from src.evaluation.baselines import XGBoostModel
from src.evaluation.metrics import compute_metrics
from src.models.common import TARGET_MAP, load_feature_data
from src.utils import load_config

INV_TARGET_MAP = {v: k for k, v in TARGET_MAP.items()}

TOURNAMENTS = [
    {"name": "WC2018", "cutoff": "2018-06-14", "year": 2018},
    {"name": "WC2022", "cutoff": "2022-11-20", "year": 2022},
]


def _per_sample_log_loss(y_true: np.ndarray, y_prob: np.ndarray) -> np.ndarray:
    eps = 1e-10
    return -np.log(np.clip(y_prob[np.arange(len(y_true)), y_true], eps, 1.0))


def backtest_tournament(df: pd.DataFrame, cfg: dict, tournament: dict) -> dict:
    cutoff = pd.Timestamp(tournament["cutoff"])
    year = tournament["year"]

    train_df = df[df["date"] < cutoff].copy().reset_index(drop=True)
    test_df = df[
        (df["competition"] == "FIFA World Cup")
        & (pd.to_datetime(df["date"]).dt.year == year)
    ].copy().reset_index(drop=True)

    if len(test_df) == 0:
        return {
            "name": tournament["name"],
            "error": (
                "no WC matches found — check that features.csv contains rows with "
                f"competition='FIFA World Cup' in year {year}"
            ),
        }

    model = XGBoostModel(cfg=cfg)
    model.fit(train_df)

    y_test = test_df["target"].map(TARGET_MAP).astype(int).values
    y_prob = model.predict_proba(test_df)
    overall = compute_metrics(y_test, y_prob, "xgboost")

    by_stage: dict = {}
    for stage, _ in test_df.groupby("tournament_stage"):
        mask = (test_df["tournament_stage"] == stage).values
        yt, yp = y_test[mask], y_prob[mask]
        if len(yt) < 2:
            continue
        m = compute_metrics(yt, yp, "xgboost")
        by_stage[str(stage)] = {"n": int(mask.sum()), "accuracy": m["accuracy"], "log_loss": m["log_loss"]}

    per_sample_ll = _per_sample_log_loss(y_test, y_prob)
    top10_idx = np.argsort(per_sample_ll)[::-1][:10]
    worst: list[dict] = []
    for i in top10_idx:
        row = test_df.iloc[int(i)]
        worst.append({
            "home_team": str(row.get("home_team", "?")),
            "away_team": str(row.get("away_team", "?")),
            "date": str(row["date"])[:10],
            "actual": INV_TARGET_MAP[int(y_test[i])],
            "p_home": round(float(y_prob[i, 2]), 3),
            "p_draw": round(float(y_prob[i, 1]), 3),
            "p_away": round(float(y_prob[i, 0]), 3),
            "loss": round(float(per_sample_ll[i]), 4),
        })

    return {
        "name": tournament["name"],
        "n_train": len(train_df),
        "n_test": len(test_df),
        "overall": {"accuracy": overall["accuracy"], "log_loss": overall["log_loss"]},
        "by_stage": by_stage,
        "worst_predictions": worst,
    }


def _print_result(result: dict) -> None:
    if "error" in result:
        print(f"\n{result['name']}: ERROR — {result['error']}")
        return
    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  {result['name']}  (train={result['n_train']}, test={result['n_test']})")
    print(sep)
    print(f"  Overall  accuracy={result['overall']['accuracy']:.3f}   log-loss={result['overall']['log_loss']:.3f}")
    if result["by_stage"]:
        print("\n  By tournament stage:")
        for stage, m in sorted(result["by_stage"].items()):
            print(f"    {stage:<30} n={m['n']:>3}  acc={m['accuracy']:.3f}  ll={m['log_loss']:.3f}")
    if result["worst_predictions"]:
        print("\n  Top-10 worst predictions:")
        hdr = f"    {'Home':<22} {'Away':<22} {'Act':>4} {'P(H)':>6} {'P(D)':>6} {'P(A)':>6} {'Loss':>7}"
        print(hdr)
        print("    " + "-" * (len(hdr) - 4))
        for w in result["worst_predictions"]:
            print(f"    {w['home_team']:<22} {w['away_team']:<22} {w['actual']:>4} {w['p_home']:>6.3f} {w['p_draw']:>6.3f} {w['p_away']:>6.3f} {w['loss']:>7.4f}")


def run_wc_backtest(features_csv: str = "data/processed/features.csv") -> list[dict]:
    cfg = load_config()
    df = load_feature_data(features_csv)
    results = []
    for tournament in TOURNAMENTS:
        print(f"\nRunning {tournament['name']} backtest (cutoff {tournament['cutoff']}) ...")
        result = backtest_tournament(df, cfg, tournament)
        _print_result(result)
        results.append(result)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Out-of-sample backtest on WC 2018 and WC 2022.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    args = parser.parse_args()
    run_wc_backtest(args.features_csv)


if __name__ == "__main__":
    main()
