"""Confederation membership lookup — derived from team_identity canonical registry.

All callers use lookup_confederation(team_name); the underlying mapping is
built from team_identity.CANONICAL_TEAMS so there is one source of truth.
"""

from __future__ import annotations

from src.data.team_identity import CANONICAL_TEAMS, ALIAS_TO_CANONICAL

# ---------------------------------------------------------------------------
# Build flat {any_name: confederation} lookup at import time
# ---------------------------------------------------------------------------
TEAM_CONFEDERATION: dict[str, str] = {}

for _canonical, _meta in CANONICAL_TEAMS.items():
    _conf = _meta.get("confederation", "UNKNOWN")
    TEAM_CONFEDERATION[_canonical] = _conf
    for _alias in _meta.get("aliases", []):
        TEAM_CONFEDERATION[_alias] = _conf


def lookup_confederation(team: str) -> str:
    """Return the confederation for *team* (any alias), or 'UNKNOWN'."""
    canonical = ALIAS_TO_CANONICAL.get(str(team).strip(), str(team).strip())
    return TEAM_CONFEDERATION.get(canonical, "UNKNOWN")
