"""
Canonical player records.

Mirrors the design of team_identity.py: a small authoritative registry
with alias resolution, so all downstream code works with stable player_id
values regardless of the source name variant.

Extend CANONICAL_PLAYERS with real data when external sources are connected.
The resolution layer (resolve_player / get_player) stays stable.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Canonical registry
# Format: player_id -> {name, nationality, position, birth_date, aliases}
# ---------------------------------------------------------------------------
CANONICAL_PLAYERS: Dict[str, Dict] = {
    "messi_lionel": {
        "name": "Lionel Messi",
        "nationality": "Argentina",
        "position": "FWD",
        "birth_date": "1987-06-24",
        "aliases": ["L. Messi", "Leo Messi", "Messi"],
    },
    "ronaldo_cristiano": {
        "name": "Cristiano Ronaldo",
        "nationality": "Portugal",
        "position": "FWD",
        "birth_date": "1985-02-05",
        "aliases": ["C. Ronaldo", "CR7", "Ronaldo"],
    },
    "mbappe_kylian": {
        "name": "Kylian Mbappé",
        "nationality": "France",
        "position": "FWD",
        "birth_date": "1998-12-20",
        "aliases": ["K. Mbappe", "Mbappe", "Mbappé"],
    },
    "neuer_manuel": {
        "name": "Manuel Neuer",
        "nationality": "Germany",
        "position": "GK",
        "birth_date": "1986-03-27",
        "aliases": ["M. Neuer", "Neuer"],
    },
    "kane_harry": {
        "name": "Harry Kane",
        "nationality": "England",
        "position": "FWD",
        "birth_date": "1993-07-28",
        "aliases": ["H. Kane", "Kane"],
    },
    "salah_mohamed": {
        "name": "Mohamed Salah",
        "nationality": "Egypt",
        "position": "FWD",
        "birth_date": "1992-06-15",
        "aliases": ["M. Salah", "Salah", "Mo Salah"],
    },
    "neymar_jr": {
        "name": "Neymar Jr",
        "nationality": "Brazil",
        "position": "FWD",
        "birth_date": "1992-02-05",
        "aliases": ["Neymar", "Neymar Jr.", "N. Junior"],
    },
    "de_bruyne_kevin": {
        "name": "Kevin De Bruyne",
        "nationality": "Belgium",
        "position": "MID",
        "birth_date": "1991-06-28",
        "aliases": ["K. De Bruyne", "De Bruyne", "KDB"],
    },
    "modric_luka": {
        "name": "Luka Modrić",
        "nationality": "Croatia",
        "position": "MID",
        "birth_date": "1985-09-09",
        "aliases": ["L. Modric", "Modric", "Modrić"],
    },
    "benzema_karim": {
        "name": "Karim Benzema",
        "nationality": "France",
        "position": "FWD",
        "birth_date": "1987-12-19",
        "aliases": ["K. Benzema", "Benzema"],
    },
    "lewandowski_robert": {
        "name": "Robert Lewandowski",
        "nationality": "Poland",
        "position": "FWD",
        "birth_date": "1988-08-21",
        "aliases": ["R. Lewandowski", "Lewandowski", "Lewy"],
    },
    "alisson_becker": {
        "name": "Alisson Becker",
        "nationality": "Brazil",
        "position": "GK",
        "birth_date": "1992-10-02",
        "aliases": ["Alisson", "A. Becker"],
    },
    "courtois_thibaut": {
        "name": "Thibaut Courtois",
        "nationality": "Belgium",
        "position": "GK",
        "birth_date": "1992-05-11",
        "aliases": ["T. Courtois", "Courtois"],
    },
    "henderson_jordan": {
        "name": "Jordan Henderson",
        "nationality": "England",
        "position": "MID",
        "birth_date": "1990-06-17",
        "aliases": ["J. Henderson", "Henderson"],
    },
    "son_heung_min": {
        "name": "Son Heung-min",
        "nationality": "South Korea",
        "position": "FWD",
        "birth_date": "1992-07-08",
        "aliases": ["H. Son", "Son", "Sonny"],
    },
}

# ---------------------------------------------------------------------------
# Reverse lookup: normalised alias -> player_id
# ---------------------------------------------------------------------------
_ALIAS_MAP: Dict[str, str] = {}
for _pid, _data in CANONICAL_PLAYERS.items():
    _ALIAS_MAP[_pid] = _pid
    _ALIAS_MAP[_data["name"].lower()] = _pid
    for _alias in _data.get("aliases", []):
        _ALIAS_MAP[_alias.lower()] = _pid


def _normalise(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def resolve_player(name: str, nationality: Optional[str] = None) -> Optional[str]:
    """
    Return the canonical player_id for *name*, or None if unknown.

    *nationality* is used to disambiguate when the same display name
    appears for players from different countries.
    """
    key = _normalise(name)
    player_id = _ALIAS_MAP.get(key)
    if player_id is None:
        return None
    if nationality:
        entry = CANONICAL_PLAYERS[player_id]
        if entry["nationality"].lower() != nationality.lower():
            return None
    return player_id


def get_player(player_id: str) -> Optional[Dict]:
    """Return the canonical record for *player_id*, or None if not found."""
    return CANONICAL_PLAYERS.get(player_id)


def list_players_for_team(nationality: str) -> List[str]:
    """Return all player_ids whose nationality matches *nationality*."""
    return [
        pid
        for pid, data in CANONICAL_PLAYERS.items()
        if data["nationality"].lower() == nationality.lower()
    ]
