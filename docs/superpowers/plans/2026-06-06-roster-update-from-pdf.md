# Roster Update from FIFA PDF — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write `scripts/update_rosters_from_pdf.py` that downloads the official FIFA WC 2026 squad PDF, parses all 48 team pages, rebuilds `frontend/src/lib/rosters.json` with correct names/ages/clubs, preserves existing `espn_id`/`sofascore_id` via fuzzy-match, then optionally runs the FotMob image downloader.

**Architecture:** Use `pdfplumber`'s `extract_words()` to get per-word bounding boxes; assign each word to its PDF column by x-coordinate (verified from the actual file — positions are fixed across all 48 pages). Pure helper functions handle name casing, age math, club stripping, and fuzzy ID matching independently of I/O so they can be unit-tested without touching the PDF.

**Tech Stack:** Python 3.11, `pdfplumber` (already installed), `requests`, `json`, `unicodedata`, `re`, `datetime`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `scripts/update_rosters_from_pdf.py` | Create | Main script — download, parse, merge, write |
| `tests/test_update_rosters.py` | Create | Unit tests for all pure helper functions |
| `frontend/src/lib/rosters.json` | Modified at runtime | Rewritten by the script |

---

## Column x-boundaries (verified from Algeria page)

```
Player rows:  first_names ≥102  last_name ≥180  shirt ≥227  dob ≥282  club ≥310  height ≥405
Coach rows:   first_names ≥181  last_name ≥267  nationality ≥351
```

---

## Task 1 — Core helper functions (TDD)

**Files:**
- Create: `scripts/update_rosters_from_pdf.py` (skeleton + helpers only)
- Create: `tests/test_update_rosters.py`

- [ ] **Step 1.1 — Create the test file with failing tests**

```python
# tests/test_update_rosters.py
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
```

- [ ] **Step 1.2 — Run tests to confirm they all fail**

```bash
cd C:\Users\Nimaa\Projects\FIFA-WC-2026
python -m pytest tests/test_update_rosters.py -v 2>&1 | head -40
```

