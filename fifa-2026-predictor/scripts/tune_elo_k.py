"""Grid-search Elo K-factor using Elo-only log-loss on the test set.

Runs entirely from matches_clean.csv — no model retraining needed.
For each candidate K, replays the full match history to build Elo ratings,
records elo_win_prob before each update, then measures log-loss and accuracy
on the last 20% of matches (chronological split, matching train_xgb.py).

Usage (from fifa-2026-predictor/ directory):
    python scripts/tune_elo_k.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.competition_weights import get_competition_k_multiplier
from src.features.elo import EloConfig, expected_score, goal_margin_multiplier, actual_score

# Match the config defaults
HOME_ADVANTAGE = 100.0
BASE_RATING = 1500.0
MIN_YEAR = 1993

K_GRID = [15, 20, 25, 30, 35, 40, 45, 50, 60, 75]
TEST_FRACTION = 0.20


def replay_elo(df: pd.DataFrame, k_factor: float) -> pd.DataFrame:
    """Replay all matches, recording elo_win_prob before each update."""
    cfg = EloConfig(k_factor=k_factor, home_advantage=HOME_ADVANTAGE, base_rating=BASE_RATING)
    ratings: dict[str, float] = {}

    results = []
    for row in df.itertuples(index=False):
        home, away = row.home_team, row.away_team
        h_elo = ratings.get(home, BASE_RATING)
        a_elo = ratings.get(away, BASE_RATING)
        neutral = bool(row.neutral)

        adj = h_elo + (0.0 if neutral else HOME_ADVANTAGE)
        win_prob = expected_score(adj, a_elo)

        comp_k_mult = get_competition_k_multiplier(getattr(row, "competition", "Unknown"))
        effective_k = k_factor * comp_k_mult
        mult = goal_margin_multiplier(int(row.home_score), int(row.away_score))
        act_home, act_away = actual_score(int(row.home_score), int(row.away_score))

        ratings[home] = h_elo + effective_k * mult * (act_home - expected_score(adj, a_elo))
        ratings[away] = a_elo + effective_k * mult * (act_away - (1.0 - expected_score(adj, a_elo)))

        results.append({"elo_win_prob": win_prob, "home_score": row.home_score, "away_score": row.away_score})

    return pd.DataFrame(results, index=df.index)


def evaluate(preds: pd.DataFrame, test_mask: pd.Series) -> dict[str, float]:
    """Compute log-loss and accuracy on the test slice."""
    sub = preds[test_mask].copy()
    # Binary outcome: 1 = home win, 0 = draw or away win
    binary = (sub["home_score"] > sub["away_score"]).astype(float)
    p = sub["elo_win_prob"].clip(1e-6, 1 - 1e-6).values
    y = binary.values

    logloss = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    # Accuracy: predict home win if prob > 0.5
    acc_binary = np.mean((p > 0.5) == y)
    # 3-class accuracy: map elo_win_prob → outcome (home if p>0.55, away if p<0.45, else draw)
    pred_outcome = np.where(p > 0.55, "H", np.where(p < 0.45, "A", "D"))
    true_outcome = np.where(sub["home_score"] > sub["away_score"], "H",
                            np.where(sub["home_score"] < sub["away_score"], "A", "D"))
    acc_3cls = np.mean(pred_outcome == true_outcome)
    return {"log_loss": logloss, "acc_binary": acc_binary, "acc_3cls": acc_3cls}


def main() -> None:
    data_path = Path(__file__).resolve().parents[1] / "data" / "processed" / "matches_clean.csv"
    print(f"Loading {data_path} ...")
    df = pd.read_csv(data_path, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"].dt.year >= MIN_YEAR].sort_values("date").reset_index(drop=True)
    print(f"  {len(df):,} matches (1993+)")

    # Test set = last TEST_FRACTION of rows (chronological)
    n = len(df)
    test_start = int(n * (1.0 - TEST_FRACTION))
    test_mask = pd.Series(False, index=df.index)
    test_mask.iloc[test_start:] = True
    print(f"  Test set: {test_mask.sum():,} matches from {df.loc[test_mask, 'date'].min().date()}\n")

    print(f"{'K':>6}  {'log-loss':>10}  {'acc-binary':>12}  {'acc-3cls':>10}")
    print("-" * 46)

    best_k, best_loss = None, float("inf")
    for k in K_GRID:
        preds = replay_elo(df, k)
        metrics = evaluate(preds, test_mask)
        marker = " <-- current" if k == 40.0 else ""
        print(f"{k:>6}  {metrics['log_loss']:>10.5f}  {metrics['acc_binary']:>12.4f}  {metrics['acc_3cls']:>10.4f}{marker}")
        if metrics["log_loss"] < best_loss:
            best_loss = metrics["log_loss"]
            best_k = k

    print(f"\nBest K = {best_k}  (log-loss {best_loss:.5f})")
    print("\nNote: this measures Elo-only prediction quality.")
    print("If best_k differs significantly from 40, update configs/config.yaml,")
    print("regenerate features.csv, and retrain the full model to confirm improvement.")


if __name__ == "__main__":
    main()
