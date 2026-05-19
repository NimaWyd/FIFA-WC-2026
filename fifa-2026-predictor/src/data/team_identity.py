"""Canonical team identity — single source of truth across all pipeline sources.

Canonical display names follow FIFA convention.
Aliases map any raw source variant to the canonical display name.
Confederation and 2025 FIFA rank are co-located here so there is one place to update.

Usage:
    from src.data.team_identity import resolve_team, get_confederation, get_fifa_rank

    resolve_team("USA")          # → "United States"
    resolve_team("South Korea")  # → "Korea Republic"
    resolve_team("Unknown FC")   # → "Unknown FC"  (safe passthrough)
    get_confederation("IR Iran") # → "AFC"
    get_fifa_rank("France")      # → 2
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Live rankings cache — loaded once from fifa_rankings.csv when it exists.
# get_fifa_rank() checks this first so rankings can be updated without code
# changes (issue #74). Falls back to hardcoded fifa_rank_2025 values.
# ---------------------------------------------------------------------------

_RANKINGS_CSV = Path(__file__).resolve().parents[2] / "data/processed/fifa_rankings.csv"
_rankings_cache: dict[str, int] | None = None


def _load_rankings_cache() -> dict[str, int]:
    global _rankings_cache
    if _rankings_cache is not None:
        return _rankings_cache
    if _RANKINGS_CSV.exists():
        try:
            with _RANKINGS_CSV.open(newline="", encoding="utf-8") as f:
                _rankings_cache = {
                    row["team"]: int(row["fifa_rank"])
                    for row in csv.DictReader(f)
                    if row.get("team") and row.get("fifa_rank")
                }
            return _rankings_cache
        except Exception:
            pass
    _rankings_cache = {}
    return _rankings_cache

# ---------------------------------------------------------------------------
# Master team registry
# canonical display name → {confederation, fifa_rank_2025, aliases}
# ---------------------------------------------------------------------------
# fifa_rank_2025: approximate mid-2025 FIFA World Ranking; None for unranked.
# aliases: list of all known raw-source variants for this team.

CANONICAL_TEAMS: dict[str, dict] = {

    # =========================================================================
    # UEFA (55 members + Kosovo associate)
    # =========================================================================
    "Albania": {"confederation": "UEFA", "fifa_rank_2025": 55, "aliases": []},
    "Andorra": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Armenia": {"confederation": "UEFA", "fifa_rank_2025": 75, "aliases": []},
    "Austria": {"confederation": "UEFA", "fifa_rank_2025": 22, "aliases": []},
    "Azerbaijan": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Belarus": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Belgium": {"confederation": "UEFA", "fifa_rank_2025": 8, "aliases": []},
    "Bosnia and Herzegovina": {
        "confederation": "UEFA", "fifa_rank_2025": 67,
        "aliases": ["Bosnia", "Bosnia & Herzegovina", "Bosnia-Herzegovina",
                    "Bosnia Herzegovina", "BiH"],
    },
    "Bulgaria": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Croatia": {"confederation": "UEFA", "fifa_rank_2025": 11, "aliases": ["Hrvatska"]},
    "Cyprus": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Czechia": {
        "confederation": "UEFA", "fifa_rank_2025": 34,
        "aliases": ["Czech Republic", "Czechoslovakia"],
    },
    "Denmark": {"confederation": "UEFA", "fifa_rank_2025": 20, "aliases": []},
    "England": {"confederation": "UEFA", "fifa_rank_2025": 4, "aliases": []},
    "Estonia": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Faroe Islands": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": ["Faeroe Islands"]},
    "Finland": {"confederation": "UEFA", "fifa_rank_2025": 65, "aliases": []},
    "France": {"confederation": "UEFA", "fifa_rank_2025": 2, "aliases": []},
    "Georgia": {"confederation": "UEFA", "fifa_rank_2025": 69, "aliases": []},
    "Germany": {
        "confederation": "UEFA", "fifa_rank_2025": 10,
        "aliases": ["West Germany", "Deutschland"],
    },
    "Gibraltar": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Greece": {"confederation": "UEFA", "fifa_rank_2025": 52, "aliases": []},
    "Hungary": {"confederation": "UEFA", "fifa_rank_2025": 30, "aliases": []},
    "Iceland": {"confederation": "UEFA", "fifa_rank_2025": 68, "aliases": []},
    "Ireland": {
        "confederation": "UEFA", "fifa_rank_2025": None,
        "aliases": ["Republic of Ireland"],
    },
    "Israel": {"confederation": "UEFA", "fifa_rank_2025": 64, "aliases": []},
    "Italy": {"confederation": "UEFA", "fifa_rank_2025": 9, "aliases": []},
    "Kazakhstan": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Kosovo": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Latvia": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Liechtenstein": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Lithuania": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Luxembourg": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Malta": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Moldova": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Montenegro": {"confederation": "UEFA", "fifa_rank_2025": 73, "aliases": []},
    "Netherlands": {"confederation": "UEFA", "fifa_rank_2025": 7, "aliases": ["Holland"]},
    "North Macedonia": {
        "confederation": "UEFA", "fifa_rank_2025": 74,
        "aliases": ["Macedonia", "FYROM", "FYR Macedonia", "North Macedonia (FYROM)"],
    },
    "Northern Ireland": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Norway": {"confederation": "UEFA", "fifa_rank_2025": 54, "aliases": []},
    "Poland": {"confederation": "UEFA", "fifa_rank_2025": 24, "aliases": []},
    "Portugal": {"confederation": "UEFA", "fifa_rank_2025": 6, "aliases": []},
    "Romania": {"confederation": "UEFA", "fifa_rank_2025": 37, "aliases": []},
    "Russia": {
        "confederation": "UEFA", "fifa_rank_2025": None,
        "aliases": ["Soviet Union", "CIS", "Russian Federation"],
    },
    "San Marino": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},
    "Scotland": {"confederation": "UEFA", "fifa_rank_2025": 32, "aliases": []},
    "Serbia": {
        "confederation": "UEFA", "fifa_rank_2025": 23,
        "aliases": ["Yugoslavia", "Serbia and Montenegro", "FR Yugoslavia",
                    "Federal Republic of Yugoslavia", "Serbia & Montenegro"],
    },
    "Slovakia": {"confederation": "UEFA", "fifa_rank_2025": 38, "aliases": []},
    "Slovenia": {"confederation": "UEFA", "fifa_rank_2025": 59, "aliases": []},
    "Spain": {"confederation": "UEFA", "fifa_rank_2025": 3, "aliases": []},
    "Sweden": {"confederation": "UEFA", "fifa_rank_2025": 53, "aliases": []},
    "Switzerland": {"confederation": "UEFA", "fifa_rank_2025": 17, "aliases": ["Swiss"]},
    "Turkey": {
        "confederation": "UEFA", "fifa_rank_2025": 40,
        "aliases": ["Türkiye", "Turkiye"],
    },
    "Ukraine": {"confederation": "UEFA", "fifa_rank_2025": 29, "aliases": []},
    "Wales": {"confederation": "UEFA", "fifa_rank_2025": None, "aliases": []},

    # =========================================================================
    # CONMEBOL (10 members)
    # =========================================================================
    "Argentina": {"confederation": "CONMEBOL", "fifa_rank_2025": 1, "aliases": []},
    "Bolivia": {"confederation": "CONMEBOL", "fifa_rank_2025": 51, "aliases": []},
    "Brazil": {"confederation": "CONMEBOL", "fifa_rank_2025": 5, "aliases": ["Brasil"]},
    "Chile": {"confederation": "CONMEBOL", "fifa_rank_2025": 40, "aliases": []},
    "Colombia": {"confederation": "CONMEBOL", "fifa_rank_2025": 14, "aliases": []},
    "Ecuador": {"confederation": "CONMEBOL", "fifa_rank_2025": 21, "aliases": []},
    "Paraguay": {"confederation": "CONMEBOL", "fifa_rank_2025": 45, "aliases": []},
    "Peru": {"confederation": "CONMEBOL", "fifa_rank_2025": 39, "aliases": []},
    "Uruguay": {"confederation": "CONMEBOL", "fifa_rank_2025": 12, "aliases": []},
    "Venezuela": {"confederation": "CONMEBOL", "fifa_rank_2025": 36, "aliases": []},

    # =========================================================================
    # CONCACAF (41 members)
    # =========================================================================
    "Antigua and Barbuda": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": ["Antigua & Barbuda"]},
    "Aruba": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Bahamas": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Barbados": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Belize": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Bermuda": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Canada": {"confederation": "CONCACAF", "fifa_rank_2025": 28, "aliases": []},
    "Cayman Islands": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Costa Rica": {"confederation": "CONCACAF", "fifa_rank_2025": 50, "aliases": []},
    "Cuba": {"confederation": "CONCACAF", "fifa_rank_2025": 82, "aliases": []},
    "Curaçao": {
        "confederation": "CONCACAF", "fifa_rank_2025": None,
        "aliases": ["Curacao", "Curaçao"],
    },
    "Dominican Republic": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "El Salvador": {"confederation": "CONCACAF", "fifa_rank_2025": 81, "aliases": []},
    "Grenada": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Guatemala": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Guyana": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Haiti": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Honduras": {"confederation": "CONCACAF", "fifa_rank_2025": 49, "aliases": []},
    "Jamaica": {"confederation": "CONCACAF", "fifa_rank_2025": 60, "aliases": []},
    "Mexico": {"confederation": "CONCACAF", "fifa_rank_2025": 18, "aliases": []},
    "Nicaragua": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Panama": {"confederation": "CONCACAF", "fifa_rank_2025": 46, "aliases": []},
    "Puerto Rico": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Saint Kitts and Nevis": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": ["St. Kitts and Nevis", "St Kitts and Nevis"]},
    "Saint Lucia": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": ["St. Lucia", "St Lucia"]},
    "Saint Vincent and the Grenadines": {
        "confederation": "CONCACAF", "fifa_rank_2025": None,
        "aliases": ["St. Vincent and the Grenadines", "St Vincent and the Grenadines",
                    "St. Vincent & the Grenadines"],
    },
    "Suriname": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": []},
    "Trinidad and Tobago": {
        "confederation": "CONCACAF", "fifa_rank_2025": 83,
        "aliases": ["Trinidad & Tobago", "T&T"],
    },
    "United States": {
        "confederation": "CONCACAF", "fifa_rank_2025": 16,
        "aliases": ["USA", "US", "United States of America", "U.S.A.", "U.S.",
                    "United States Men's National Team", "USMNT"],
    },
    "US Virgin Islands": {"confederation": "CONCACAF", "fifa_rank_2025": None, "aliases": ["U.S. Virgin Islands"]},

    # =========================================================================
    # CAF (54 members)
    # =========================================================================
    "Algeria": {"confederation": "CAF", "fifa_rank_2025": 44, "aliases": []},
    "Angola": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Benin": {"confederation": "CAF", "fifa_rank_2025": 78, "aliases": []},
    "Botswana": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Burkina Faso": {
        "confederation": "CAF", "fifa_rank_2025": 58,
        "aliases": ["Upper Volta"],
    },
    "Burundi": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Cameroon": {"confederation": "CAF", "fifa_rank_2025": 47, "aliases": []},
    "Cape Verde Islands": {
        "confederation": "CAF", "fifa_rank_2025": 70,
        "aliases": ["Cape Verde", "Cabo Verde"],
    },
    "Central African Republic": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": ["CAR"]},
    "Chad": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Comoros": {"confederation": "CAF", "fifa_rank_2025": 90, "aliases": []},
    "Congo": {"confederation": "CAF", "fifa_rank_2025": 80, "aliases": ["Republic of the Congo", "Congo Republic"]},
    "DR Congo": {
        "confederation": "CAF", "fifa_rank_2025": 57,
        "aliases": ["Congo DR", "Congo, DR", "Zaire", "DRC", "Democratic Republic of Congo",
                    "Democratic Republic of the Congo"],
    },
    "Djibouti": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Egypt": {"confederation": "CAF", "fifa_rank_2025": 42, "aliases": []},
    "Equatorial Guinea": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Eritrea": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Eswatini": {
        "confederation": "CAF", "fifa_rank_2025": None,
        "aliases": ["Swaziland"],
    },
    "Ethiopia": {"confederation": "CAF", "fifa_rank_2025": 92, "aliases": []},
    "Gabon": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Gambia": {"confederation": "CAF", "fifa_rank_2025": 91, "aliases": ["The Gambia"]},
    "Ghana": {"confederation": "CAF", "fifa_rank_2025": 43, "aliases": []},
    "Guinea": {"confederation": "CAF", "fifa_rank_2025": 62, "aliases": []},
    "Guinea-Bissau": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Côte d'Ivoire": {
        "confederation": "CAF", "fifa_rank_2025": 33,
        "aliases": ["Ivory Coast", "Cote d'Ivoire", "Cote d Ivoire",
                    "Côte d Ivoire", "Ivory Coast"],
    },
    "Kenya": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Lesotho": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Liberia": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Libya": {"confederation": "CAF", "fifa_rank_2025": 86, "aliases": []},
    "Madagascar": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Malawi": {"confederation": "CAF", "fifa_rank_2025": 93, "aliases": []},
    "Mali": {"confederation": "CAF", "fifa_rank_2025": 56, "aliases": []},
    "Mauritania": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Mauritius": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Morocco": {"confederation": "CAF", "fifa_rank_2025": 13, "aliases": []},
    "Mozambique": {"confederation": "CAF", "fifa_rank_2025": 84, "aliases": []},
    "Namibia": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Niger": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Nigeria": {"confederation": "CAF", "fifa_rank_2025": 35, "aliases": []},
    "Rwanda": {"confederation": "CAF", "fifa_rank_2025": 85, "aliases": []},
    "São Tomé and Príncipe": {
        "confederation": "CAF", "fifa_rank_2025": None,
        "aliases": ["Sao Tome and Principe", "São Tomé e Príncipe"],
    },
    "Senegal": {"confederation": "CAF", "fifa_rank_2025": 20, "aliases": []},
    "Seychelles": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Sierra Leone": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Somalia": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "South Africa": {"confederation": "CAF", "fifa_rank_2025": 41, "aliases": []},
    "South Sudan": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Sudan": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Tanzania": {"confederation": "CAF", "fifa_rank_2025": 88, "aliases": []},
    "Togo": {"confederation": "CAF", "fifa_rank_2025": None, "aliases": []},
    "Tunisia": {"confederation": "CAF", "fifa_rank_2025": 48, "aliases": []},
    "Uganda": {"confederation": "CAF", "fifa_rank_2025": 89, "aliases": []},
    "Zambia": {"confederation": "CAF", "fifa_rank_2025": 87, "aliases": []},
    "Zimbabwe": {"confederation": "CAF", "fifa_rank_2025": 79, "aliases": []},

    # =========================================================================
    # AFC (47 members)
    # =========================================================================
    "Afghanistan": {"confederation": "AFC", "fifa_rank_2025": 94, "aliases": []},
    "Australia": {"confederation": "AFC", "fifa_rank_2025": 24, "aliases": ["Socceroos"]},
    "Bahrain": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Bangladesh": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Bhutan": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Brunei": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": ["Brunei Darussalam"]},
    "Cambodia": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "China": {
        "confederation": "AFC", "fifa_rank_2025": 99,
        "aliases": ["China PR", "PR China", "People's Republic of China"],
    },
    "Chinese Taipei": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": ["Taiwan"]},
    "Guam": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Hong Kong": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "India": {"confederation": "AFC", "fifa_rank_2025": 95, "aliases": []},
    "Indonesia": {"confederation": "AFC", "fifa_rank_2025": 98, "aliases": []},
    "IR Iran": {
        "confederation": "AFC", "fifa_rank_2025": 22,
        "aliases": ["Iran", "Islamic Republic of Iran", "Iran IR"],
    },
    "Iraq": {"confederation": "AFC", "fifa_rank_2025": 61, "aliases": []},
    "Japan": {"confederation": "AFC", "fifa_rank_2025": 24, "aliases": []},
    "Jordan": {"confederation": "AFC", "fifa_rank_2025": 71, "aliases": []},
    "Korea DPR": {
        "confederation": "AFC", "fifa_rank_2025": None,
        "aliases": ["North Korea", "DPR Korea", "Democratic People's Republic of Korea"],
    },
    "Korea Republic": {
        "confederation": "AFC", "fifa_rank_2025": 23,
        "aliases": ["South Korea", "Korea", "Republic of Korea"],
    },
    "Kuwait": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Kyrgyzstan": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": ["Kyrgyz Republic"]},
    "Laos": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Lebanon": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Macau": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": ["Macao"]},
    "Malaysia": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Maldives": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Mongolia": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Myanmar": {
        "confederation": "AFC", "fifa_rank_2025": None,
        "aliases": ["Burma"],
    },
    "Nepal": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Oman": {"confederation": "AFC", "fifa_rank_2025": 77, "aliases": []},
    "Pakistan": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Palestine": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Philippines": {"confederation": "AFC", "fifa_rank_2025": 100, "aliases": []},
    "Qatar": {"confederation": "AFC", "fifa_rank_2025": 37, "aliases": []},
    "Saudi Arabia": {"confederation": "AFC", "fifa_rank_2025": 56, "aliases": []},
    "Singapore": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Sri Lanka": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Syria": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Tajikistan": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "Thailand": {"confederation": "AFC", "fifa_rank_2025": 96, "aliases": []},
    "Timor-Leste": {
        "confederation": "AFC", "fifa_rank_2025": None,
        "aliases": ["East Timor", "Timor Leste"],
    },
    "Turkmenistan": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},
    "UAE": {
        "confederation": "AFC", "fifa_rank_2025": None,
        "aliases": ["United Arab Emirates", "U.A.E."],
    },
    "Uzbekistan": {"confederation": "AFC", "fifa_rank_2025": 66, "aliases": []},
    "Vietnam": {"confederation": "AFC", "fifa_rank_2025": 97, "aliases": []},
    "Yemen": {"confederation": "AFC", "fifa_rank_2025": None, "aliases": []},

    # =========================================================================
    # OFC (11 members)
    # =========================================================================
    "American Samoa": {"confederation": "OFC", "fifa_rank_2025": None, "aliases": []},
    "Cook Islands": {"confederation": "OFC", "fifa_rank_2025": None, "aliases": []},
    "Fiji": {"confederation": "OFC", "fifa_rank_2025": None, "aliases": []},
    "New Caledonia": {"confederation": "OFC", "fifa_rank_2025": None, "aliases": []},
    "New Zealand": {"confederation": "OFC", "fifa_rank_2025": 72, "aliases": ["All Whites"]},
    "Papua New Guinea": {"confederation": "OFC", "fifa_rank_2025": None, "aliases": ["PNG"]},
    "Samoa": {"confederation": "OFC", "fifa_rank_2025": None, "aliases": []},
    "Solomon Islands": {"confederation": "OFC", "fifa_rank_2025": None, "aliases": []},
    "Tahiti": {"confederation": "OFC", "fifa_rank_2025": None, "aliases": []},
    "Tonga": {"confederation": "OFC", "fifa_rank_2025": None, "aliases": []},
    "Vanuatu": {"confederation": "OFC", "fifa_rank_2025": None, "aliases": []},
}

# ---------------------------------------------------------------------------
# Build flat alias lookup (populated once at import time)
# ---------------------------------------------------------------------------
ALIAS_TO_CANONICAL: dict[str, str] = {}


def _build_alias_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for display_name, meta in CANONICAL_TEAMS.items():
        mapping[display_name] = display_name  # canonical name maps to itself
        for alias in meta.get("aliases", []):
            if alias in mapping and mapping[alias] != display_name:
                raise ValueError(
                    f"Alias conflict: '{alias}' maps to both "
                    f"'{mapping[alias]}' and '{display_name}'"
                )
            mapping[alias] = display_name
    return mapping


ALIAS_TO_CANONICAL = _build_alias_map()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_team(name: str) -> str:
    """Map any raw team name to its canonical display name.

    Unknown names pass through unchanged — the pipeline never crashes on
    unexpected team names; they simply receive UNKNOWN confederation and
    default FIFA rank at runtime.
    """
    return ALIAS_TO_CANONICAL.get(str(name).strip(), str(name).strip())


def safe_resolve_team(name: str) -> Optional[str]:
    """Like resolve_team but returns None for names not in the registry."""
    return ALIAS_TO_CANONICAL.get(str(name).strip())


def get_confederation(name: str, default: str = "UNKNOWN") -> str:
    """Return the confederation for *name* (any alias), or *default*."""
    canonical = resolve_team(name)
    meta = CANONICAL_TEAMS.get(canonical)
    if meta is None:
        return default
    return meta.get("confederation", default)


def get_fifa_rank(name: str, default: int = 75) -> int:
    """Return the current FIFA rank for *name* (any alias), or *default*.

    Prefers data/processed/fifa_rankings.csv when present (issue #74) so
    rankings can be updated by editing the CSV without touching code.
    Falls back to the hardcoded fifa_rank_2025 snapshot in CANONICAL_TEAMS.
    """
    canonical = resolve_team(name)
    cache = _load_rankings_cache()
    if canonical in cache:
        return cache[canonical]
    meta = CANONICAL_TEAMS.get(canonical)
    if meta is None:
        return default
    rank = meta.get("fifa_rank_2025")
    return rank if rank is not None else default


def list_aliases(name: str) -> list[str]:
    """Return all registered aliases for a canonical team name."""
    canonical = resolve_team(name)
    meta = CANONICAL_TEAMS.get(canonical)
    if meta is None:
        return []
    return list(meta.get("aliases", []))


def is_known_team(name: str) -> bool:
    """Return True if *name* (or any alias) is in the canonical registry."""
    return str(name).strip() in ALIAS_TO_CANONICAL


# ---------------------------------------------------------------------------
# World Cup penalty shootout records (wins, total_shootouts, 1982-2022)
# ---------------------------------------------------------------------------
WC_PENALTY_RECORDS: dict[str, tuple[int, int]] = {
    "Germany": (4, 4),
    "Croatia": (4, 4),
    "Argentina": (4, 5),
    "Brazil": (3, 5),
    "France": (2, 3),
    "Korea Republic": (1, 1),
    "Morocco": (1, 1),
    "Ukraine": (1, 1),
    "Russia": (1, 1),
    "Ireland": (1, 1),
    "Belgium": (1, 1),
    "Bulgaria": (1, 1),
    "Portugal": (1, 1),
    "Uruguay": (1, 2),
    "Sweden": (1, 2),
    "Costa Rica": (1, 2),
    "Italy": (1, 3),
    "Netherlands": (1, 4),
    "England": (0, 2),
    "Spain": (0, 3),
    "Mexico": (0, 2),
    "Romania": (0, 2),
    "Switzerland": (0, 1),
    "Denmark": (0, 1),
    "Japan": (0, 1),
    "Ghana": (0, 1),
}


def get_penalty_win_rate(name: str, default: float = 0.5) -> float:
    """Return historical WC penalty shootout win rate for *name* (any alias).

    Returns *default* (0.5) for teams with no WC PSO history.
    """
    canonical = resolve_team(name)
    record = WC_PENALTY_RECORDS.get(canonical)
    if record is None or record[1] == 0:
        return default
    return record[0] / record[1]


# ---------------------------------------------------------------------------
# Defunct nation dissolution cutoffs
# Matches with these raw names before the cutoff are excluded from the
# training pipeline to prevent Elo bleed into successor states.
# ---------------------------------------------------------------------------
DEFUNCT_NATION_CUTOFFS: dict[str, str] = {
    "Soviet Union": "1992-01-01",
    "USSR": "1992-01-01",
    "CIS": "1993-01-01",
    "Yugoslavia": "1992-01-01",
    "Czechoslovakia": "1993-01-01",
    "East Germany": "1990-11-01",
}
