"""Build pre-match features without leakage."""

from __future__ import annotations

import argparse
from typing import Any, Optional

import numpy as np
import pandas as pd

from src.data.schema import ensure_match_schema
from src.data.team_identity import CANONICAL_TEAMS
from src.features.elo import rank_to_starting_elo
from src.features.match_row_builder import build_match_row
from src.features.registry import get_registry
from src.features.state_tracker import TeamStateTracker
from src.utils import PROJECT_ROOT, ensure_parent_dir, load_config


def _result_label(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "H"
    if home_score < away_score:
        return "A"
    return "D"


def build_feature_table(
    matches: pd.DataFrame,
    cfg: dict[str, Any],
    *,
    rosters_df: Optional[pd.DataFrame] = None,
    ratings_df: Optional[pd.DataFrame] = None,
    injuries_df: Optional[pd.DataFrame] = None,
    lineups_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Convert ordered historical matches into supervised feature rows.

    Processes matches strictly in chronological order.  For each match the
    pre-match state snapshot is captured via build_match_row() before
    tracker.update() advances the rolling state.  This guarantees no leakage.

    Optional player data arguments (rosters_df, ratings_df, injuries_df,
    lineups_df) are passed to the feature registry's player_aggregate block
    when that block is enabled.  When all are None the pipeline runs exactly
    as before Phase 5.
    """
    default_fifa_rank = int(cfg["features"]["default_fifa_rank"])
    h2h_window = int(cfg["features"].get("h2h_window", 10))
    elo_inactivity_halflife = float(cfg["features"].get("elo_inactivity_halflife", 0.0))

    # Rename 'tournament' → 'competition' when results.csv is the source
    if "tournament" in matches.columns and "competition" not in matches.columns:
        matches = matches.rename(columns={"tournament": "competition"})

    # Normalize team aliases, fill optional defaults, coerce types — single
    # source of truth shared with the inference path.
    matches = ensure_match_schema(matches)
    matches = matches.dropna(subset=["date", "home_score", "away_score"])
    matches = matches.sort_values("date").reset_index(drop=True)

    team_elo_init = {
        name: rank_to_starting_elo(meta.get("fifa_rank_2025"))
        for name, meta in CANONICAL_TEAMS.items()
    }
    tracker = TeamStateTracker(cfg, team_elo_init=team_elo_init)
    rows: list[dict[str, Any]] = []

    for row in matches.itertuples(index=False):
        home_team = str(row.home_team)
        away_team = str(row.away_team)
        date = pd.Timestamp(row.date)
        neutral = bool(row.neutral)

        home_rank_raw = getattr(row, "home_fifa_rank", np.nan)
        away_rank_raw = getattr(row, "away_fifa_rank", np.nan)
        home_rank = int(home_rank_raw) if pd.notna(home_rank_raw) else default_fifa_rank
        away_rank = int(away_rank_raw) if pd.notna(away_rank_raw) else default_fifa_rank

        home_conf = str(getattr(row, "home_confederation", "UNKNOWN"))
        away_conf = str(getattr(row, "away_confederation", "UNKNOWN"))
        competition = str(row.competition)
        tournament_stage = str(getattr(row, "tournament_stage", "Unknown"))

        record = build_match_row(
            tracker=tracker,
            home_team=home_team,
            away_team=away_team,
            match_date=date,
            competition=competition,
            neutral=neutral,
            home_confederation=home_conf,
            away_confederation=away_conf,
            home_fifa_rank=home_rank,
            away_fifa_rank=away_rank,
            tournament_stage=tournament_stage,
            h2h_window=h2h_window,
            elo_inactivity_halflife=elo_inactivity_halflife,
        )
        # Registry: merge any extra features from enabled blocks.
        # The player_aggregate block is disabled by default; enabling it
        # requires populated player data passed in via the keyword arguments.
        registry = get_registry()
        if registry.enabled_blocks() != ["form", "elo", "tournament"]:
            context: dict[str, Any] = {
                "home_team": home_team,
                "away_team": away_team,
                "match_date": str(date.date()),
                "rosters_df": rosters_df,
                "ratings_df": ratings_df,
                "injuries_df": injuries_df,
                "lineups_df": lineups_df,
            }
            extra = registry.build_all(context)
            if extra:
                record.update(extra)

        record["home_score"] = int(row.home_score)
        record["away_score"] = int(row.away_score)
        record["target"] = _result_label(record["home_score"], record["away_score"])
        rows.append(record)

        # Issue #109/#111: augment neutral matches with home/away swapped so the
        # model learns that neutral ground is symmetric.  Half weight prevents
        # double-counting the same result.
        if neutral:
            aug = build_match_row(
                tracker=tracker,
                home_team=away_team,
                away_team=home_team,
                match_date=date,
                competition=competition,
                neutral=True,
                home_confederation=away_conf,
                away_confederation=home_conf,
                home_fifa_rank=away_rank,
                away_fifa_rank=home_rank,
                tournament_stage=tournament_stage,
                h2h_window=h2h_window,
                elo_inactivity_halflife=elo_inactivity_halflife,
            )
            aug["home_score"] = int(row.away_score)
            aug["away_score"] = int(row.home_score)
            aug_label = _result_label(int(row.away_score), int(row.home_score))
            aug["target"] = aug_label
            aug["match_weight"] = aug.get("match_weight", 1.0) * 0.5
            aug["stage_weight"] = aug.get("stage_weight", 1.0) * 0.5
            rows.append(aug)

        tracker.update(
            home_team=home_team,
            away_team=away_team,
            home_goals=int(row.home_score),
            away_goals=int(row.away_score),
            neutral=neutral,
            date=date,
            competition=competition,
        )

    result = pd.DataFrame(rows)

    # Time-decay sample weights: recent matches contribute more to training.
    # Weight = 2^(-(days_before_last_match / halflife)).  A match played at the
    # same date as the newest match gets weight 1.0; one played `halflife` days
    # earlier gets 0.5; one played 2*halflife days earlier gets 0.25, etc.
    halflife = float(cfg["features"].get("time_decay_halflife_days", 730))
    if len(result) > 0 and halflife > 0:
        reference = result["date"].max()
        days_ago = (reference - result["date"]).dt.days.clip(lower=0)
        result["match_weight"] = (2.0 ** (-days_ago / halflife)).round(6)
    else:
        result["match_weight"] = 1.0

    return result


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
