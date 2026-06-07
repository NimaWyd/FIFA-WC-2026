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


DOB_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
COUNTRY_CODE_RE = re.compile(r"^\([A-Z]{3}\)$")


def extract_col_bounds(header_words: list[dict]) -> tuple[float, float, float, float]:
    """
    Extract column x-boundaries from the table header row.

    The header row contains tokens like:
      '#' 'POS' 'PLAYER' 'NAME' 'FIRST' 'NAME(S)' 'LAST' 'NAME(S)' 'NAME' 'ON' 'SHIRT' 'DOB' ...

    Column data is left-aligned within each column and sits up to ~40 px to the
    LEFT of its header label.  We apply fixed left-guards when computing boundaries:

      first-last boundary = x_last - 40  (last-name data can be 36 px left of 'LAST')
      last-shirt boundary = x_shirt - 30 (shirt-name data is 0-23 px left of 'SHIRT')

    Returns (x_12, x_23, x_34, x_dob):
      x_12  = boundary between PLAYER-NAME and FIRST-NAME zones
      x_23  = boundary between FIRST-NAME and LAST-NAME zones  (x_last - 40)
      x_34  = boundary between LAST-NAME and SHIRT-NAME zones  (x_shirt - 30)
      x_dob = hard right boundary (DOB column start)
    """
    tokens = sorted(header_words, key=lambda w: w["x0"])
    x_player = x_first = x_last = x_shirt = x_dob = None
    for w in tokens:
        t = w["text"]
        if t == "PLAYER" and x_player is None:
            x_player = w["x0"]
        elif t == "FIRST" and x_first is None:
            x_first = w["x0"]
        elif t == "LAST" and x_last is None:
            x_last = w["x0"]
        elif t == "SHIRT" and x_shirt is None:
            x_shirt = w["x0"]
        elif t == "DOB" and x_dob is None:
            x_dob = w["x0"]
    if None in (x_player, x_first, x_last, x_shirt, x_dob):
        raise ValueError(f"Cannot extract col bounds from header: {[w['text'] for w in tokens]}")
    x_12 = (x_player + x_first) / 2  # midpoint — no data lives here, so exact value matters less
    x_23 = x_last - 40               # left edge of last-name data (max 36 px left of 'LAST' header)
    x_34 = x_shirt - 30              # left edge of shirt-name data (max 23 px left of 'SHIRT' header)
    return x_12, x_23, x_34, x_dob


def parse_player_words(words: list[dict], ref_date: date,
                       col_bounds: tuple[float, float, float, float]) -> dict:
    """
    Parse one player row using column boundaries derived from the page header.

    col_bounds = (x_12, x_23, x_34, x_dob) from extract_col_bounds().

    Column assignment (left → right):
      x < x_12            → shirt# / POS → skip
      x_12 <= x < x_23   → PLAYER-NAME display → skip
      x_23 <= x < x_34   → FIRST NAME(S) → keep as first_names
      x_34 <= x < x_23+Δ → LAST NAME(S) → keep as last_name_parts
                            (x_23+Δ chosen so LAST data falls here; anything ≥ x_34 is shirt-name)

    Wait — re-reading the layout:
      Col 1 = PLAYER NAME (display)   → x < x_23
      Col 2 = FIRST NAME(S)           → x_23 <= x < x_34   (between left of LAST and left of SHIRT)

    Actually: data columns are:
      Display  [left of x_first data start]
      First    [x_first data start .. x_last data start)
      Last     [x_last data start  .. x_shirt data start)
      Shirt    [x_shirt data start .. DOB)

    x_23 = x_last - 40  → left edge of last-name = right edge of first-name
    x_34 = x_shirt - 30 → left edge of shirt-name = right edge of last-name

    So:
      first_names:  x_12 <= x < x_23   (after display, before last-name)
      last_names:   x_23 <= x < x_34   (after last-name start, before shirt-name)
    """
    x_12, x_23, x_34, x_dob = col_bounds

    tokens = [(w["x0"], w["text"].replace("\x00", "")) for w in words]

    pos = None
    dob: str | None = None
    dob_idx = None

    for i, (x, t) in enumerate(tokens):
        if t in POS_TO_KEY and pos is None:
            pos = t
        if DOB_RE.match(t):
            dob = t
            dob_idx = i
            break

    if pos is None or dob is None or dob_idx is None:
        raise ValueError(f"Could not locate POS or DOB in row: {tokens}")

    first_names: list[str] = []
    last_name_parts: list[str] = []

    for i, (x, t) in enumerate(tokens):
        if i >= dob_idx:
            break
        if x_12 <= x < x_23:
            first_names.append(t)
        elif x_23 <= x < x_34:
            last_name_parts.append(t)
        # x < x_12   → shirt# / POS → skip
        # x >= x_34  → shirt-name → skip

    # Club: tokens after DOB, skipping country code (XXX) and HEIGHT (integer)
    club_parts: list[str] = []
    for i in range(dob_idx + 1, len(tokens)):
        x, t = tokens[i]
        if COUNTRY_CODE_RE.match(t):
            continue
        if re.match(r"^\d{2,3}$", t):  # HEIGHT cm
            break
        club_parts.append(t)

    last = title_case_name(" ".join(last_name_parts))
    display_name = (" ".join(first_names) + " " + last).strip()

    return {
        "name": display_name,
        "position_key": POS_TO_KEY[pos],
        "age": calc_age(dob, ref_date),
        "club": strip_club_country(" ".join(club_parts)),
    }


