"""Prepare the open international football results CSV for this pipeline.

Works with both the auto-downloaded file (download_open_data.py) and a
manually downloaded Kaggle CSV (martj42/international_results).

Default start year is 1993 — the year FIFA rankings were introduced.  Going
back further adds Elo warm-up depth without meaningful pre-match metadata.

Usage:
    # After running download_open_data.py:
    python -m src.data.prepare_kaggle_data

    # Custom paths / year filter:
    python -m src.data.prepare_kaggle_data \\
        --input-csv data/raw/results.csv \\
        --output-csv data/raw/open_data_prepared.csv \\
        --from-year 1993

Deduplication key: (date, home_team, away_team) after canonical normalization.
FIFA ranks are a static mid-2025 snapshot used as a proxy for all years —
this is a documented limitation; historical ranks are not available in the
open dataset.
"""

from __future__ import annotations

import argparse

import pandas as pd

from src.data.team_identity import get_confederation, get_fifa_rank, resolve_team
from src.utils import PROJECT_ROOT, ensure_parent_dir

# ---------------------------------------------------------------------------
# Competition name mapping (martj42 tournament column → project names)
# ---------------------------------------------------------------------------
TOURNAMENT_MAP: dict[str, str] = {
    # World Cup
    "FIFA World Cup": "FIFA World Cup",
    "FIFA World Cup qualification": "FIFA World Cup Qualification",
    "FIFA World Cup Qualification": "FIFA World Cup Qualification",
    "FIFA World Cup qualification (CONCACAF)": "FIFA World Cup Qualification",
    "FIFA World Cup qualification (UEFA)": "FIFA World Cup Qualification",
    "FIFA World Cup qualification (CAF)": "FIFA World Cup Qualification",
    "FIFA World Cup qualification (AFC)": "FIFA World Cup Qualification",
    "FIFA World Cup qualification (CONMEBOL)": "FIFA World Cup Qualification",
    "FIFA World Cup qualification (OFC)": "FIFA World Cup Qualification",
    # UEFA
    "UEFA Euro": "UEFA Euro",
    "UEFA Euro qualification": "UEFA Euro Qualification",
    "UEFA Euro Qualification": "UEFA Euro Qualification",
    "UEFA Nations League": "UEFA Nations League",
    "UEFA Nations League A": "UEFA Nations League",
    "UEFA Nations League B": "UEFA Nations League",
    "UEFA Nations League C": "UEFA Nations League",
    "UEFA Nations League D": "UEFA Nations League",
    # CONMEBOL
    "Copa América": "Copa America",
    "Copa America": "Copa America",
    "Copa América qualification": "Copa America Qualification",
    # AFC
    "AFC Asian Cup": "AFC Asian Cup",
    "AFC Asian Cup qualification": "AFC Asian Cup Qualification",
    "AFC Asian Cup Qualification": "AFC Asian Cup Qualification",
    "AFC Challenge Cup": "AFC Challenge Cup",
    "AFC Challenge Cup qualification": "AFC Challenge Cup Qualification",
    "AFC Solidarity Cup": "AFC Solidarity Cup",
    "AFF Championship": "AFF Championship",
    "SAFF Championship": "SAFF Championship",
    # CAF
    "Africa Cup of Nations": "Africa Cup of Nations",
    "Africa Cup of Nations qualification": "Africa Cup of Nations Qualification",
    "Africa Cup of Nations Qualification": "Africa Cup of Nations Qualification",
    "African Cup of Nations": "Africa Cup of Nations",
    "African Cup of Nations qualification": "Africa Cup of Nations Qualification",
    "CECAFA Cup": "CECAFA Cup",
    "COSAFA Cup": "COSAFA Cup",
    "WAFU Cup of Nations": "WAFU Cup of Nations",
    "WAFU Cup": "WAFU Cup of Nations",
    # CONCACAF
    "CONCACAF Gold Cup": "CONCACAF Gold Cup",
    "CONCACAF Championship": "CONCACAF Gold Cup",
    "Gold Cup": "CONCACAF Gold Cup",
    "CONCACAF Nations League": "CONCACAF Nations League",
    "CONCACAF Nations League A": "CONCACAF Nations League",
    "CONCACAF Nations League B": "CONCACAF Nations League",
    "CONCACAF Nations League C": "CONCACAF Nations League",
    "CFU Caribbean Cup": "CFU Caribbean Cup",
    "Caribbean Cup": "CFU Caribbean Cup",
    # OFC
    "OFC Nations Cup": "OFC Nations Cup",
    "OFC Nations Cup qualification": "OFC Nations Cup Qualification",
    # Arab
    "Arab Cup": "Arab Cup",
    "Arabian Gulf Cup": "Arabian Gulf Cup",
    "Gulf Cup": "Arabian Gulf Cup",
    # Other regional
    "Intercontinental Cup": "Intercontinental Cup",
    "King's Cup": "King's Cup",
    "Copa Centroamericana": "CONCACAF Gold Cup",
    "CONCACAF Championship qualification": "CONCACAF Gold Cup Qualification",
    # Friendlies
    "Friendly": "International Friendly",
    "Friendlies": "International Friendly",
    "International Friendly": "International Friendly",
}

# Map raw tournament name → default tournament_stage label
STAGE_MAP: dict[str, str] = {
    "FIFA World Cup": "Group Stage",
    "UEFA Euro": "Group Stage",
    "Copa América": "Group Stage",
    "Copa America": "Group Stage",
    "AFC Asian Cup": "Group Stage",
    "Africa Cup of Nations": "Group Stage",
    "African Cup of Nations": "Group Stage",
    "CONCACAF Gold Cup": "Group Stage",
    "UEFA Nations League": "Group Stage",
    "CONCACAF Nations League": "Group Stage",
    "OFC Nations Cup": "Group Stage",
    "Friendly": "Unknown",
    "Friendlies": "Unknown",
    "International Friendly": "Unknown",
}

