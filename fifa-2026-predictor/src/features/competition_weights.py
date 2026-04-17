"""Single source of truth for competition importance (features + inference)."""

COMPETITION_WEIGHTS: dict[str, int] = {
    "FIFA World Cup": 5,
    "UEFA Euro": 4,
    "Copa America": 4,
    "UEFA Nations League": 3,
    "UEFA Euro Qualification": 2,
    "FIFA World Cup Qualification": 2,
    "International Friendly": 1,
}

DEFAULT_COMPETITION_WEIGHT = 2