Expected: `ImportError` or `ModuleNotFoundError` (script doesn't exist yet).

- [ ] **Step 1.3 — Create the script with just the helper functions**

```python
# scripts/update_rosters_from_pdf.py
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
```

- [ ] **Step 1.4 — Run tests, confirm helpers pass**

```bash
python -m pytest tests/test_update_rosters.py -v
```

Expected: All 12 tests **PASS**.

- [ ] **Step 1.5 — Commit**

```bash
git add scripts/update_rosters_from_pdf.py tests/test_update_rosters.py
git commit -m "feat(rosters): add helper functions for PDF roster update"
```

---

## Task 2 — Word-row parsers (TDD)

These turn a list of `{"text": str, "x0": float}` dicts (one PDF line) into structured data.

**Files:**
- Modify: `scripts/update_rosters_from_pdf.py` — add `parse_player_words`, `parse_coach_words`
- Modify: `tests/test_update_rosters.py` — add word-row tests

- [ ] **Step 2.1 — Add failing tests for `parse_player_words` and `parse_coach_words`**

Append to `tests/test_update_rosters.py`:

```python
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

class TestParsePlayerWords:
    def test_simple_name(self):
        r = parse_player_words(MANDI_WORDS, TOURNAMENT)
        assert r["name"] == "Aissa Mandi"
        assert r["position_key"] == "defenders"
        assert r["age"] == 34
        assert r["club"] == "Lille OSC"

    def test_compound_last_name(self):
        r = parse_player_words(HADJ_MOUSSA_WORDS, TOURNAMENT)
        assert r["name"] == "Anis Hadj Moussa"
        assert r["position_key"] == "forwards"
        assert r["club"] == "Feyenoord Rotterdam"

    def test_accented_last_name_uses_last_name_col(self):
        r = parse_player_words(BELAID_WORDS, TOURNAMENT)
        # LAST NAME col has BELAÏD (accented), SHIRT col has BELAID — use LAST NAME
        assert r["name"] == "Zineddine Belaïd"

class TestParseCoachWords:
    def test_coach_name(self):
        assert parse_coach_words(PETKOVIC_WORDS) == "Vladimir Petković"
```

- [ ] **Step 2.2 — Run to confirm tests fail**

```bash
python -m pytest tests/test_update_rosters.py::TestParsePlayerWords tests/test_update_rosters.py::TestParseCoachWords -v
```

Expected: `ImportError` — functions not defined yet.

- [ ] **Step 2.3 — Add `parse_player_words` and `parse_coach_words` to the script**

Add after the `normalize_for_match` function:

```python
def parse_player_words(words: list[dict], ref_date: date) -> dict:
    """
    Parse one player row (list of word dicts with 'text' and 'x0') into structured data.
    Column boundaries determined from Algeria page of the actual PDF:
      first_names x∈[102,180)  last_name x∈[180,227)  dob x∈[282,310)  club x∈[310,405)
    """
    pos = None
    first_names: list[str] = []
    last_name_parts: list[str] = []
    dob: str | None = None
    club_parts: list[str] = []

    for w in words:
        x, t = w["x0"], w["text"].replace("\x00", "")
        if t in POS_TO_KEY:
            pos = t
        elif 102 <= x < 180:
            first_names.append(t)
        elif 180 <= x < 227:
            last_name_parts.append(t)
        elif 282 <= x < 310:
            dob = t
        elif 310 <= x < 405:
            club_parts.append(t)

    last = title_case_name(" ".join(last_name_parts))
    display_name = (" ".join(first_names) + " " + last).strip()
    return {
        "name": display_name,
        "position_key": POS_TO_KEY[pos],
        "age": calc_age(dob, ref_date),
        "club": strip_club_country(" ".join(club_parts)),
    }


def parse_coach_words(words: list[dict]) -> str:
    """
    Parse the 'Head coach' row. Coach column boundaries:
      first_names x∈[181,267)  last_name x∈[267,351)
    """
    first_names: list[str] = []
    last_name_parts: list[str] = []
    for w in words:
        x, t = w["x0"], w["text"].replace("\x00", "")
        if 181 <= x < 267:
            first_names.append(t)
        elif 267 <= x < 351:
            last_name_parts.append(t)
    last = title_case_name(" ".join(last_name_parts))
    return (" ".join(first_names) + " " + last).strip()
```

- [ ] **Step 2.4 — Run tests, confirm they pass**

```bash
python -m pytest tests/test_update_rosters.py -v
```

Expected: All tests **PASS**.

- [ ] **Step 2.5 — Commit**

```bash
git add scripts/update_rosters_from_pdf.py tests/test_update_rosters.py
git commit -m "feat(rosters): add word-position row parsers for player and coach"
```

---

## Task 3 — Page parser + fuzzy ID matcher (TDD)

**Files:**
- Modify: `scripts/update_rosters_from_pdf.py` — add `parse_page`, `find_best_match`, `resolve_team_key`
- Modify: `tests/test_update_rosters.py` — add tests

- [ ] **Step 3.1 — Add failing tests**

Append to `tests/test_update_rosters.py`:

```python
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
```

- [ ] **Step 3.2 — Run to confirm tests fail**

```bash
python -m pytest tests/test_update_rosters.py::TestFindBestMatch tests/test_update_rosters.py::TestResolveTeamKey -v
```

Expected: `ImportError`.

- [ ] **Step 3.3 — Add `find_best_match`, `resolve_team_key`, and `parse_page` to the script**

Add after `parse_coach_words`:

```python
def find_best_match(new_name: str, existing_players: list[dict]) -> dict:
    """
    Fuzzy-match new_name against existing player list.
    Returns dict of IDs to copy (espn_id, sofascore_id) — empty dict if no match.
    Threshold: token-set similarity ≥ 0.6 after accent-stripping.
    """
    key_new = normalize_for_match(new_name)
    tokens_new = set(key_new.split())
    best_score, best_player = 0.0, None
    for p in existing_players:
        tokens_old = set(normalize_for_match(p.get("name", "")).split())
        if not tokens_new or not tokens_old:
            continue
        sim = len(tokens_new & tokens_old) / max(len(tokens_new), len(tokens_old))
        if sim > best_score:
            best_score, best_player = sim, p
    if best_score < 0.6 or best_player is None:
        return {}
    return {k: best_player[k] for k in ("espn_id", "sofascore_id") if best_player.get(k)}


def resolve_team_key(pdf_name: str, rosters: dict) -> str | None:
    """Map a PDF team name to the corresponding rosters.json key."""
    if pdf_name in PDF_NAME_OVERRIDES:
        candidate = PDF_NAME_OVERRIDES[pdf_name]
        return candidate if candidate in rosters else None
    if pdf_name in rosters:
        return pdf_name
    pdf_lower = pdf_name.lower()
    for key in rosters:
        if key.lower() == pdf_lower:
            return key
    return None


def parse_page(page, ref_date: date) -> dict | None:
    """
    Parse one PDF page into {team_name, players, manager}.
    players is a dict keyed by position (goalkeepers/defenders/midfielders/forwards).
    """
    words_raw = page.extract_words(x_tolerance=3, y_tolerance=3)
    if not words_raw:
        return None

    lines: defaultdict[int, list] = defaultdict(list)
    for w in words_raw:
        lines[round(w["top"])].append(w)

    sorted_ys = sorted(lines)

    # Find team name: line matching "Team Name (XXX)"
    team_name = None
    for y in sorted_ys[:8]:
        line_words = sorted(lines[y], key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in line_words)
        m = re.search(r"^(.+?)\s+\([A-Z]{3}\)$", text.strip())
        if m:
            team_name = m.group(1).strip()
            break
    if not team_name:
        return None

    players: dict[str, list] = {k: [] for k in POS_TO_KEY.values()}
    manager: str | None = None

    for y in sorted_ys:
        line_words = sorted(lines[y], key=lambda w: w["x0"])
        if not line_words:
            continue
        first = line_words[0]["text"]

        # Player row: first token is shirt number 1-26
        if re.match(r"^\d{1,2}$", first) and 1 <= int(first) <= 26:
            try:
                row = parse_player_words(line_words, ref_date)
                players[row["position_key"]].append({
                    "name": row["name"],
                    "club": row["club"],
                    "age":  row["age"],
                })
            except Exception as exc:
                print(f"  WARN: failed to parse player row '{first}': {exc}")

        # Coach row: starts with "Head"
        elif first == "Head":
            try:
                manager = parse_coach_words(line_words)
            except Exception as exc:
                print(f"  WARN: failed to parse coach row: {exc}")

    return {"team_name": team_name, "players": players, "manager": manager}
```

- [ ] **Step 3.4 — Run all tests**

```bash
python -m pytest tests/test_update_rosters.py -v
```

Expected: All tests **PASS**.

- [ ] **Step 3.5 — Commit**

```bash
git add scripts/update_rosters_from_pdf.py tests/test_update_rosters.py
git commit -m "feat(rosters): add page parser, fuzzy ID matcher, team name resolver"
```

---

## Task 4 — Main script (download → parse → merge → write → prompt)

**Files:**
- Modify: `scripts/update_rosters_from_pdf.py` — add `main()` and `if __name__ == "__main__"` block

- [ ] **Step 4.1 — Add `main()` to the script**

Append to `scripts/update_rosters_from_pdf.py`:

```python
def main() -> None:
    # ── 1. Load existing rosters for ID preservation ────────────────────────────
    with open(ROSTERS_PATH, encoding="utf-8") as f:
        old_rosters: dict = json.load(f)

    all_old_players_by_team: dict[str, list] = {}
    for team, roster in old_rosters.items():
        pool = []
        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            pool.extend(roster.get(pos, []))
        all_old_players_by_team[team] = pool

    # ── 2. Download PDF ─────────────────────────────────────────────────────────
    print(f"Downloading PDF from {PDF_URL} …")
    response = requests.get(PDF_URL, timeout=60)
    response.raise_for_status()
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        os.write(tmp_fd, response.content)
        os.close(tmp_fd)
        print(f"  Downloaded {len(response.content) // 1024} KB → {tmp_path}")

        # ── 3. Parse all 48 pages ────────────────────────────────────────────────
        new_rosters: dict = {}
        unmapped: list[str] = []

        with pdfplumber.open(tmp_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                data = parse_page(page, TOURNAMENT_DATE)
                if not data:
                    print(f"  [page {i:2}] SKIP (no data)")
                    continue

                roster_key = resolve_team_key(data["team_name"], old_rosters)
                if not roster_key:
                    print(f"  [page {i:2}] UNMAPPED: {data['team_name']!r}")
                    unmapped.append(data["team_name"])
                    continue

                old_pool = all_old_players_by_team.get(roster_key, [])

                # ── 4. Merge IDs into new players ────────────────────────────────
                for player_list in data["players"].values():
                    for player in player_list:
                        player.update(find_best_match(player["name"], old_pool))

                old = old_rosters.get(roster_key, {})
                entry: dict = {"manager": data["manager"] or old.get("manager")}
                if old.get("manager_sofascore_id"):
                    entry["manager_sofascore_id"] = old["manager_sofascore_id"]
                entry.update(data["players"])
                new_rosters[roster_key] = entry

                n_players = sum(len(v) for v in data["players"].values())
                n_with_id = sum(
                    1 for v in data["players"].values()
                    for p in v if p.get("sofascore_id")
                )
                print(f"  [page {i:2}] {roster_key}: {n_players} players, {n_with_id} with sofascore_id")

    finally:
        os.unlink(tmp_path)

    # ── 5. Write updated rosters.json ───────────────────────────────────────────
    with open(ROSTERS_PATH, "w", encoding="utf-8") as f:
        json.dump(new_rosters, f, ensure_ascii=False, indent=2)

    total = sum(
        len(t.get(p, []))
        for t in new_rosters.values()
        for p in ("goalkeepers", "defenders", "midfielders", "forwards")
    )
    with_sid = sum(
        1
        for t in new_rosters.values()
        for p in ("goalkeepers", "defenders", "midfielders", "forwards")
        for pl in t.get(p, [])
        if pl.get("sofascore_id")
    )

    print(f"\n{'─'*60}")
    print(f"Teams   : {len(new_rosters)} / 48")
    print(f"Players : {total}")
    print(f"With sofascore_id : {with_sid}  ({total - with_sid} without)")
    if unmapped:
        print(f"UNMAPPED teams    : {unmapped}")
    print(f"Saved → {ROSTERS_PATH}")

    # ── 6. Offer FotMob download ─────────────────────────────────────────────────
    print()
    ans = input("Run download_player_images.py now? (takes ~15–20 min) [y/N]: ").strip().lower()
    if ans == "y":
        subprocess.run([sys.executable, "scripts/download_player_images.py"], check=False)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4.2 — Verify tests still pass after adding main()**

```bash
python -m pytest tests/test_update_rosters.py -v
```

Expected: All tests **PASS**.

- [ ] **Step 4.3 — Commit**

```bash
git add scripts/update_rosters_from_pdf.py
git commit -m "feat(rosters): add main() — download, parse, merge, write rosters.json"
```

---

## Task 5 — End-to-end run + verify

- [ ] **Step 5.1 — Run the script (dry run first — inspect output before writing)**

Run and watch the page-by-page output:

```bash
python scripts/update_rosters_from_pdf.py
```

Expected per-page lines:
```
  [page  1] Algeria: 26 players, N with sofascore_id
  [page  2] Argentina: 26 players, N with sofascore_id
  ...
  [page 48] Uzbekistan: 26 players, N with sofascore_id
```

If any team shows `UNMAPPED`, add it to `PDF_NAME_OVERRIDES` in the script and re-run.

- [ ] **Step 5.2 — Verify rosters.json sanity**

```bash
python -c "
import json
r = json.load(open('frontend/src/lib/rosters.json', encoding='utf-8'))
print('Teams:', len(r))
total = sum(len(t.get(p,[])) for t in r.values() for p in ['goalkeepers','defenders','midfielders','forwards'])
with_sid = sum(1 for t in r.values() for p in ['goalkeepers','defenders','midfielders','forwards'] for pl in t.get(p,[]) if pl.get('sofascore_id'))
print('Players:', total, '  With sofascore_id:', with_sid)
# Check age range is plausible
ages = [pl['age'] for t in r.values() for p in ['goalkeepers','defenders','midfielders','forwards'] for pl in t.get(p,[])]
print('Age range:', min(ages), '-', max(ages))
# Spot-check a player
arg = r.get('Argentina', {})
print('Argentina GKs:', [p['name'] for p in arg.get('goalkeepers',[])])
"
```

Expected:
- Teams: 48
- Players: 1248 (48 × 26)
- Age range: ~16–42
- Argentina GKs include "Juan Musso" (or similar)

- [ ] **Step 5.3 — Answer the FotMob download prompt**

When the script asks `Run download_player_images.py now? [y/N]`:
- Type `y` to download immediately (takes ~15–20 min), or
- Type `N` to skip and run `python scripts/download_player_images.py` separately later

- [ ] **Step 5.4 — Commit rosters.json**

```bash
git add frontend/src/lib/rosters.json
git commit -m "data(rosters): rebuild all 48 squads from official FIFA WC 2026 PDF"
```

- [ ] **Step 5.5 — Commit any fixes needed (conditional)**

If Step 5.1 required adding entries to `PDF_NAME_OVERRIDES` for unmapped teams, commit those:

```bash
git add scripts/update_rosters_from_pdf.py
git commit -m "fix(rosters): add PDF_NAME_OVERRIDES for unmapped teams"
```

If no changes were needed (all 48 teams resolved), skip this step.
