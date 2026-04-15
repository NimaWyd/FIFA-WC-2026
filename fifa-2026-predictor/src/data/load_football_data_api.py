"""Legal adapter for football-data.org API."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from src.utils import ensure_parent_dir

BASE_URL = "https://api.football-data.org/v4"


def fetch_international_matches_from_api(
    date_from: str,
    date_to: str,
    output_csv: str,
) -> pd.DataFrame:
    """
    Fetch matches from football-data.org (if access plan allows).

    This is intentionally conservative and legal-first. Different API plans may
    provide different competition access levels.
    """
    load_dotenv()
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise RuntimeError("FOOTBALL_DATA_API_KEY is missing. Add it to your .env file.")

    headers = {"X-Auth-Token": api_key}
    params = {"dateFrom": date_from, "dateTo": date_to}
    endpoint = f"{BASE_URL}/matches"
    response = requests.get(endpoint, headers=headers, params=params, timeout=30)
    response.raise_for_status()

    payload = response.json().get("matches", [])
    records: list[dict[str, object]] = []
    for match in payload:
        score = match.get("score", {}).get("fullTime", {})
        records.append(
            {
                "date": str(match.get("utcDate", ""))[:10],
                "home_team": match.get("homeTeam", {}).get("name"),
                "away_team": match.get("awayTeam", {}).get("name"),
                "home_score": score.get("home"),
                "away_score": score.get("away"),
                "competition": match.get("competition", {}).get("name", "Unknown"),
                "neutral": False,  # Source may not consistently expose this.
            }
        )

    df = pd.DataFrame.from_records(records)
    output_path = Path(output_csv)
    ensure_parent_dir(output_path)
    df.to_csv(output_path, index=False)
    return df

