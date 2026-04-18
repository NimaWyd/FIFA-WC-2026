"""Prepare the open international football results CSV for this pipeline.

Works with both the auto-downloaded file (download_open_data.py) and a
manually downloaded Kaggle CSV.

Usage:
    # After running download_open_data.py:
    python -m src.data.prepare_kaggle_data

    # Custom paths / year filter:
    python -m src.data.prepare_kaggle_data \
        --input-csv data/raw/results.csv \
        --output-csv data/raw/open_data_prepared.csv \
        --from-year 2014
"""

from __future__ import annotations

import argparse

import pandas as pd

from src.data.confederation_lookup import lookup_confederation
from src.data.schema import normalize_team_name
from src.utils import PROJECT_ROOT, ensure_parent_dir

# ---------------------------------------------------------------------------
# Competition name mapping (Kaggle / martj42 → project names)
# ---------------------------------------------------------------------------
TOURNAMENT_MAP: dict[str, str] = {
    "FIFA World Cup": "FIFA World Cup",
    "FIFA World Cup qualification": "FIFA World Cup Qualification",
    "FIFA World Cup Qualification": "FIFA World Cup Qualification",
    "UEFA Euro": "UEFA Euro",
    "UEFA Euro qualification": "UEFA Euro Qualification",
    "Copa América": "Copa America",
    "AFC Asian Cup": "AFC Asian Cup",
    "AFC Asian Cup qualification": "AFC Asian Cup Qualification",
    "Africa Cup of Nations": "Africa Cup of Nations",
    "Africa Cup of Nations qualification": "Africa Cup of Nations Qualification",
    "CONCACAF Gold Cup": "CONCACAF Gold Cup",
    "CONCACAF Championship": "CONCACAF Gold Cup",
    "UEFA Nations League": "UEFA Nations League",
    "Friendly": "International Friendly",
    "Friendlies": "International Friendly",
}

STAGE_MAP: dict[str, str] = {
    "FIFA World Cup": "Group Stage",
    "UEFA Euro": "Group Stage",
    "Copa América": "Group Stage",
    "AFC Asian Cup": "Group Stage",
    "Africa Cup of Nations": "Group Stage",
    "CONCACAF Gold Cup": "Group Stage",
    "UEFA Nations League": "Group Stage",
    "Friendly": "Unknown",
    "Friendlies": "Unknown",
}

# ---------------------------------------------------------------------------
# Static FIFA World Rankings snapshot (approximate mid-2025)
# Update these if you want more accurate rank features.
# ---------------------------------------------------------------------------
FIFA_RANKINGS: dict[str, int] = {
    "Argentina": 1, "France": 2, "Spain": 3, "England": 4, "Brazil": 5,
    "Portugal": 6, "Belgium": 7, "Netherlands": 8, "Germany": 9, "Italy": 10,
    "Croatia": 11, "Morocco": 12, "United States": 13, "Colombia": 14,
    "Japan": 15, "Uruguay": 16, "Switzerland": 17, "Mexico": 18,
    "Senegal": 19, "Denmark": 20, "Ecuador": 21, "Austria": 22,
    "Serbia": 23, "Poland": 24, "Turkey": 25, "Korea Republic": 26,
    "Australia": 27, "Canada": 28, "Ukraine": 29, "Hungary": 30,
    "IR Iran": 31, "Scotland": 32, "Côte d'Ivoire": 33, "Czechia": 34,
    "Nigeria": 35, "Venezuela": 36, "Romania": 37, "Slovakia": 38,
    "Peru": 39, "Chile": 40, "South Africa": 41, "Egypt": 42,
    "Ghana": 43, "Algeria": 44, "Paraguay": 45, "Panama": 46,
    "Cameroon": 47, "Tunisia": 48, "Honduras": 49, "Costa Rica": 50,
    "Bolivia": 51, "Greece": 52, "Sweden": 53, "Norway": 54,
    "Albania": 55, "Mali": 56, "DR Congo": 57, "Burkina Faso": 58,
    "Slovenia": 59, "Jamaica": 60, "Iraq": 61, "Guinea": 62,
    "Saudi Arabia": 63, "Israel": 64, "Finland": 65, "Uzbekistan": 66,
    "Bosnia and Herzegovina": 67, "Iceland": 68, "Georgia": 69,
    "Cape Verde Islands": 70, "Jordan": 71, "New Zealand": 72,
    "Montenegro": 73, "North Macedonia": 74, "Armenia": 75,
    "Qatar": 76, "Oman": 77, "Benin": 78, "Zimbabwe": 79, "Congo": 80,
    "El Salvador": 81, "Cuba": 82, "Trinidad and Tobago": 83,
    "Mozambique": 84, "Rwanda": 85, "Libya": 86, "Zambia": 87,
    "Tanzania": 88, "Uganda": 89, "Comoros": 90, "Gambia": 91,
    "Ethiopia": 92, "Malawi": 93, "Afghanistan": 94, "India": 95,
    "Thailand": 96, "Vietnam": 97, "Indonesia": 98, "China": 99,
    "Philippines": 100,
}

