"""Build squad_ratings.csv from EA FC 26 player data + WC 2026 rosters.

Workflow
--------
1. For teams with a released WC roster (rosters.json):
   - Fuzzy-match each squad player against FC26 players of the same nationality.
   - For unmatched players (domestic leagues not in FC26) estimate rating from
     the matched players' mean.
2. For teams whose roster is not yet released:
   - Use ALL FC26 players of that nationality (proxy for squad depth/quality).
3. Write data/processed/squad_ratings.csv with columns:
   team, squad_avg_rating, top_player_rating, attack_rating, defense_rating, gk_rating

Re-run this script any time rosters.json is updated to refresh the CSV:
    python scripts/build_squad_ratings_fc26.py --fc26 data/raw/fc26_players.csv

Requirements: rapidfuzz  (pip install rapidfuzz)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
ROSTERS_PATH = REPO_ROOT / "frontend/src/lib/rosters.json"
OUTPUT_PATH = REPO_ROOT / "fifa-2026-predictor/data/processed/squad_ratings.csv"
DEFAULT_FC26_PATH = REPO_ROOT / "fifa-2026-predictor/data/raw/fc26_players.csv"

# ---------------------------------------------------------------------------
# Nationality name mapping: rosters.json team name  →  FC26 nationality_name
# ---------------------------------------------------------------------------
NATIONALITY_MAP: dict[str, str] = {
    "IR Iran": "Iran",
    "Turkey": "Türkiye",
    "DR Congo": "Congo DR",
    "Cape Verde Islands": "Cabo Verde",
    "Curaçao": "Curacao",
    "USA": "United States",
    "Korea Republic": "Korea Republic",  # same — explicit for clarity
}

# ---------------------------------------------------------------------------
# Position categories (using FC26's player_positions first token)
# ---------------------------------------------------------------------------
ATTACK_POS = {"ST", "CF", "LW", "RW", "CAM", "LM", "RM", "SS"}
DEFENSE_POS = {"CB", "LB", "RB", "LWB", "RWB", "CDM", "WB"}
GK_POS = {"GK"}
# CM, LAM, RAM, etc. are counted toward both squad/attack avg but not defense

_DEFAULT_RATING = 68.0


def _primary_position(positions_str: str) -> str:
    """Return the first listed position, e.g. 'ST, CAM' → 'ST'."""
    return positions_str.split(",")[0].strip().upper()


def _mean(values: list[float], fallback: float) -> float:
    return round(sum(values) / len(values), 1) if values else fallback


def build_ratings(
    fc26_df: pd.DataFrame,
    rosters: dict,
    fuzzy_threshold: int = 75,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Returns a DataFrame with squad ratings for every WC team.

    Parameters
    ----------
    fc26_df : DataFrame with at least: long_name, short_name, nationality_name,
              overall, player_positions
    rosters : dict loaded from rosters.json
    fuzzy_threshold : minimum rapidfuzz score to accept a name match (0-100)
    verbose : print a summary table
    """
    # Pre-group FC26 by nationality for O(1) lookup
    fc26_by_nation: dict[str, pd.DataFrame] = {
        nation: grp.reset_index(drop=True)
        for nation, grp in fc26_df.groupby("nationality_name")
    }

    rows = []
    unmatched_report: dict[str, list[str]] = {}

    for wc_team, roster_data in sorted(rosters.items()):
        fc26_nation = NATIONALITY_MAP.get(wc_team, wc_team)
        nation_df = fc26_by_nation.get(fc26_nation, pd.DataFrame())

        released = roster_data.get("released", True)

        if nation_df.empty and released:
            print(
                f"  WARNING: no FC26 players found for '{wc_team}' "
                f"(looked up as '{fc26_nation}'). Add to NATIONALITY_MAP if needed.",
                file=sys.stderr,
            )

        if not released or nation_df.empty:
            # ── No released roster OR nation has no FC26 players ──────────
            if nation_df.empty:
                avg = _DEFAULT_RATING
                top = avg + 8.0
                atk = avg + 1.0
                dfn = avg - 1.0
                gk = avg
                unmatched_report[wc_team] = ["(no FC26 data — using default estimate)"]
            else:
                # Not released: use the top 26 FC26 players by overall as a
                # proxy WC squad. Using all players (e.g. Spain has 1,036)
                # drags the average down with low-rated domestic players who
                # would never make a WC squad.
                pool = (
                    nation_df
                    .sort_values("overall", ascending=False)
                    .head(26)
                    .reset_index(drop=True)
                )
                overalls = pool["overall"].tolist()
                avg = _mean(overalls, _DEFAULT_RATING)
                top = float(pool["overall"].max())
                pos_col = pool["player_positions"].apply(_primary_position)
                atk = _mean(pool.loc[pos_col.isin(ATTACK_POS), "overall"].tolist(), avg)
                dfn = _mean(pool.loc[pos_col.isin(DEFENSE_POS), "overall"].tolist(), avg)
                gk_ = pool.loc[pos_col.isin(GK_POS), "overall"].tolist()
                gk = _mean(gk_, avg)
                unmatched_report[wc_team] = []
        else:
            # ── Released roster: fuzzy-match squad players to FC26 ────────
            # Collect all roster player names
            squad_names: list[tuple[str, str]] = []  # (name, position_group)
            for pos_group, key in [
                ("GK", "goalkeepers"),
                ("DEF", "defenders"),
                ("MID", "midfielders"),
                ("ATT", "forwards"),
            ]:
                for p in roster_data.get(key, []):
                    squad_names.append((p["name"], pos_group))

            # Build candidate list from FC26.
            # WRatio handles multi-word names and non-ASCII characters well.
            fc26_names_long = nation_df["long_name"].tolist()
            fc26_names_short = nation_df["short_name"].tolist()

            matched_overalls: list[float] = []
            matched_atk: list[float] = []
            matched_dfn: list[float] = []
            matched_gk: list[float] = []
            unmatched_names: list[str] = []

            for player_name, pos_group in squad_names:
                # Match against long_name and short_name; take the best score.
                best_long = process.extractOne(
                    player_name, fc26_names_long,
                    scorer=fuzz.WRatio,
                )
                best_short = process.extractOne(
                    player_name, fc26_names_short,
                    scorer=fuzz.WRatio,
                )

                best = None
                if best_long and best_short:
                    if best_long[1] >= best_short[1]:
                        best = (best_long[0], best_long[1], best_long[2])
                    else:
                        best = (best_short[0], best_short[1], best_short[2])
                elif best_long:
                    best = (best_long[0], best_long[1], best_long[2])
                elif best_short:
                    best = (best_short[0], best_short[1], best_short[2])

                if best and best[1] >= fuzzy_threshold:
                    idx = best[2]
                    overall = float(nation_df.loc[idx, "overall"])
                    matched_overalls.append(overall)
                    if pos_group == "GK":
                        matched_gk.append(overall)
                    elif pos_group == "DEF":
                        matched_dfn.append(overall)
                    else:  # MID / ATT
                        matched_atk.append(overall)
                else:
                    unmatched_names.append(player_name)

            unmatched_report[wc_team] = unmatched_names

            # Estimate unmatched players using matched mean (or rank fallback)
            matched_mean = _mean(matched_overalls, _DEFAULT_RATING)
            unmatched_estimate = matched_mean

            # Include unmatched estimates in overall avg (improves accuracy for
            # small-coverage nations like Iran where most squad plays domestically)
            all_overalls = matched_overalls + [unmatched_estimate] * len(unmatched_names)

            avg = _mean(all_overalls, _DEFAULT_RATING)
            top = max(matched_overalls) if matched_overalls else matched_mean
            atk = _mean(matched_atk, avg)
            dfn = _mean(matched_dfn, avg)
            gk = _mean(matched_gk, avg)

        rows.append({
            "team": wc_team,
            "squad_avg_rating": round(avg, 1),
            "top_player_rating": round(top, 1),
            "attack_rating": round(atk, 1),
            "defense_rating": round(dfn, 1),
            "gk_rating": round(gk, 1),
        })

    df = pd.DataFrame(rows)

    if verbose:
        _print_summary(df, unmatched_report, rosters)

    return df


