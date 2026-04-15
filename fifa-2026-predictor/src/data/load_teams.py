"""Build team-level reference table from historical matches."""

from __future__ import annotations

import argparse

import pandas as pd

from src.utils import PROJECT_ROOT, ensure_parent_dir


def build_team_table(matches_csv: str, output_csv: str) -> pd.DataFrame:
    matches = pd.read_csv(PROJECT_ROOT / matches_csv)

    home = matches[
        ["home_team", "home_confederation", "home_fifa_rank"]
    ].rename(
        columns={
            "home_team": "team",
            "home_confederation": "confederation",
            "home_fifa_rank": "fifa_rank",
        }
    )
    away = matches[
        ["away_team", "away_confederation", "away_fifa_rank"]
    ].rename(
        columns={
            "away_team": "team",
            "away_confederation": "confederation",
            "away_fifa_rank": "fifa_rank",
        }
    )
    teams = pd.concat([home, away], ignore_index=True)
    teams = teams.dropna(subset=["team"]).drop_duplicates(subset=["team"], keep="last")
    teams = teams.sort_values("team").reset_index(drop=True)

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