# The 48 confirmed / likely WC 2026 teams (used to flag rows for enriched focus)
WC_2026_TEAMS = {
    # Hosts
    "United States", "Canada", "Mexico",
    # UEFA
    "Spain", "France", "England", "Germany", "Portugal", "Netherlands",
    "Belgium", "Italy", "Croatia", "Switzerland", "Denmark", "Austria",
    "Scotland", "Turkey", "Slovakia", "Poland", "Serbia", "Hungary",
    "Slovenia", "Albania", "Czechia", "Georgia", "Ukraine",
    # CONMEBOL
    "Argentina", "Brazil", "Colombia", "Uruguay", "Ecuador", "Venezuela",
    "Paraguay",
    # CAF
    "Morocco", "Senegal", "Nigeria", "Cameroon", "Egypt", "Côte d'Ivoire",
    "DR Congo", "Tunisia", "Ghana", "Algeria", "South Africa", "Mali",
    # AFC
    "Japan", "Korea Republic", "IR Iran", "Australia", "Saudi Arabia",
    "Iraq", "Jordan", "Uzbekistan",
    # CONCACAF (non-hosts)
    "Panama", "Honduras", "Costa Rica", "Jamaica",
    # OFC
    "New Zealand",
}


def lookup_fifa_rank(team: str, default: int = 75) -> int:
    return FIFA_RANKINGS.get(team, default)


def prepare(input_csv: str, output_csv: str, from_year: int) -> pd.DataFrame:
    path = PROJECT_ROOT / input_csv
    if not path.exists():
        raise FileNotFoundError(
            f"Input CSV not found: {path}\n"
            "Run first:  python -m src.data.download_open_data"
        )

    df = pd.read_csv(path, low_memory=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "home_team", "away_team"])

    # Score columns may be named differently across sources
    for col in ["home_score", "away_score"]:
        if col not in df.columns:
            # Try alternative Kaggle column names
            alt = {"home_score": "home_goals", "away_score": "away_goals"}.get(col, col)
            if alt in df.columns:
                df[col] = df[alt]
    df = df.dropna(subset=["home_score", "away_score"])
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce").fillna(0).astype(int)
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce").fillna(0).astype(int)

    df = df[df["date"].dt.year >= from_year].copy()

    # Normalise team names
    df["home_team"] = df["home_team"].map(normalize_team_name)
    df["away_team"] = df["away_team"].map(normalize_team_name)

    # Tournament column may be "tournament" (martj42) or "competition"
    tournament_col = "tournament" if "tournament" in df.columns else "competition"
    df["competition"] = df[tournament_col].map(
        lambda t: TOURNAMENT_MAP.get(str(t).strip(), str(t).strip())
    )
    df["tournament_stage"] = df[tournament_col].map(
        lambda t: STAGE_MAP.get(str(t).strip(), "Unknown")
    )

    # Confederations from lookup table
    df["home_confederation"] = df["home_team"].map(lookup_confederation)
    df["away_confederation"] = df["away_team"].map(lookup_confederation)

    # FIFA ranks from static snapshot
    df["home_fifa_rank"] = df["home_team"].map(lookup_fifa_rank)
    df["away_fifa_rank"] = df["away_team"].map(lookup_fifa_rank)

    # Neutral
    if "neutral" in df.columns:
        df["neutral"] = df["neutral"].astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        df["neutral"] = False

    keep = [
        "date", "home_team", "away_team", "home_score", "away_score",
        "competition", "neutral",
        "home_confederation", "away_confederation",
        "home_fifa_rank", "away_fifa_rank",
        "tournament_stage",
    ]
    df = df[keep].sort_values("date").reset_index(drop=True)

    out = PROJECT_ROOT / output_csv
    ensure_parent_dir(out)
    df.to_csv(out, index=False)

    # Summary stats
    teams = set(df["home_team"]) | set(df["away_team"])
    wc_covered = WC_2026_TEAMS & teams
    wc_missing = WC_2026_TEAMS - teams
    conf_map = (
        pd.concat([
            df[["home_team", "home_confederation"]].rename(columns={"home_team": "team", "home_confederation": "conf"}),
            df[["away_team", "away_confederation"]].rename(columns={"away_team": "team", "away_confederation": "conf"}),
        ])
        .drop_duplicates(subset=["team"], keep="last")
        .set_index("team")["conf"]
        .to_dict()
    )
    unknown_conf = {t for t in teams if conf_map.get(t) == "UNKNOWN"}

    print(f"\nSaved {len(df):,} matches ({from_year}-present) -> {out}")
    print(f"Unique teams:              {len(teams)}")
    print(f"WC 2026 teams covered:     {len(wc_covered)} / {len(WC_2026_TEAMS)}")
    if wc_missing:
        print(f"WC 2026 teams missing:     {sorted(wc_missing)}")
    if unknown_conf:
        print(f"UNKNOWN confederation ({len(unknown_conf)}): {sorted(unknown_conf)[:8]}")

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare open international results CSV.")
    parser.add_argument("--input-csv", default="data/raw/results.csv")
    parser.add_argument("--output-csv", default="data/raw/open_data_prepared.csv")
    parser.add_argument(
        "--from-year", type=int, default=2010,
        help="Drop matches before this year (default 2010). "
             "Going back further adds Elo stability but dilutes recent signal.",
    )
    args = parser.parse_args()
    prepare(args.input_csv, args.output_csv, args.from_year)


if __name__ == "__main__":
    main()