def _print_summary(
    df: pd.DataFrame,
    unmatched_report: dict[str, list[str]],
    rosters: dict,
) -> None:
    print("\n" + "=" * 72)
    print("Squad Ratings Summary (EA FC 26)")
    print("=" * 72)
    print(f"{'Team':<28} {'Avg':>5} {'Top':>5} {'Atk':>5} {'Def':>5} {'GK':>5}  {'Unmatched'}")
    print("-" * 72)
    for _, row in df.sort_values("squad_avg_rating", ascending=False).iterrows():
        team = row["team"]
        released = rosters.get(team, {}).get("released", True)
        status = "" if released else " *"
        unmatched = unmatched_report.get(team, [])
        um_str = f"{len(unmatched)} players" if unmatched else "all matched"
        print(
            f"{team + status:<28} "
            f"{row['squad_avg_rating']:>5.1f} "
            f"{row['top_player_rating']:>5.1f} "
            f"{row['attack_rating']:>5.1f} "
            f"{row['defense_rating']:>5.1f} "
            f"{row['gk_rating']:>5.1f}  "
            f"{um_str}"
        )
    print("-" * 72)
    print("* = roster not yet released; using full FC26 nationality pool")

    # Highlight the Egypt vs Iran comparison
    egypt = df[df["team"] == "Egypt"]
    iran = df[df["team"].isin(["IR Iran", "Iran"])]
    norway = df[df["team"] == "Norway"]
    if not egypt.empty and not iran.empty:
        print(f"\nKey check — Egypt avg: {egypt['squad_avg_rating'].values[0]:.1f}  "
              f"| Iran avg: {iran['squad_avg_rating'].values[0]:.1f}")
    if not norway.empty:
        print(f"Key check — Norway avg: {norway['squad_avg_rating'].values[0]:.1f}  "
              f"top: {norway['top_player_rating'].values[0]:.1f}")

    total_unmatched = sum(
        len(v) for v in unmatched_report.values()
        if v != ["(no FC26 data — using rank estimate)"]
    )
    print(f"\nTotal unmatched roster players across all teams: {total_unmatched}")
    print("=" * 72 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build squad_ratings.csv from EA FC 26 data."
    )
    parser.add_argument(
        "--fc26",
        default=str(DEFAULT_FC26_PATH),
        help="Path to FC26 CSV (default: %(default)s)",
    )
    parser.add_argument(
        "--rosters",
        default=str(ROSTERS_PATH),
        help="Path to rosters.json (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_PATH),
        help="Output CSV path (default: %(default)s)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=75,
        help="Fuzzy match score threshold 0-100 (default: 75)",
    )
    args = parser.parse_args()

    fc26_path = Path(args.fc26)
    if not fc26_path.exists():
        print(f"ERROR: FC26 file not found: {fc26_path}", file=sys.stderr)
        print("Download 'EA FC 26 Players' from Kaggle and place it at that path.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading FC26 data from {fc26_path} ...")
    fc26_df = pd.read_csv(fc26_path, low_memory=False)
    fc26_df["overall"] = pd.to_numeric(fc26_df["overall"], errors="coerce")
    fc26_df = fc26_df.dropna(subset=["overall", "nationality_name", "long_name"])
    fc26_df["overall"] = fc26_df["overall"].astype(int)
    print(f"  {len(fc26_df):,} players loaded, {fc26_df['nationality_name'].nunique()} nations")

    print(f"Loading rosters from {args.rosters} ...")
    with open(args.rosters, encoding="utf-8") as f:
        rosters = json.load(f)
    released = sum(1 for d in rosters.values() if d.get("released", True))
    print(f"  {len(rosters)} teams, {released} with released rosters")

    df = build_ratings(fc26_df, rosters, fuzzy_threshold=args.threshold)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False, encoding="utf-8")
    print(f"Wrote {len(df)} team ratings to {output}")


if __name__ == "__main__":
    main()
