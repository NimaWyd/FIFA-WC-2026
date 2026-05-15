# fifa-2026-predictor/src/simulation/wc2026_bracket.py
"""WC2026 group structure and R32 bracket — backend counterpart to frontend/src/lib/wc2026Groups.ts."""
from __future__ import annotations

WC2026_GROUPS: list[dict] = [
    {
        "id": "A",
        "teams": ["Mexico", "Korea Republic", "South Africa", "Czechia"],
        "matches": [
            {"home": "Mexico", "away": "South Africa", "date": "2026-06-11"},
            {"home": "Korea Republic", "away": "Czechia", "date": "2026-06-12"},
            {"home": "Mexico", "away": "Korea Republic", "date": "2026-06-18"},
            {"home": "Czechia", "away": "South Africa", "date": "2026-06-18"},
            {"home": "Czechia", "away": "Mexico", "date": "2026-06-25"},
            {"home": "South Africa", "away": "Korea Republic", "date": "2026-06-25"},
        ],
    },
    {
        "id": "B",
        "teams": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
        "matches": [
            {"home": "Canada", "away": "Bosnia and Herzegovina", "date": "2026-06-12"},
            {"home": "Qatar", "away": "Switzerland", "date": "2026-06-13"},
            {"home": "Switzerland", "away": "Bosnia and Herzegovina", "date": "2026-06-18"},
            {"home": "Canada", "away": "Qatar", "date": "2026-06-18"},
            {"home": "Switzerland", "away": "Canada", "date": "2026-06-24"},
            {"home": "Bosnia and Herzegovina", "away": "Qatar", "date": "2026-06-24"},
        ],
    },
    {
        "id": "C",
        "teams": ["Brazil", "Morocco", "Scotland", "Haiti"],
        "matches": [
            {"home": "Brazil", "away": "Morocco", "date": "2026-06-13"},
            {"home": "Haiti", "away": "Scotland", "date": "2026-06-13"},
            {"home": "Scotland", "away": "Morocco", "date": "2026-06-19"},
            {"home": "Brazil", "away": "Haiti", "date": "2026-06-19"},
            {"home": "Morocco", "away": "Haiti", "date": "2026-06-24"},
            {"home": "Scotland", "away": "Brazil", "date": "2026-06-24"},
        ],
    },
    {
        "id": "D",
        "teams": ["United States", "Paraguay", "Australia", "Turkey"],
        "matches": [
            {"home": "United States", "away": "Paraguay", "date": "2026-06-12"},
            {"home": "Australia", "away": "Turkey", "date": "2026-06-14"},
            {"home": "United States", "away": "Australia", "date": "2026-06-19"},
            {"home": "Turkey", "away": "Paraguay", "date": "2026-06-19"},
            {"home": "Turkey", "away": "United States", "date": "2026-06-25"},
            {"home": "Paraguay", "away": "Australia", "date": "2026-06-25"},
        ],
    },
    {
        "id": "E",
        "teams": ["Germany", "Côte d'Ivoire", "Ecuador", "Curaçao"],
        "matches": [
            {"home": "Germany", "away": "Curaçao", "date": "2026-06-14"},
            {"home": "Côte d'Ivoire", "away": "Ecuador", "date": "2026-06-14"},
            {"home": "Germany", "away": "Côte d'Ivoire", "date": "2026-06-20"},
            {"home": "Ecuador", "away": "Curaçao", "date": "2026-06-20"},
            {"home": "Ecuador", "away": "Germany", "date": "2026-06-25"},
            {"home": "Curaçao", "away": "Côte d'Ivoire", "date": "2026-06-25"},
        ],
    },
    {
        "id": "F",
        "teams": ["Netherlands", "Japan", "Sweden", "Tunisia"],
        "matches": [
            {"home": "Netherlands", "away": "Japan", "date": "2026-06-14"},
            {"home": "Sweden", "away": "Tunisia", "date": "2026-06-14"},
            {"home": "Netherlands", "away": "Sweden", "date": "2026-06-20"},
            {"home": "Tunisia", "away": "Japan", "date": "2026-06-20"},
            {"home": "Tunisia", "away": "Netherlands", "date": "2026-06-25"},
            {"home": "Japan", "away": "Sweden", "date": "2026-06-25"},
        ],
    },
    {
        "id": "G",
        "teams": ["Belgium", "Egypt", "IR Iran", "New Zealand"],
        "matches": [
            {"home": "Belgium", "away": "Egypt", "date": "2026-06-15"},
            {"home": "IR Iran", "away": "New Zealand", "date": "2026-06-15"},
            {"home": "Belgium", "away": "IR Iran", "date": "2026-06-21"},
            {"home": "New Zealand", "away": "Egypt", "date": "2026-06-21"},
            {"home": "New Zealand", "away": "Belgium", "date": "2026-06-26"},
            {"home": "Egypt", "away": "IR Iran", "date": "2026-06-26"},
        ],
    },
    {
        "id": "H",
        "teams": ["Spain", "Saudi Arabia", "Uruguay", "Cape Verde Islands"],
        "matches": [
            {"home": "Spain", "away": "Cape Verde Islands", "date": "2026-06-15"},
            {"home": "Saudi Arabia", "away": "Uruguay", "date": "2026-06-15"},
            {"home": "Spain", "away": "Saudi Arabia", "date": "2026-06-21"},
            {"home": "Uruguay", "away": "Cape Verde Islands", "date": "2026-06-21"},
            {"home": "Uruguay", "away": "Spain", "date": "2026-06-26"},
            {"home": "Cape Verde Islands", "away": "Saudi Arabia", "date": "2026-06-26"},
        ],
    },
    {
        "id": "I",
        "teams": ["France", "Senegal", "Norway", "Iraq"],
        "matches": [
            {"home": "France", "away": "Senegal", "date": "2026-06-16"},
            {"home": "Iraq", "away": "Norway", "date": "2026-06-16"},
            {"home": "France", "away": "Iraq", "date": "2026-06-22"},
            {"home": "Norway", "away": "Senegal", "date": "2026-06-22"},
            {"home": "Norway", "away": "France", "date": "2026-06-26"},
            {"home": "Senegal", "away": "Iraq", "date": "2026-06-26"},
        ],
    },
    {
        "id": "J",
        "teams": ["Argentina", "Algeria", "Austria", "Jordan"],
        "matches": [
            {"home": "Argentina", "away": "Algeria", "date": "2026-06-16"},
            {"home": "Austria", "away": "Jordan", "date": "2026-06-16"},
            {"home": "Argentina", "away": "Austria", "date": "2026-06-22"},
            {"home": "Jordan", "away": "Algeria", "date": "2026-06-22"},
            {"home": "Jordan", "away": "Argentina", "date": "2026-06-27"},
            {"home": "Algeria", "away": "Austria", "date": "2026-06-27"},
        ],
    },
    {
        "id": "K",
        "teams": ["Portugal", "Uzbekistan", "Colombia", "DR Congo"],
        "matches": [
            {"home": "Portugal", "away": "DR Congo", "date": "2026-06-17"},
            {"home": "Uzbekistan", "away": "Colombia", "date": "2026-06-17"},
            {"home": "Portugal", "away": "Uzbekistan", "date": "2026-06-23"},
            {"home": "Colombia", "away": "DR Congo", "date": "2026-06-23"},
            {"home": "Colombia", "away": "Portugal", "date": "2026-06-27"},
            {"home": "DR Congo", "away": "Uzbekistan", "date": "2026-06-27"},
        ],
    },
    {
        "id": "L",
        "teams": ["England", "Croatia", "Ghana", "Panama"],
        "matches": [
            {"home": "England", "away": "Croatia", "date": "2026-06-17"},
            {"home": "Ghana", "away": "Panama", "date": "2026-06-17"},
            {"home": "England", "away": "Ghana", "date": "2026-06-23"},
            {"home": "Panama", "away": "Croatia", "date": "2026-06-23"},
            {"home": "Panama", "away": "England", "date": "2026-06-27"},
            {"home": "Croatia", "away": "Ghana", "date": "2026-06-27"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Knockout bracket advancement — source: Wikipedia "2026 FIFA World Cup knockout stage"
# Each tuple = (match_number_A, match_number_B) whose winners meet in the next round.
# ---------------------------------------------------------------------------

# R16: which two R32 match winners play each other
WC2026_R16_PAIRS: list[tuple[int, int]] = [
    (74, 77),  # Match 89
    (73, 75),  # Match 90
    (76, 78),  # Match 91
    (79, 80),  # Match 92
    (83, 84),  # Match 93
    (81, 82),  # Match 94
    (86, 88),  # Match 95
    (85, 87),  # Match 96
]

# QF: which two R16 match winners play each other
WC2026_QF_PAIRS: list[tuple[int, int]] = [
    (89, 90),   # Match 97
    (93, 96),   # Match 98
    (91, 92),   # Match 99
    (94, 95),   # Match 100
]

# SF: which two QF match winners play each other
WC2026_SF_PAIRS: list[tuple[int, int]] = [
    (97, 98),   # Match 101
    (99, 100),  # Match 102
]

# R32 bracket — source: Wikipedia "2026 FIFA World Cup knockout stage"
# slot_type: "W" = group winner, "RU" = runner-up, "3rd" = best 3rd-place
# eligible_groups: for "3rd" slots, the set of groups whose 3rd-place team can fill this slot
WC2026_R32: list[dict] = [
    {"match": 73, "slot1_type": "RU", "slot1_group": "A", "slot2_type": "RU", "slot2_group": "B"},
    {"match": 74, "slot1_type": "W",  "slot1_group": "E", "slot2_type": "3rd", "eligible_groups": {"A","B","C","D","F"}},
    {"match": 75, "slot1_type": "W",  "slot1_group": "F", "slot2_type": "RU", "slot2_group": "C"},
    {"match": 76, "slot1_type": "W",  "slot1_group": "C", "slot2_type": "RU", "slot2_group": "F"},
    {"match": 77, "slot1_type": "W",  "slot1_group": "I", "slot2_type": "3rd", "eligible_groups": {"C","D","F","G","H"}},
    {"match": 78, "slot1_type": "RU", "slot1_group": "E", "slot2_type": "RU", "slot2_group": "I"},
    {"match": 79, "slot1_type": "W",  "slot1_group": "A", "slot2_type": "3rd", "eligible_groups": {"C","E","F","H","I"}},
    {"match": 80, "slot1_type": "W",  "slot1_group": "L", "slot2_type": "3rd", "eligible_groups": {"E","H","I","J","K"}},
    {"match": 81, "slot1_type": "W",  "slot1_group": "D", "slot2_type": "3rd", "eligible_groups": {"B","E","F","I","J"}},
    {"match": 82, "slot1_type": "W",  "slot1_group": "G", "slot2_type": "3rd", "eligible_groups": {"A","E","H","I","J"}},
    {"match": 83, "slot1_type": "RU", "slot1_group": "K", "slot2_type": "RU", "slot2_group": "L"},
    {"match": 84, "slot1_type": "W",  "slot1_group": "H", "slot2_type": "RU", "slot2_group": "J"},
    {"match": 85, "slot1_type": "W",  "slot1_group": "B", "slot2_type": "3rd", "eligible_groups": {"E","F","G","I","J"}},
    {"match": 86, "slot1_type": "W",  "slot1_group": "J", "slot2_type": "RU", "slot2_group": "H"},
    {"match": 87, "slot1_type": "W",  "slot1_group": "K", "slot2_type": "3rd", "eligible_groups": {"D","E","I","J","L"}},
    {"match": 88, "slot1_type": "RU", "slot1_group": "D", "slot2_type": "RU", "slot2_group": "G"},
]
