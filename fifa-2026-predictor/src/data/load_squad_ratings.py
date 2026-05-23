"""Load squad ratings CSV into a lookup dict for use at inference time."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils import PROJECT_ROOT

DEFAULT_PATH = PROJECT_ROOT / "data/processed/squad_ratings.csv"

_REQUIRED_COLS = {
    "team", "squad_avg_rating", "top_player_rating",
    "attack_rating", "defense_rating", "gk_rating",
}


def load_squad_ratings(path: Path = DEFAULT_PATH) -> dict[str, dict[str, float]]:
    """Return {team_name: {feature: value}} from the squad ratings CSV.

    Returns an empty dict when the file is absent or schema is wrong.
    build_match_row skips squad features when this returns empty.
    """
    if not path.exists():
        return {}
    df = pd.read_csv(path, encoding="utf-8")
    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        return {}
    return {
        row["team"]: {
            "squad_avg_rating": float(row["squad_avg_rating"]),
            "top_player_rating": float(row["top_player_rating"]),
            "attack_rating": float(row["attack_rating"]),
            "defense_rating": float(row["defense_rating"]),
            "gk_rating": float(row["gk_rating"]),
        }
        for _, row in df.iterrows()
    }
