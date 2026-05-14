"""Seed data/processed/fifa_rankings.csv from the CANONICAL_TEAMS snapshot.

Run after each FIFA rankings release to keep predictions current:

    python -m src.data.seed_fifa_rankings

To update with manually downloaded rankings, edit the CSV directly — the file
format is two columns: team (canonical name), fifa_rank (integer).

get_fifa_rank() in team_identity.py prefers this CSV over the hardcoded
snapshot, so no code changes are needed when rankings shift.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.data.team_identity import CANONICAL_TEAMS
from src.utils import PROJECT_ROOT, ensure_parent_dir

DEFAULT_OUTPUT = PROJECT_ROOT / "data/processed/fifa_rankings.csv"


def generate_rankings() -> list[dict[str, object]]:
    """Return one row per team that has a known FIFA rank, sorted by rank."""
    rows = [
        {"team": team, "fifa_rank": meta["fifa_rank_2025"]}
        for team, meta in CANONICAL_TEAMS.items()
        if meta.get("fifa_rank_2025") is not None
    ]
    return sorted(rows, key=lambda r: r["fifa_rank"])


def write_rankings(rows: list[dict[str, object]], output: Path) -> None:
    ensure_parent_dir(output)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["team", "fifa_rank"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed FIFA rankings CSV from team_identity.py snapshot.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    output = Path(args.output)
    rows = generate_rankings()
    write_rankings(rows, output)
    print(f"Wrote {len(rows)} rankings to {output}")
    print(f"Top 10: {[r['team'] for r in rows[:10]]}")


if __name__ == "__main__":
    main()