def parse_coach_words(words: list[dict], col_bounds: tuple[float, float] = (181, 267)) -> str:
    """
    Parse the 'Head coach' row using coach-specific column boundaries.

    Coach columns differ from player columns. Algeria reference positions:
      - Coach first_names: x ∈ [181, 267)
      - Coach last_name:   x ∈ [267, 351)
      - Nationality:       x ≥ 351

    Empirically other teams shift first/last starting positions by ±20px
    (e.g. Argentina first=168/last=263, Spain first=162/last=238). We widen
    the acceptance bands so all 48 coaches parse correctly while still
    excluding the leftmost display-name columns (x < 160) and the
    rightmost nationality column (x ≥ 345).
    """
    tokens = [(w["x0"], w["text"].replace("\x00", "")) for w in words]
    x_first, x_last = col_bounds
    # Widen first-name lower bound to admit teams whose name col starts left of 181
    # (e.g. Argentina=168, Mexico=159, Spain=162, Korea=169). Anything below 155
    # is still in the leftmost display-name column.
    x_first_lo = min(x_first, 155)
    x_last_lo = min(x_last, 230)

    # Detect nationality column: the last big horizontal gap (>40 px) between
    # consecutive tokens with x >= x_first_lo marks the start of nationality.
    # Some teams have nationality starting as low as x≈310 (Bosnia) which
    # overlaps the static [230, 345) last-name band, so use the gap instead.
    sorted_right = sorted(((x, t) for x, t in tokens if x >= x_first_lo), key=lambda p: p[0])
    x_nat: float = float("inf")
    for i in range(1, len(sorted_right)):
        prev_x = sorted_right[i - 1][0]
        cur_x = sorted_right[i][0]
        if cur_x - prev_x > 40 and prev_x >= x_last_lo:
            x_nat = cur_x
            break
    if x_nat == float("inf"):
        x_nat = 345  # fallback

    first_parts: list[str] = []
    last_parts: list[str] = []

    for x, t in tokens:
        if x_first_lo <= x < x_last_lo:
            first_parts.append(t)
        elif x_last_lo <= x < x_nat:
            last_parts.append(t)

    last = title_case_name(" ".join(last_parts))
    return (" ".join(first_parts) + " " + last).strip()


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

    # Extract column boundaries from the header row (contains '#', 'FIRST', 'LAST', 'DOB')
    col_bounds: tuple[float, float, float] | None = None
    for y in sorted_ys:
        line_words = sorted(lines[y], key=lambda w: w["x0"])
        texts = [w["text"] for w in line_words]
        if "FIRST" in texts and "LAST" in texts and "DOB" in texts:
            try:
                col_bounds = extract_col_bounds(line_words)
            except Exception:
                pass
            break

    if col_bounds is None:
        print(f"  WARN: could not extract column bounds for {team_name}")
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
                row = parse_player_words(line_words, ref_date, col_bounds)
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
                manager = parse_coach_words(line_words, (181, 267))
            except Exception as exc:
                print(f"  WARN: failed to parse coach row: {exc}")

    return {"team_name": team_name, "players": players, "manager": manager}


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
    finally:
        os.close(tmp_fd)

    try:
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
