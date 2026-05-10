"""Single source of truth for competition importance (features + inference)."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Competition name normalisation map
# Maps raw/variant names → canonical internal key used for weight lookup.
# Keys are lowercased for case-insensitive matching.
# ---------------------------------------------------------------------------

_COMP_NORM_MAP: dict[str, str] = {
    # World Cup
    "fifa world cup": "FIFA World Cup",
    "world cup": "FIFA World Cup",
    # Euro
    "uefa european championship": "UEFA Euro",
    "uefa euro": "UEFA Euro",
    "european championship": "UEFA Euro",
    "euro": "UEFA Euro",
    # Copa
    "copa america": "Copa America",
    "copa américa": "Copa America",
    "south american championship": "Copa America",
    # Asian Cup
    "afc asian cup": "AFC Asian Cup",
    "asian cup": "AFC Asian Cup",
    # Africa
    "africa cup of nations": "Africa Cup of Nations",
    "african cup of nations": "Africa Cup of Nations",
    "afcon": "Africa Cup of Nations",
    "can": "Africa Cup of Nations",
    # Gold Cup / CONCACAF
    "concacaf gold cup": "Gold Cup",
    "gold cup": "Gold Cup",
    "concacaf championship": "Gold Cup",
    # Nations League
    "uefa nations league": "UEFA Nations League",
    "nations league": "UEFA Nations League",
    "uefa nations league a": "UEFA Nations League",
    "uefa nations league b": "UEFA Nations League",
    "uefa nations league c": "UEFA Nations League",
    "uefa nations league d": "UEFA Nations League",
    # Qualifications
    "fifa world cup qualification": "FIFA World Cup Qualification",
    "world cup qualification": "FIFA World Cup Qualification",
    "world cup qualifying": "FIFA World Cup Qualification",
    "wc qualification": "FIFA World Cup Qualification",
    "wc qualifying": "FIFA World Cup Qualification",
    "uefa euro qualification": "UEFA Euro Qualification",
    "euro qualification": "UEFA Euro Qualification",
    "european championship qualification": "UEFA Euro Qualification",
    "conmebol qualifier": "CONMEBOL Qualifier",
    "conmebol qualifying": "CONMEBOL Qualifier",
    "afc qualification": "FIFA World Cup Qualification",
    "caf qualification": "FIFA World Cup Qualification",
    "ofc qualification": "FIFA World Cup Qualification",
    "concacaf qualification": "FIFA World Cup Qualification",
    # Confederations Cup / minor comps
    "fifa confederations cup": "Confederations Cup",
    "confederations cup": "Confederations Cup",
    # Olympic Games
    "olympic games": "Olympic Games",
    "olympics": "Olympic Games",
    "summer olympics": "Olympic Games",
    # British Home Championship (historic)
    "british home championship": "British Home Championship",
    "home championship": "British Home Championship",
    # Friendlies
    "international friendly": "International Friendly",
    "friendly": "International Friendly",
    "friendlies": "International Friendly",
    "test match": "International Friendly",
    # Unknown / default
    "unknown": "Unknown",
}


def normalize_competition_name(competition: str) -> str:
    """Map a raw competition string to its canonical form for weight lookup."""
    return _COMP_NORM_MAP.get(str(competition).strip().lower(), competition)


# ---------------------------------------------------------------------------
# Sample-weight multipliers (used in build_features.py for match_weight)
# ---------------------------------------------------------------------------

COMPETITION_WEIGHTS: dict[str, int] = {
    "FIFA World Cup": 5,
    "UEFA Euro": 4,
    "Copa America": 4,
    "AFC Asian Cup": 4,
    "Africa Cup of Nations": 4,
    "Gold Cup": 3,
    "UEFA Nations League": 3,
    "Confederations Cup": 3,
    "Olympic Games": 2,
    "UEFA Euro Qualification": 2,
    "FIFA World Cup Qualification": 2,
    "CONMEBOL Qualifier": 2,
    "British Home Championship": 2,
    "International Friendly": 1,
}

DEFAULT_COMPETITION_WEIGHT = 2


def get_competition_weight(competition: str) -> int:
    """Return sample-weight for *competition*, normalising name first."""
    canon = normalize_competition_name(competition)
    return COMPETITION_WEIGHTS.get(canon, DEFAULT_COMPETITION_WEIGHT)


# ---------------------------------------------------------------------------
# Elo K-factor multipliers: high-stakes matches move ratings more
# ---------------------------------------------------------------------------

COMPETITION_K_MULTIPLIERS: dict[str, float] = {
    "FIFA World Cup": 2.0,
    "UEFA Euro": 1.75,
    "Copa America": 1.75,
    "AFC Asian Cup": 1.5,
    "Africa Cup of Nations": 1.5,
    "Gold Cup": 1.25,
    "UEFA Nations League": 1.25,
    "Confederations Cup": 1.25,
    "Olympic Games": 1.0,
    "UEFA Euro Qualification": 1.0,
    "FIFA World Cup Qualification": 1.0,
    "CONMEBOL Qualifier": 1.0,
    "British Home Championship": 1.0,
    "International Friendly": 0.5,
}

DEFAULT_COMPETITION_K_MULTIPLIER: float = 1.0


def get_competition_k_multiplier(competition: str) -> float:
    """Return Elo K-factor multiplier for *competition*, normalising name first."""
    canon = normalize_competition_name(competition)
    return COMPETITION_K_MULTIPLIERS.get(canon, DEFAULT_COMPETITION_K_MULTIPLIER)

# ---------------------------------------------------------------------------
# Tournament stage normalization
# ---------------------------------------------------------------------------

_STAGE_NORM_MAP: dict[str, str] = {
    # Group stage variants
    "group": "group_stage",
    "group stage": "group_stage",
    "group phase": "group_stage",
    "groups": "group_stage",
    "league stage": "group_stage",
    "group stage round 1": "group_stage",
    "group stage round 2": "group_stage",
    "group stage round 3": "group_stage",
    "matchday 1": "group_stage",
    "matchday 2": "group_stage",
    "matchday 3": "group_stage",
    "group a": "group_stage",
    "group b": "group_stage",
    "group c": "group_stage",
    "group d": "group_stage",
    "group e": "group_stage",
    "group f": "group_stage",
    "group g": "group_stage",
    "group h": "group_stage",
    # Knockout rounds
    "round of 64": "round_of_64",
    "round of 32": "round_of_32",
    "first round": "round_of_32",
    "1st round": "round_of_32",
    "round of 16": "round_of_16",
    "last 16": "round_of_16",
    "second round": "round_of_16",
    "2nd round": "round_of_16",
    "round of 8": "quarterfinal",
    "quarter-final": "quarterfinal",
    "quarter-finals": "quarterfinal",
    "quarterfinal": "quarterfinal",
    "quarterfinals": "quarterfinal",
    "quarterfinales": "quarterfinal",
    "quarter final": "quarterfinal",
    "round of 4": "semifinal",
    "semi-final": "semifinal",
    "semi-finals": "semifinal",
    "semifinal": "semifinal",
    "semi final": "semifinal",
    "final": "final",
    "grand final": "final",
    "championship": "final",
    # Third place
    "third place": "third_place",
    "third-place": "third_place",
    "third-place playoff": "third_place",
    "3rd place": "third_place",
    "3rd place playoff": "third_place",
    "third place play-off": "third_place",
    # Playoffs
    "play-off": "playoff",
    "play-offs": "playoff",
    "playoff": "playoff",
    "playoffs": "playoff",
    "promotion play-off": "playoff",
    "relegation play-off": "playoff",
    # Qualification
    "qualification": "qualification",
    "qualifying": "qualification",
    "qualifier": "qualification",
    "qualifiers": "qualification",
    "qualification round": "qualification",
    "qualifying round": "qualification",
    "preliminary": "qualification",
    "preliminary round": "qualification",
    # Unknown / fallback
    "unknown": "unknown",
    "none": "unknown",
    "nan": "unknown",
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


# ---------------------------------------------------------------------------
# Issue #59: per-tier H/D/A base rates
# Rates are empirically derived from international match data and represent
# the structural outcome distribution for each competition importance tier.
# Tier 5 (World Cup) has more decisive results due to knockout format bias.
# Tier 1 (Friendlies) has fewer home wins due to experimental lineup effects.
# ---------------------------------------------------------------------------

_TIER_BASE_RATES: dict[int, dict[str, float]] = {
    5: {"home_rate": 0.44, "draw_rate": 0.23, "away_rate": 0.33},  # World Cup
    4: {"home_rate": 0.46, "draw_rate": 0.24, "away_rate": 0.30},  # Major continental
    3: {"home_rate": 0.48, "draw_rate": 0.25, "away_rate": 0.27},  # Secondary continental
    2: {"home_rate": 0.50, "draw_rate": 0.25, "away_rate": 0.25},  # Qualifiers
    1: {"home_rate": 0.44, "draw_rate": 0.27, "away_rate": 0.29},  # Friendlies
}

_DEFAULT_TIER_BASE_RATES = {"home_rate": 0.47, "draw_rate": 0.25, "away_rate": 0.28}


def get_tier_base_rates(competition_weight: int) -> dict[str, float]:
    """Return empirical H/D/A base rates for the given competition-weight tier."""
    return _TIER_BASE_RATES.get(competition_weight, _DEFAULT_TIER_BASE_RATES)


# ---------------------------------------------------------------------------
# Issue #47: per-stage sample weight multipliers
# Maps canonical stage → weight multiplier so knockout matches influence
# training more than group-stage or friendly matches.
# Minimum is 0.5 (unknown/qualification) to avoid zeroing out old matches.
# ---------------------------------------------------------------------------

_STAGE_SAMPLE_WEIGHTS: dict[str, float] = {
    "unknown": 0.5,
    "qualification": 0.5,
    "group_stage": 1.0,
    "round_of_64": 1.25,
    "round_of_32": 1.25,
    "round_of_16": 1.5,
    "playoff": 1.5,
    "quarterfinal": 1.75,
    "semifinal": 2.0,
    "third_place": 1.5,
    "final": 2.5,
}

_DEFAULT_STAGE_SAMPLE_WEIGHT: float = 1.0


def get_stage_sample_weight(stage: str) -> float:
    """Return sample-weight multiplier for the given tournament stage.

    Accepts both raw and canonical stage strings.
    """
    norm = normalize_tournament_stage(stage)
    return _STAGE_SAMPLE_WEIGHTS.get(norm, _DEFAULT_STAGE_SAMPLE_WEIGHT)
