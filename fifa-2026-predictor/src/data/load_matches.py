"""Primary data ingestion entrypoint for match data."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.load_football_data_api import fetch_international_matches_from_api
from src.data.load_statsbomb import fetch_statsbomb_open_matches
from src.data.schema import normalize_team_name
from src.utils import PROJECT_ROOT, ensure_parent_dir, load_config

# Composite key used to detect duplicate matches across sources.
_DEDUP_KEY = ["date", "home_team", "away_team"]

_STAGE_LOOKUP_PATH = "data/raw/wc_stage_lookup.csv"


def _apply_stage_lookup(df: pd.DataFrame) -> pd.DataFrame:
    """Backfill tournament_stage from the WC stage lookup CSV where value is absent or 'Unknown'."""
    lookup_path = PROJECT_ROOT / _STAGE_LOOKUP_PATH
    if not lookup_path.exists():
        return df

    lookup = pd.read_csv(lookup_path, parse_dates=["date"])
    lookup = lookup.rename(columns={"tournament_stage": "_stage_lookup"})

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    merged = df.merge(lookup, on=["date", "home_team", "away_team"], how="left")

    needs_fill = df["tournament_stage"].isin(["Unknown", "unknown", ""]) | df["tournament_stage"].isna()
    df["tournament_stage"] = df["tournament_stage"].where(
        ~needs_fill, merged["_stage_lookup"].fillna(df["tournament_stage"])
    )
    return df


def load_local_matches(input_csv: str) -> pd.DataFrame:
    """Load local CSV into dataframe."""
    path = PROJECT_ROOT / input_csv
    if not path.exists():
        raise FileNotFoundError(f"Local match file not found: {path}")
    return pd.read_csv(path)


def save_processed_matches(df: pd.DataFrame, output_csv: str) -> None:
    """Persist minimally cleaned matches to processed storage."""
    output_path = PROJECT_ROOT / output_csv
    ensure_parent_dir(output_path)

    cleaned = df.copy()
    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    cleaned = cleaned.dropna(subset=["date", "home_team", "away_team", "home_score", "away_score"])
    cleaned["neutral"] = cleaned["neutral"].astype(str).str.lower().isin(["true", "1", "yes"])
    # Normalize team name aliases so CSVs persist canonical names.
    cleaned["home_team"] = cleaned["home_team"].map(normalize_team_name)
    cleaned["away_team"] = cleaned["away_team"].map(normalize_team_name)
    if "tournament_stage" not in cleaned.columns:
        cleaned["tournament_stage"] = "Unknown"
    cleaned = _apply_stage_lookup(cleaned)
    cleaned = cleaned.sort_values("date").reset_index(drop=True)

    # Dedup by canonical key after normalization so overlapping sources don't
    # inflate the training set or corrupt rolling Elo state.
    before = len(cleaned)
    cleaned = cleaned.drop_duplicates(subset=_DEDUP_KEY, keep="first")
    if len(cleaned) < before:
        print(f"load_matches: removed {before - len(cleaned):,} duplicate rows")

    cleaned.to_csv(output_path, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load football match data from legal sources.")
    parser.add_argument(
        "--source",
        choices=["local", "football-data", "statsbomb"],
        default="local",
        help="Data source backend.",
    )
    parser.add_argument("--input-csv", default="data/raw/demo_international_matches.csv")
    parser.add_argument("--output-csv", default="data/processed/matches_clean.csv")
    parser.add_argument("--date-from", default="2022-01-01")
    parser.add_argument("--date-to", default="2026-12-31")
    parser.add_argument("--competition-id", type=int, default=43)
    parser.add_argument("--season-id", type=int, default=106)
    return parser.parse_args()


def main() -> None:
    _ = load_config()
    args = parse_args()

    if args.source == "local":
        df = load_local_matches(args.input_csv)
    elif args.source == "football-data":
        temp_output = PROJECT_ROOT / "data/raw/football_data_api_matches.csv"
        df = fetch_international_matches_from_api(args.date_from, args.date_to, str(temp_output))
    else:
        temp_output = PROJECT_ROOT / "data/raw/statsbomb_open_matches.csv"
        df = fetch_statsbomb_open_matches(args.competition_id, args.season_id, str(temp_output))

    save_processed_matches(df, args.output_csv)
    print(f"Saved cleaned matches to: {PROJECT_ROOT / args.output_csv}")


if __name__ == "__main__":
    main()

