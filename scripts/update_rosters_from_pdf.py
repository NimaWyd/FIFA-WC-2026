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
