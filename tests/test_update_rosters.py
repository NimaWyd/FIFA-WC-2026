import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from datetime import date
from scripts.update_rosters_from_pdf import (
    calc_age,
    title_case_name,
    strip_club_country,
    normalize_for_match,
)

TOURNAMENT = date(2026, 6, 11)

class TestCalcAge:
    def test_birthday_already_passed(self):
        assert calc_age("01/05/1990", TOURNAMENT) == 36

    def test_birthday_not_yet_this_year(self):
        # born July — hasn't had birthday by 11 June
        assert calc_age("15/07/1990", TOURNAMENT) == 35

    def test_born_on_tournament_day(self):
        assert calc_age("11/06/1994", TOURNAMENT) == 32

class TestTitleCaseName:
    def test_simple(self):
        assert title_case_name("MAHREZ") == "Mahrez"

    def test_compound(self):
        assert title_case_name("HADJ MOUSSA") == "Hadj Moussa"

    def test_hyphen(self):
        assert title_case_name("AÏT-NOURI") == "Aït-Nouri"

    def test_accented(self):
        assert title_case_name("BELAÏD") == "Belaïd"

class TestStripClubCountry:
    def test_basic(self):
        assert strip_club_country("Lille OSC (FRA)") == "Lille OSC"

    def test_three_letter_code(self):
        assert strip_club_country("Al Ahli FC (KSA)") == "Al Ahli FC"

    def test_no_code(self):
        assert strip_club_country("Juventus") == "Juventus"

class TestNormalizeForMatch:
    def test_strips_accents(self):
        assert normalize_for_match("Aïssa Mandi") == normalize_for_match("Aissa Mandi")

    def test_token_order_invariant(self):
        assert normalize_for_match("Mandi Aissa") == normalize_for_match("Aissa Mandi")

    def test_case_insensitive(self):
        assert normalize_for_match("MAHREZ") == normalize_for_match("mahrez")

from scripts.update_rosters_from_pdf import parse_player_words, parse_coach_words

# ── Fixtures (x-positions verified from Algeria page 1 of the PDF) ─────────────

MANDI_WORDS = [
    {"text": "2",          "x0": 7},
    {"text": "DF",         "x0": 18},
    {"text": "MANDI",      "x0": 29},   # PLAYER NAME col (sort-last)
    {"text": "Aissa",      "x0": 40},   # PLAYER NAME col (short first)
    {"text": "Aissa",      "x0": 103},  # FIRST NAME(S) col
    {"text": "MANDI",      "x0": 181},  # LAST NAME(S) col
    {"text": "MANDI",      "x0": 227},  # NAME ON SHIRT col
    {"text": "22/10/1991", "x0": 282},
    {"text": "Lille",      "x0": 310},
    {"text": "OSC",        "x0": 317},
    {"text": "(FRA)",      "x0": 323},
    {"text": "184",        "x0": 405},
]

HADJ_MOUSSA_WORDS = [
    {"text": "11",          "x0": 7},
    {"text": "FW",          "x0": 18},
    {"text": "HADJ",        "x0": 29},
    {"text": "MOUSSA",      "x0": 38},
    {"text": "Anis",        "x0": 40},
    {"text": "Anis",        "x0": 103},
    {"text": "HADJ",        "x0": 181},
    {"text": "MOUSSA",      "x0": 190},
    {"text": "HADJ",        "x0": 227},
    {"text": "MOUSSA",      "x0": 238},
    {"text": "11/02/2002",  "x0": 282},
    {"text": "Feyenoord",   "x0": 310},
    {"text": "Rotterdam",   "x0": 322},
    {"text": "(NED)",       "x0": 334},
    {"text": "176",         "x0": 405},
]

BELAID_WORDS = [
    {"text": "5",           "x0": 7},
    {"text": "DF",          "x0": 18},
    {"text": "BELAID",      "x0": 29},
    {"text": "Zineddine",   "x0": 40},
    {"text": "Zineddine",   "x0": 103},
    {"text": "BELAÏD",      "x0": 181},  # accented in LAST NAME col
    {"text": "BELAID",      "x0": 227},  # no accent on shirt
    {"text": "20/03/1999",  "x0": 282},
    {"text": "JS",          "x0": 310},
    {"text": "Kabylie",     "x0": 315},
    {"text": "(ALG)",       "x0": 325},
    {"text": "186",         "x0": 405},
]

