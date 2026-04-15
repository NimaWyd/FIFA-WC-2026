"""Build pre-match features without leakage."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.features.elo import EloConfig, update_ratings
from src.utils import PROJECT_ROOT, ensure_parent_dir, load_config


def _result_label(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "H"
    if home_score < away_score:
        return "A"
    return "D"


def build_feature_table(matches: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    """Convert ordered historical matches into supervised rows."""
    form_window = int(cfg["features"]["form_window"])
    elo_cfg = EloConfig(
        k_factor=float(cfg["features"]["elo_k_factor"]),
        home_advantage=float(cfg["features"]["elo_home_advantage"]),
    )
    default_fifa_rank = int(cfg["features"]["default_fifa_rank"])

    matches = matches.copy()
    matches["date"] = pd.to_datetime(matches["date"], errors="coerce")
    matches = matches.sort_values("date").reset_index(drop=True)

    ratings = defaultdict(lambda: elo_cfg.base_rating)
    form_points = defaultdict(lambda: deque(maxlen=form_window))
    goals_for = defaultdict(lambda: deque(maxlen=form_window))
    goals_against = defaultdict(lambda: deque(maxlen=form_window))
    last_played = {}

    rows: list[dict[str, Any]] = []
    for row in matches.itertuples(index=False):
        home_team = str(row.home_team)
        away_team = str(row.away_team)
        date = pd.Timestamp(row.date)
        neutral = bool(row.neutral)
        home_rank = getattr(row, "home_fifa_rank", np.nan)
        away_rank = getattr(row, "away_fifa_rank", np.nan)

        home_form = float(np.mean(form_points[home_team])) if form_points[home_team] else 1.5
        away_form = float(np.mean(form_points[away_team])) if form_points[away_team] else 1.5
        home_gf_roll = float(np.mean(goals_for[home_team])) if goals_for[home_team] else 1.0
        away_gf_roll = float(np.mean(goals_for[away_team])) if goals_for[away_team] else 1.0
        home_ga_roll = float(np.mean(goals_against[home_team])) if goals_against[home_team] else 1.0
        away_ga_roll = float(np.mean(goals_against[away_team])) if goals_against[away_team] else 1.0

        home_rest = (date - last_played[home_team]).days if home_team in last_played else 7
        away_rest = (date - last_played[away_team]).days if away_team in last_played else 7

        home_elo_pre = ratings[home_team]
        away_elo_pre = ratings[away_team]

        record = {
            "date": date,
            "home_team": home_team,
            "away_team": away_team,
            "competition": str(row.competition),
            "neutral": int(neutral),
            "home_confederation": getattr(row, "home_confederation", "UNKNOWN"),
            "away_confederation": getattr(row, "away_confederation", "UNKNOWN"),
            "home_fifa_rank": int(home_rank) if pd.notna(home_rank) else default_fifa_rank,
            "away_fifa_rank": int(away_rank) if pd.notna(away_rank) else default_fifa_rank,
            "tournament_stage": getattr(row, "tournament_stage", "Unknown"),
            "home_form_last5": home_form,
            "away_form_last5": away_form,
            "home_goals_for_last5": home_gf_roll,
            "away_goals_for_last5": away_gf_roll,
            "home_goals_against_last5": home_ga_roll,
            "away_goals_against_last5": away_ga_roll,
            "home_rest_days": max(0, int(home_rest)),
            "away_rest_days": max(0, int(away_rest)),
            "home_elo_pre": home_elo_pre,
            "away_elo_pre": away_elo_pre,
            "elo_diff_home_away": home_elo_pre - away_elo_pre,
            "form_diff_home_away": home_form - away_form,
            "goal_balance_diff": (home_gf_roll - home_ga_roll) - (away_gf_roll - away_ga_roll),
            "home_score": int(row.home_score),
            "away_score": int(row.away_score),
        }
        record["target"] = _result_label(record["home_score"], record["away_score"])
        rows.append(record)

        home_new, away_new = update_ratings(
            home_rating=home_elo_pre,
            away_rating=away_elo_pre,
            home_goals=int(row.home_score),
            away_goals=int(row.away_score),
            neutral=neutral,
            cfg=elo_cfg,
        )
        ratings[home_team] = home_new
        ratings[away_team] = away_new

        home_points = 3 if row.home_score > row.away_score else 1 if row.home_score == row.away_score else 0
        away_points = 3 if row.home_score < row.away_score else 1 if row.home_score == row.away_score else 0
        form_points[home_team].append(home_points)
        form_points[away_team].append(away_points)

        goals_for[home_team].append(int(row.home_score))
        goals_for[away_team].append(int(row.away_score))
        goals_against[home_team].append(int(row.away_score))
        goals_against[away_team].append(int(row.home_score))
        last_played[home_team] = date
        last_played[away_team] = date

    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build leakage-safe football features.")
    parser.add_argument("--input-csv", default="data/processed/matches_clean.csv")
    parser.add_argument("--output-csv", default="data/processed/features.csv")
    return parser.parse_args()


def main() -> None:
    cfg = load_config()
    args = parse_args()
    input_path = PROJECT_ROOT / args.input_csv
    output_path = PROJECT_ROOT / args.output_csv

    if not input_path.exists():
        raise FileNotFoundError(
            f"Missing cleaned matches file: {input_path}. "
            "Run src/data/load_matches.py first."
        )

    matches = pd.read_csv(input_path)
    features_df = build_feature_table(matches, cfg)
    ensure_parent_dir(output_path)
    features_df.to_csv(output_path, index=False)
    print(f"Saved feature table to: {output_path}")


if __name__ == "__main__":
    main()

