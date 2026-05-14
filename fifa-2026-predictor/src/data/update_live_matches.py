"""Live match result fetcher — appends new results to matches_clean.csv.

Usage (CLI):
    python -m src.data.update_live_matches
    python -m src.data.update_live_matches --date-from 2026-06-01 --output data/processed/matches_clean.csv

Requires FOOTBALL_DATA_API_KEY in .env.
"""
from __future__ import annotations

import argparse
import logging
import os
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from src.data.load_football_data_api import fetch_international_matches_from_api
from src.data.team_identity import resolve_team
from src.utils import PROJECT_ROOT

log = logging.getLogger(__name__)

DEFAULT_OUTPUT = PROJECT_ROOT / "data/processed/matches_clean.csv"
FALLBACK_DATE = "2020-01-01"


def get_last_update_date(matches_csv: Path) -> str:
    """Return the most recent match date in the CSV, or FALLBACK_DATE if absent."""
    if not matches_csv.exists():
        return FALLBACK_DATE
    try:
        df = pd.read_csv(matches_csv, usecols=["date"])
    except (ValueError, KeyError) as exc:
        log.warning("Could not read date column from %s: %s — using fallback.", matches_csv, exc)
        return FALLBACK_DATE
    if df.empty:
        return FALLBACK_DATE
    max_date = pd.to_datetime(df["date"], errors="coerce").max()
    if pd.isna(max_date):
        return FALLBACK_DATE
    return str(max_date.date())


def fetch_and_append_new_results(
    output_csv: Path = DEFAULT_OUTPUT,
    date_from: str | None = None,
    date_to: str | None = None,
) -> int:
    """Fetch completed international results and append new ones to output_csv.

    Returns the count of new rows added.
    """
    auto_detected = date_from is None
    if date_from is None:
        date_from = get_last_update_date(output_csv)
    if date_to is None:
        date_to = str(date.today())

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        temp_path = f.name

    log.info("Fetching results from %s to %s", date_from, date_to)
    try:
        new_df = fetch_international_matches_from_api(date_from, date_to, temp_path)
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    # Only keep completed matches (both scores present)
    new_df = new_df.dropna(subset=["home_score", "away_score"])
    # Strict > only when auto-detected (to skip the boundary match already in CSV).
    # When caller passes date_from explicitly, include the boundary (>=).
    if auto_detected:
        new_df = new_df[new_df["date"] > date_from].copy()
    else:
        new_df = new_df[new_df["date"] >= date_from].copy()

    if new_df.empty:
        log.info("No new completed matches found.")
        return 0

    # Resolve team names to canonical (must happen BEFORE dedup so canonical
    # names in new_df match the canonical names stored in the existing CSV)
    for col in ("home_team", "away_team"):
        new_df[col] = new_df[col].apply(
            lambda x: resolve_team(str(x)) if pd.notna(x) else x
        )

    # Deduplicate against existing CSV
    if output_csv.exists():
        existing_df = pd.read_csv(output_csv, usecols=["date", "home_team", "away_team"])
        existing_keys = set(
            zip(existing_df["date"], existing_df["home_team"], existing_df["away_team"])
        )
        new_df = new_df[
            ~new_df.apply(
                lambda r: (r["date"], r["home_team"], r["away_team"]) in existing_keys,
                axis=1,
            )
        ]

    if new_df.empty:
        log.info("All fetched matches already present — nothing to append.")
        return 0

    header = not output_csv.exists()
    new_df.to_csv(output_csv, mode="a", header=header, index=False)
    log.info("Appended %d new matches to %s", len(new_df), output_csv)
    return len(new_df)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and append new match results.")
    parser.add_argument("--date-from", default=None, help="YYYY-MM-DD (default: max date in CSV)")
    parser.add_argument("--date-to", default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to matches_clean.csv")
    args = parser.parse_args()

    n = fetch_and_append_new_results(
        output_csv=Path(args.output),
        date_from=args.date_from,
        date_to=args.date_to,
    )
    print(f"Done. {n} new matches added.")


if __name__ == "__main__":
    main()
