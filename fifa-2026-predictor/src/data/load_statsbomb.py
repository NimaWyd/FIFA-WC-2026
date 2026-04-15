"""StatsBomb Open Data loader (legal, open-source dataset)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.utils import ensure_parent_dir

MATCHES_URL_TEMPLATE = (
    "https://raw.githubusercontent.com/statsbomb/open-data/master/data/matches/{competition_id}/{season_id}.json"
)


def fetch_statsbomb_open_matches(
    competition_id: int,
    season_id: int,
    output_csv: str,
) -> pd.DataFrame:
    """Download StatsBomb open matches and map them to a generic schema."""
    url = MATCHES_URL_TEMPLATE.format(competition_id=competition_id, season_id=season_id)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload: list[dict[str, Any]] = response.json()

    rows: list[dict[str, object]] = []
    for match in payload:
        home = match.get("home_team", {})
        away = match.get("away_team", {})
        comp = match.get("competition", {})
        rows.append(
            {
                "date": match.get("match_date"),
                "home_team": home.get("home_team_name"),
                "away_team": away.get("away_team_name"),
                "home_score": match.get("home_score"),
                "away_score": match.get("away_score"),
                "competition": comp.get("competition_name", "StatsBomb Open"),
                "neutral": False,
            }
        )

    df = pd.DataFrame(rows)
    output_path = Path(output_csv)
    ensure_parent_dir(output_path)
    df.to_csv(output_path, index=False)
    return df

