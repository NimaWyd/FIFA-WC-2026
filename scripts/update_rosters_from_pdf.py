"""
Update frontend/src/lib/rosters.json from the official FIFA WC 2026 squad PDF.
Run from repo root: python scripts/update_rosters_from_pdf.py
"""
import json, os, re, subprocess, sys, tempfile, unicodedata, warnings
from collections import defaultdict
from datetime import date
from pathlib import Path

import pdfplumber
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

TOURNAMENT_DATE = date(2026, 6, 11)
PDF_URL = "https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf"
ROSTERS_PATH = Path("frontend/src/lib/rosters.json")

POS_TO_KEY = {"GK": "goalkeepers", "DF": "defenders", "MF": "midfielders", "FW": "forwards"}

# PDF team name → rosters.json key (for names that differ)
PDF_NAME_OVERRIDES: dict[str, str] = {
    "Cabo Verde": "Cape Verde Islands",
    "Congo DR": "DR Congo",
    "Türkiye": "Turkey",
    "USA": "United States",
    "Bosnia And Herzegovina": "Bosnia and Herzegovina",
}


def calc_age(dob_str: str, ref_date: date) -> int:
    """'DD/MM/YYYY' → age in whole years at ref_date."""
    d, m, y = map(int, dob_str.split("/"))
    born = date(y, m, d)
    age = ref_date.year - born.year
    if (ref_date.month, ref_date.day) < (born.month, born.day):
        age -= 1
    return age


def title_case_name(caps: str) -> str:
    """'HADJ MOUSSA' → 'Hadj Moussa', 'AÏT-NOURI' → 'Aït-Nouri'."""
    def cap_part(s: str) -> str:
        return "-".join(w.capitalize() for w in s.split("-"))
    return " ".join(cap_part(w) for w in caps.split())


def strip_club_country(club: str) -> str:
    """'Lille OSC (FRA)' → 'Lille OSC'."""
    return re.sub(r"\s+\([A-Z]{3}\)\s*$", "", club).strip()


def normalize_for_match(name: str) -> str:
    """Accent-strip, lowercase, sort tokens — for fuzzy player matching."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    tokens = sorted(re.sub(r"[^a-z0-9 ]", "", ascii_name.lower()).split())
    return " ".join(tokens)
