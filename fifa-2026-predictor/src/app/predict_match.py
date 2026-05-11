"""CLI app to predict one match before kickoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

import joblib
import pandas as pd

from src.data.schema import ensure_match_schema, normalize_team_name
from src.data.team_identity import CANONICAL_TEAMS
from src.features.elo import rank_to_starting_elo
from src.features.match_row_builder import build_match_row
from src.features.registry import get_registry
from src.features.state_tracker import TeamStateTracker
from src.models.common import TARGET_MAP
from src.models.scoreline_model import TeamDependentScoreModel
from src.utils import PROJECT_ROOT, load_config


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
    *,
    rosters_df: Optional[pd.DataFrame] = None,
    ratings_df: Optional[pd.DataFrame] = None,
    injuries_df: Optional[pd.DataFrame] = None,
    lineups_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Build one leakage-safe feature row for a future fixture.

    Replays all history strictly before *match_date* through TeamStateTracker
    to derive consistent Elo, form, goals and rest-day features — the same
    logic used during training via build_features.py.

    Optional player data keyword arguments are forwarded to the feature
    registry's player_aggregate block when it is enabled.
    """
    # Normalize aliases so tracker state aligns with any canonical name the
    # caller passes — e.g. history "USA" and caller "United States" must match.
    history = ensure_match_schema(history_df)
    history = history[history["date"] < pd.to_datetime(match_date)].sort_values("date")

    team_elo_init = {
        name: rank_to_starting_elo(meta.get("fifa_rank_2025"))
        for name, meta in CANONICAL_TEAMS.items()
    }
    tracker = TeamStateTracker(cfg, team_elo_init=team_elo_init)
    tracker.replay_history(history)

    record = build_match_row(
        tracker=tracker,
        home_team=home_team,
        away_team=away_team,
        match_date=pd.to_datetime(match_date),
        competition=competition,
        neutral=neutral,
        home_confederation=home_confederation,
        away_confederation=away_confederation,
        home_fifa_rank=home_fifa_rank,
        away_fifa_rank=away_fifa_rank,
        tournament_stage=tournament_stage,
        elo_inactivity_halflife=float(cfg["features"].get("elo_inactivity_halflife", 0.0)),
    )

    # Registry: merge any extra features from enabled blocks (e.g. player_aggregate).
    registry = get_registry()
    if registry.enabled_blocks() != ["form", "elo", "tournament"]:
        context: dict[str, Any] = {
            "home_team": home_team,
            "away_team": away_team,
            "match_date": match_date,
            "rosters_df": rosters_df,
            "ratings_df": ratings_df,
            "injuries_df": injuries_df,
            "lineups_df": lineups_df,
        }
        extra = registry.build_all(context)
        if extra:
            record.update(extra)

    return pd.DataFrame([record])


def predict_scorelines(
    scoreline_params_path: Path,
    feature_row: pd.DataFrame,
    top_n: int = 3,
    outcome_probs: Optional[dict[str, float]] = None,
) -> list[tuple[str, float]]:
    """Return top scoreline probabilities using the team-dependent model.

    When *outcome_probs* (home_win, draw, away_win) are supplied the Poisson
    lambdas are calibrated so that integrating over the distribution reproduces
    those probabilities — keeping scorelines and win-probability consistent.
    """
    if not scoreline_params_path.exists():
        return []
    model = TeamDependentScoreModel.load(scoreline_params_path)
    row = feature_row.iloc[0].to_dict()
    lh_raw, la_raw = model.predict_lambdas_from_row(row)
    if outcome_probs is not None:
        lh, la = TeamDependentScoreModel.calibrate_lambdas_to_outcomes(
            outcome_probs["home_win"],
            outcome_probs["draw"],
            outcome_probs["away_win"],
            lambda_home_init=lh_raw,
            lambda_away_init=la_raw,
        )
    else:
        lh, la = lh_raw, la_raw
    return TeamDependentScoreModel.top_scorelines(lh, la, top_n=top_n)


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

    # Normalise team names so aliases resolve to canonical form
    home_team = normalize_team_name(args.home_team)
    away_team = normalize_team_name(args.away_team)

    history_path = PROJECT_ROOT / args.history_csv
    if not history_path.exists():
        raise FileNotFoundError(f"History CSV missing: {history_path}")

    history_df = pd.read_csv(history_path)
    model = joblib.load(PROJECT_ROOT / args.model_path)
    sample = build_pre_match_row(
        history_df=history_df,
        home_team=home_team,
        away_team=away_team,
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
    result: dict[str, Any] = {
        "home_team": home_team,
        "away_team": away_team,
        "match_date": args.match_date,
        "probabilities": {
            "away_win": prob_by_class.get(TARGET_MAP["A"], 0.0),
            "draw": prob_by_class.get(TARGET_MAP["D"], 0.0),
            "home_win": prob_by_class.get(TARGET_MAP["H"], 0.0),
        },
    }

    if args.with_scorelines:
        scoreline_path = PROJECT_ROOT / "src/models/artifacts/scoreline_params.json"
        scorelines = predict_scorelines(
            scoreline_path, sample, top_n=3, outcome_probs=result["probabilities"]
        )
        result["top_scorelines"] = scorelines

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
