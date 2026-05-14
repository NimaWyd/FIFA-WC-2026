"""Generate squad-level FIFA ratings from team_identity.py FIFA rank data.

Writes data/processed/squad_ratings.csv. Ratings are proxied from FIFA
rankings using a linear formula — higher rank → lower rating.

Run:
    python -m src.data.seed_squad_ratings
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.team_identity import CANONICAL_TEAMS
from src.utils import PROJECT_ROOT, ensure_parent_dir

DEFAULT_OUTPUT = PROJECT_ROOT / "data/processed/squad_ratings.csv"

SQUAD_RATING_COLUMNS = [
    "team",
    "squad_avg_rating",
    "top_player_rating",
    "attack_rating",
    "defense_rating",
    "gk_rating",
]

_DEFAULT_RATING = 68.0
_DEFAULT_TOP_PLAYER = 74.0

# Rank 1 → 85.0, rank 100 → 57.2, floor at 56.0
_BASE = 85.0
_SLOPE = 0.28
_FLOOR = 56.0


def _rating_from_rank(rank: int | None) -> float:
    if rank is None:
        return _DEFAULT_RATING
    return round(max(_FLOOR, _BASE - (rank - 1) * _SLOPE), 1)


def generate_squad_ratings() -> pd.DataFrame:
    """Return a DataFrame with one row per canonical team."""
    rows = []
    for team, meta in CANONICAL_TEAMS.items():
        rank = meta.get("fifa_rank_2025")
        avg = _rating_from_rank(rank)
        rows.append({
            "team": team,
            "squad_avg_rating": avg,
            "top_player_rating": round(min(99.0, avg + 8.0), 1),
            "attack_rating": round(avg + 1.0, 1),
            "defense_rating": round(avg - 1.0, 1),
            "gk_rating": round(avg, 1),
        })
    return pd.DataFrame(rows, columns=SQUAD_RATING_COLUMNS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed squad ratings from FIFA rank data.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    output = Path(args.output)
    ensure_parent_dir(output)
    df = generate_squad_ratings()
    df.to_csv(output, index=False)
    print(f"Wrote {len(df)} team ratings to {output}")
    print(df.describe())


if __name__ == "__main__":
    main()
