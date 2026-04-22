"""Single source of truth for competition importance (features + inference)."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Sample-weight multipliers (used in build_features.py for match_weight)
# ---------------------------------------------------------------------------

COMPETITION_WEIGHTS: dict[str, int] = {
    "FIFA World Cup": 5,
    "UEFA Euro": 4,
    "Copa America": 4,
    "AFC Asian Cup": 4,
    "Africa Cup of Nations": 4,
    "AFCON": 4,
    "Gold Cup": 3,
    "UEFA Nations League": 3,
    "UEFA Euro Qualification": 2,
    "FIFA World Cup Qualification": 2,
    "CONMEBOL Qualifier": 2,
    "International Friendly": 1,
}

DEFAULT_COMPETITION_WEIGHT = 2

# ---------------------------------------------------------------------------
# Elo K-factor multipliers: high-stakes matches move ratings more
# ---------------------------------------------------------------------------

COMPETITION_K_MULTIPLIERS: dict[str, float] = {
    "FIFA World Cup": 2.0,
    "UEFA Euro": 1.75,
    "Copa America": 1.75,
    "AFC Asian Cup": 1.5,
    "Africa Cup of Nations": 1.5,
    "AFCON": 1.5,
    "Gold Cup": 1.25,
    "UEFA Nations League": 1.25,
    "UEFA Euro Qualification": 1.0,
    "FIFA World Cup Qualification": 1.0,
    "CONMEBOL Qualifier": 1.0,
    "International Friendly": 0.5,
}

DEFAULT_COMPETITION_K_MULTIPLIER: float = 1.0

# ---------------------------------------------------------------------------
# Tournament stage normalization
# ---------------------------------------------------------------------------

_STAGE_NORM_MAP: dict[str, str] = {
    "group": "group_stage",
    "group stage": "group_stage",
    "group phase": "group_stage",
    "groups": "group_stage",
    "group a": "group_stage",
    "group b": "group_stage",
    "group c": "group_stage",
    "group d": "group_stage",
    "group e": "group_stage",
    "group f": "group_stage",
    "round of 64": "round_of_64",
    "round of 32": "round_of_32",
    "round of 16": "round_of_16",
    "last 16": "round_of_16",
    "round of 8": "quarterfinal",
    "quarter-final": "quarterfinal",
    "quarter-finals": "quarterfinal",
    "quarterfinal": "quarterfinal",
    "quarterfinales": "quarterfinal",
    "quarter final": "quarterfinal",
    "semi-final": "semifinal",
    "semi-finals": "semifinal",
    "semifinal": "semifinal",
    "semi final": "semifinal",
    "final": "final",
    "grand final": "final",
    "third place": "third_place",
    "third-place": "third_place",
    "third-place playoff": "third_place",
    "3rd place": "third_place",
    "3rd place playoff": "third_place",
    "play-off": "playoff",
    "play-offs": "playoff",
    "playoff": "playoff",
    "playoffs": "playoff",
    "qualification": "qualification",
    "qualifying": "qualification",
    "qualifier": "qualification",
    "qualifiers": "qualification",
    "qualification round": "qualification",
    "unknown": "unknown",
}

# Numeric importance for each canonical stage (used as a feature)
STAGE_IMPORTANCE: dict[str, int] = {
    "unknown": 0,
    "qualification": 0,
    "group_stage": 1,
    "round_of_64": 2,
    "round_of_32": 3,
    "round_of_16": 4,
    "playoff": 4,
    "quarterfinal": 5,
    "semifinal": 6,
    "third_place": 7,
    "final": 8,
}

DEFAULT_STAGE_IMPORTANCE = 1


def normalize_tournament_stage(stage: str) -> str:
    """Map a raw tournament stage string to a canonical lower-cased form."""
    key = str(stage).strip().lower()
    if key in _STAGE_NORM_MAP:
        return _STAGE_NORM_MAP[key]
    # Fall back: lower-case, replace spaces/hyphens with underscores
    return key.replace(" ", "_").replace("-", "_")


def get_stage_importance(stage: str) -> int:
    """Return numeric importance for a tournament stage (higher = later stage)."""
    norm = normalize_tournament_stage(stage)
    return STAGE_IMPORTANCE.get(norm, DEFAULT_STAGE_IMPORTANCE)
