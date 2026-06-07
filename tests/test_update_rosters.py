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
