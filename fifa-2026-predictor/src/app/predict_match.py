"""CLI app to predict one match before kickoff."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy.stats import poisson

from src.features.competition_weights import COMPETITION_WEIGHTS, DEFAULT_COMPETITION_WEIGHT
from src.features.elo import EloConfig, expected_score, update_ratings
from src.models.common import TARGET_MAP
from src.utils import PROJECT_ROOT, load_config


def _rolling_mean(values: deque[int], default: float) -> float:
    return float(np.mean(values)) if values else default


def build_pre_match_row(
    history_df: pd.DataFrame,
    home_team: str,
    away_team: str,
    match_date: str,
    competition: str,
    neutral: bool,
    home_confederation: str,
    away_confederation: str,
    home_fifa_rank: int,
    away_fifa_rank: int,
    tournament_stage: str,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    """Build one leakage-safe feature row for a future fixture."""
    form_window = int(cfg["features"]["form_window"])
    elo_cfg = EloConfig(
        k_factor=float(cfg["features"]["elo_k_factor"]),
        home_advantage=float(cfg["features"]["elo_home_advantage"]),
    )

    history = history_df.copy()
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    history = history[history["date"] < pd.to_datetime(match_date)].sort_values("date")

    ratings = defaultdict(lambda: elo_cfg.base_rating)
    form_points = defaultdict(lambda: deque(maxlen=form_window))
    goals_for = defaultdict(lambda: deque(maxlen=form_window))
    goals_against = defaultdict(lambda: deque(maxlen=form_window))
    last_played = {}

    for row in history.itertuples(index=False):
        ht = str(row.home_team)
        at = str(row.away_team)
        date = pd.Timestamp(row.date)
        home_new, away_new = update_ratings(
            ratings[ht],
            ratings[at],
            int(row.home_score),
            int(row.away_score),
            bool(row.neutral),
            elo_cfg,
        )
        ratings[ht] = home_new
        ratings[at] = away_new

        hp = 3 if row.home_score > row.away_score else 1 if row.home_score == row.away_score else 0
        ap = 3 if row.home_score < row.away_score else 1 if row.home_score == row.away_score else 0
        form_points[ht].append(hp)
        form_points[at].append(ap)
        goals_for[ht].append(int(row.home_score))
        goals_for[at].append(int(row.away_score))
        goals_against[ht].append(int(row.away_score))
        goals_against[at].append(int(row.home_score))
        last_played[ht] = date
        last_played[at] = date

    d = pd.to_datetime(match_date)
    home_rest = (d - last_played[home_team]).days if home_team in last_played else 7
    away_rest = (d - last_played[away_team]).days if away_team in last_played else 7
    home_form = _rolling_mean(form_points[home_team], 1.5)
    away_form = _rolling_mean(form_points[away_team], 1.5)
    home_gf = _rolling_mean(goals_for[home_team], 1.0)
    away_gf = _rolling_mean(goals_for[away_team], 1.0)
    home_ga = _rolling_mean(goals_against[home_team], 1.0)
    away_ga = _rolling_mean(goals_against[away_team], 1.0)
    home_elo = float(ratings[home_team])
    away_elo = float(ratings[away_team])

    elo_adj = home_elo + (0.0 if neutral else elo_cfg.home_advantage)
    row = {
        "home_team": home_team,
        "away_team": away_team,
        "competition": competition,
        "neutral": int(neutral),
        "home_confederation": home_confederation,
        "away_confederation": away_confederation,
        "home_fifa_rank": home_fifa_rank,
        "away_fifa_rank": away_fifa_rank,
        "tournament_stage": tournament_stage,
        "home_form_last5": home_form,
        "away_form_last5": away_form,
        "home_goals_for_last5": home_gf,
        "away_goals_for_last5": away_gf,
        "home_goals_against_last5": home_ga,
        "away_goals_against_last5": away_ga,
        "home_rest_days": max(0, int(home_rest)),
        "away_rest_days": max(0, int(away_rest)),
        "home_elo_pre": home_elo,
        "away_elo_pre": away_elo,
        "elo_diff_home_away": home_elo - away_elo,
        "elo_win_prob": expected_score(elo_adj, away_elo),
        "form_diff_home_away": home_form - away_form,
        "goal_balance_diff": (home_gf - home_ga) - (away_gf - away_ga),
        "rank_diff": home_fifa_rank - away_fifa_rank,
        "competition_weight": COMPETITION_WEIGHTS.get(competition, DEFAULT_COMPETITION_WEIGHT),
        "is_same_confederation": int(home_confederation == away_confederation),
    }
    return pd.DataFrame([row])


def predict_scorelines(poisson_json: Path, top_n: int = 3) -> list[tuple[str, float]]:
    if not poisson_json.exists():
        return []
    params = json.loads(poisson_json.read_text(encoding="utf-8"))
    home_lambda = float(params["base_home_lambda"])
    away_lambda = float(params["base_away_lambda"])
    values: list[tuple[str, float]] = []
    for h in range(6):
        for a in range(6):
            p = float(poisson.pmf(h, home_lambda) * poisson.pmf(a, away_lambda))
            values.append((f"{h}-{a}", p))
    values.sort(key=lambda item: item[1], reverse=True)
    return values[:top_n]


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict one football match.")
    parser.add_argument("--model-path", default="src/models/artifacts/xgb.joblib")
    parser.add_argument("--history-csv", default="data/processed/matches_clean.csv")
    parser.add_argument("--home-team", required=True)
    parser.add_argument("--away-team", required=True)
    parser.add_argument("--match-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--competition", default="FIFA World Cup Qualification")
    parser.add_argument("--neutral", action="store_true")
    parser.add_argument("--home-confederation", default="UNKNOWN")
    parser.add_argument("--away-confederation", default="UNKNOWN")
    parser.add_argument("--home-fifa-rank", type=int, default=75)
    parser.add_argument("--away-fifa-rank", type=int, default=75)
    parser.add_argument("--tournament-stage", default="Unknown")
    parser.add_argument("--with-scorelines", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    history_path = PROJECT_ROOT / args.history_csv
    if not history_path.exists():
        raise FileNotFoundError(f"History CSV missing: {history_path}")

    history_df = pd.read_csv(history_path)
    model = joblib.load(PROJECT_ROOT / args.model_path)
    sample = build_pre_match_row(
        history_df=history_df,
        home_team=args.home_team,
        away_team=args.away_team,
        match_date=args.match_date,
        competition=args.competition,
        neutral=args.neutral,
        home_confederation=args.home_confederation,
        away_confederation=args.away_confederation,
        home_fifa_rank=args.home_fifa_rank,
        away_fifa_rank=args.away_fifa_rank,
        tournament_stage=args.tournament_stage,
        cfg=cfg,
    )

    clf = model.named_steps["classifier"]
    classes = clf.classes_
    probs = model.predict_proba(sample)[0]
    prob_by_class = {int(c): float(p) for c, p in zip(classes, probs)}
    result = {
        "home_team": args.home_team,
        "away_team": args.away_team,
        "match_date": args.match_date,
        "probabilities": {
            "away_win": prob_by_class.get(TARGET_MAP["A"], 0.0),
            "draw": prob_by_class.get(TARGET_MAP["D"], 0.0),
            "home_win": prob_by_class.get(TARGET_MAP["H"], 0.0),
        },
    }

    if args.with_scorelines:
        poisson_path = PROJECT_ROOT / "src/models/artifacts/poisson_params.json"
        result["top_scorelines"] = predict_scorelines(poisson_path, top_n=3)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