PETKOVIC_WORDS = [
    {"text": "Head",        "x0": 7},
    {"text": "coach",       "x0": 15},
    {"text": "PETKOVIC",    "x0": 74},
    {"text": "Vladimir",    "x0": 89},
    {"text": "Vladimir",    "x0": 181},  # FIRST NAME(S) col
    {"text": "PETKOVIĆ",    "x0": 267},  # LAST NAME(S) col (accented)
    {"text": "Switzerland", "x0": 351},
]

# Algeria page player col_bounds: (x_12, x_23, x_34, x_dob)
# x_23 = 181 (left edge of LAST NAME col), x_34 = 227 (left edge of SHIRT col)
# x_12 = midpoint between PLAYER NAME and FIRST NAME headers (~102)
# x_dob = 282 (DOB column start)
ALGERIA_PLAYER_BOUNDS = (102, 181, 227, 282)
ALGERIA_COACH_BOUNDS = (181, 267)

class TestParsePlayerWords:
    def test_simple_name(self):
        r = parse_player_words(MANDI_WORDS, TOURNAMENT, ALGERIA_PLAYER_BOUNDS)
        assert r["name"] == "Aissa Mandi"
        assert r["position_key"] == "defenders"
        assert r["age"] == 34
        assert r["club"] == "Lille OSC"

    def test_compound_last_name(self):
        r = parse_player_words(HADJ_MOUSSA_WORDS, TOURNAMENT, ALGERIA_PLAYER_BOUNDS)
        assert r["name"] == "Anis Hadj Moussa"
        assert r["position_key"] == "forwards"
        assert r["club"] == "Feyenoord Rotterdam"

    def test_accented_last_name_uses_last_name_col(self):
        r = parse_player_words(BELAID_WORDS, TOURNAMENT, ALGERIA_PLAYER_BOUNDS)
        # LAST NAME col has BELAÏD (accented), SHIRT col has BELAID — use LAST NAME
        assert r["name"] == "Zineddine Belaïd"

class TestParseCoachWords:
    def test_coach_name(self):
        assert parse_coach_words(PETKOVIC_WORDS, ALGERIA_COACH_BOUNDS) == "Vladimir Petković"

from scripts.update_rosters_from_pdf import find_best_match, resolve_team_key

class TestFindBestMatch:
    POOL = [
        {"name": "Aissa Mandi",  "espn_id": "111", "sofascore_id": "222"},
        {"name": "Riyad Mahrez", "espn_id": "333"},
    ]

    def test_exact_match(self):
        r = find_best_match("Aissa Mandi", self.POOL)
        assert r == {"espn_id": "111", "sofascore_id": "222"}

    def test_fuzzy_match_accent(self):
        # Belaïd vs Belaid — same after accent-strip
        pool = [{"name": "Zineddine Belaid", "espn_id": "999", "sofascore_id": "888"}]
        r = find_best_match("Zineddine Belaïd", pool)
        assert r == {"espn_id": "999", "sofascore_id": "888"}

    def test_no_match_returns_empty(self):
        assert find_best_match("Completely Different", self.POOL) == {}

    def test_returns_only_existing_ids(self):
        # Mahrez has espn_id but no sofascore_id — don't add None
        r = find_best_match("Riyad Mahrez", self.POOL)
        assert r == {"espn_id": "333"}
        assert "sofascore_id" not in r

class TestResolveTeamKey:
    ROSTERS = {"Algeria": {}, "Cape Verde Islands": {}, "Bosnia and Herzegovina": {}, "Turkey": {}}

    def test_direct_match(self):
        assert resolve_team_key("Algeria", self.ROSTERS) == "Algeria"

    def test_override_cabo_verde(self):
        assert resolve_team_key("Cabo Verde", self.ROSTERS) == "Cape Verde Islands"

    def test_override_turkey(self):
        assert resolve_team_key("Türkiye", self.ROSTERS) == "Turkey"

    def test_case_insensitive_fallback(self):
        assert resolve_team_key("ALGERIA", self.ROSTERS) == "Algeria"

    def test_unmapped_returns_none(self):
        assert resolve_team_key("Atlantis", self.ROSTERS) is None
