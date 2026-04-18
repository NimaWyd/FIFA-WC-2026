"""Build team-level reference table from historical matches."""

from __future__ import annotations

import argparse

import pandas as pd

from src.data.schema import ensure_team_schema
from src.utils import PROJECT_ROOT, ensure_parent_dir


def build_team_table(matches_csv: str, output_csv: str) -> pd.DataFrame:
    """Build a canonical team metadata table from a cleaned matches CSV.

    Handles missing confederation and FIFA rank columns gracefully — any
    absent optional column is filled with safe schema defaults rather than
    raising a KeyError.
    """
    matches = pd.read_csv(PROJECT_ROOT / matches_csv)

    # Build column maps for home and away sides, including only columns that
    # actually exist in the file.
    home_rename = {"home_team": "team"}
    away_rename = {"away_team": "team"}
    if "home_confederation" in matches.columns:
        home_rename["home_confederation"] = "confederation"
    if "away_confederation" in matches.columns:
        away_rename["away_confederation"] = "confederation"
    if "home_fifa_rank" in matches.columns:
        home_rename["home_fifa_rank"] = "fifa_rank"
    if "away_fifa_rank" in matches.columns:
        away_rename["away_fifa_rank"] = "fifa_rank"

    home = matches[list(home_rename.keys())].rename(columns=home_rename)
    away = matches[list(away_rename.keys())].rename(columns=away_rename)

    teams = pd.concat([home, away], ignore_index=True)
    teams = teams.dropna(subset=["team"]).drop_duplicates(subset=["team"], keep="last")
    teams = teams.sort_values("team").reset_index(drop=True)

    # Apply schema defaults and normalization (fills confederation / fifa_rank
    # if still absent, normalises team name aliases).
    teams = ensure_team_schema(teams)

    out = PROJECT_ROOT / output_csv
    ensure_parent_dir(out)
    teams.to_csv(out, index=False)
    return teams


def main() -> None:
    parser = argparse.ArgumentParser(description="Build team-level table.")
    parser.add_argument("--matches-csv", default="data/processed/matches_clean.csv")
    parser.add_argument("--output-csv", default="data/processed/teams.csv")
    args = parser.parse_args()
    df = build_team_table(args.matches_csv, args.output_csv)
    print(f"Saved {len(df)} teams to {PROJECT_ROOT / args.output_csv}")


if __name__ == "__main__":
    main()