# WC 2026 confirmed / likely participants — used only for reporting
WC_2026_TEAMS = {
    "United States", "Canada", "Mexico",
    "Spain", "France", "England", "Germany", "Portugal", "Netherlands",
    "Belgium", "Italy", "Croatia", "Switzerland", "Denmark", "Austria",
    "Scotland", "Turkey", "Slovakia", "Poland", "Serbia", "Hungary",
    "Slovenia", "Albania", "Czechia", "Georgia", "Ukraine",
    "Argentina", "Brazil", "Colombia", "Uruguay", "Ecuador", "Venezuela",
    "Paraguay",
    "Morocco", "Senegal", "Nigeria", "Cameroon", "Egypt", "Côte d'Ivoire",
    "DR Congo", "Tunisia", "Ghana", "Algeria", "South Africa", "Mali",
    "Japan", "Korea Republic", "IR Iran", "Australia", "Saudi Arabia",
    "Iraq", "Jordan", "Uzbekistan",
    "Panama", "Honduras", "Costa Rica", "Jamaica",
    "New Zealand",
}


def _map_tournament(raw: str) -> str:
    raw = str(raw).strip()
    return TOURNAMENT_MAP.get(raw, raw)


def _map_stage(raw: str) -> str:
    raw = str(raw).strip()
    # First try exact match, then try mapping via the competition name
    if raw in STAGE_MAP:
        return STAGE_MAP[raw]
    competition = _map_tournament(raw)
    return STAGE_MAP.get(competition, "Unknown")


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
            alt = {"home_score": "home_goals", "away_score": "away_goals"}.get(col, col)
            if alt in df.columns:
                df[col] = df[alt]
    df = df.dropna(subset=["home_score", "away_score"])
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce").fillna(0).astype(int)
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce").fillna(0).astype(int)

    df = df[df["date"].dt.year >= from_year].copy()

    # Canonicalize team names via team_identity (covers all registered aliases)
    df["home_team"] = df["home_team"].map(resolve_team)
    df["away_team"] = df["away_team"].map(resolve_team)

    # Tournament / stage mapping
    tournament_col = "tournament" if "tournament" in df.columns else "competition"
    df["competition"] = df[tournament_col].map(_map_tournament)
    df["tournament_stage"] = df[tournament_col].map(_map_stage)

    # Confederations from canonical registry
    df["home_confederation"] = df["home_team"].map(get_confederation)
    df["away_confederation"] = df["away_team"].map(get_confederation)

    # FIFA ranks — static 2025 snapshot used as proxy for all years
    df["home_fifa_rank"] = df["home_team"].map(get_fifa_rank)
    df["away_fifa_rank"] = df["away_team"].map(get_fifa_rank)

    # Neutral venue
    if "neutral" in df.columns:
        df["neutral"] = df["neutral"].astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        df["neutral"] = False

    # Source provenance
    df["source"] = "martj42"

    keep = [
        "date", "home_team", "away_team", "home_score", "away_score",
        "competition", "neutral",
        "home_confederation", "away_confederation",
        "home_fifa_rank", "away_fifa_rank",
        "tournament_stage", "source",
    ]
    df = df[keep].sort_values("date").reset_index(drop=True)

    # Deduplication: canonical key is (date, home_team, away_team)
    before = len(df)
    df = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="first")
    after = len(df)
    if before > after:
        print(f"Removed {before - after:,} duplicate match rows (same date+teams)")

    df = df.sort_values("date").reset_index(drop=True)

    out = PROJECT_ROOT / output_csv
    ensure_parent_dir(out)
    df.to_csv(out, index=False)

    # Summary stats
    teams = set(df["home_team"]) | set(df["away_team"])
    wc_covered = WC_2026_TEAMS & teams
    wc_missing = WC_2026_TEAMS - teams
    conf_counts = df[["home_confederation"]].rename(
        columns={"home_confederation": "conf"}
    ).value_counts().to_dict()
    unknown_conf_teams = {
        t for t in teams
        if get_confederation(t) == "UNKNOWN"
    }

    print(f"\nSaved {len(df):,} matches ({from_year}-present) -> {out}")
    print(f"Unique teams:              {len(teams)}")
    print(f"Date range:                {df['date'].min().date()} – {df['date'].max().date()}")
    print(f"WC 2026 teams covered:     {len(wc_covered)} / {len(WC_2026_TEAMS)}")
    if wc_missing:
        print(f"WC 2026 teams missing:     {sorted(wc_missing)}")
    if unknown_conf_teams:
        sample = sorted(unknown_conf_teams)[:8]
        print(f"UNKNOWN confederation ({len(unknown_conf_teams)}): {sample}")

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare open international results CSV.")
    parser.add_argument("--input-csv", default="data/raw/results.csv")
    parser.add_argument("--output-csv", default="data/raw/open_data_prepared.csv")
    parser.add_argument(
        "--from-year", type=int, default=1993,
        help="Drop matches before this year (default 1993 — FIFA ranking era). "
             "Going further back adds Elo warm-up but pre-dates FIFA rankings.",
    )
    args = parser.parse_args()
    prepare(args.input_csv, args.output_csv, args.from_year)


if __name__ == "__main__":
    main()
