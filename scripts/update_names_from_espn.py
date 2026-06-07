"""
Update player names in rosters.json to use ESPN display names.

Parses scripts/espn_squads_clean.txt, matches players by position + token
similarity to existing roster entries, and replaces the name field.

Run from repo root:
    python scripts/update_names_from_espn.py
"""

import json
import re
import unicodedata
from pathlib import Path

ROSTERS_PATH = Path("frontend/src/lib/rosters.json")
ESPN_PATH    = Path("scripts/espn_squads_clean.txt")

# ESPN team name → rosters.json key
TEAM_MAP = {
    "Mexico":             "Mexico",
    "South Africa":       "South Africa",
    "South Korea":        "Korea Republic",
    "Czechia":            "Czech Republic",
    "Canada":             "Canada",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Qatar":              "Qatar",
    "Switzerland":        "Switzerland",
    "Brazil":             "Brazil",
    "Morocco":            "Morocco",
    "Haiti":              "Haiti",
    "Scotland":           "Scotland",
    "United States":      "United States",
    "Australia":          "Australia",
    "Paraguay":           "Paraguay",
    "Türkiye":            "Turkey",
    "Germany":            "Germany",
    "Curacao":            "Curaçao",
    "Ivory Coast":        "Côte d'Ivoire",
    "Ecuador":            "Ecuador",
    "Netherlands":        "Netherlands",
    "Japan":              "Japan",
    "Sweden":             "Sweden",
    "Tunisia":            "Tunisia",
    "Belgium":            "Belgium",
    "Egypt":              "Egypt",
    "Iran":               "Iran",
    "New Zealand":        "New Zealand",
    "Spain":              "Spain",
    "Cape Verde":         "Cape Verde Islands",
    "Saudi Arabia":       "Saudi Arabia",
    "Uruguay":            "Uruguay",
    "France":             "France",
    "Senegal":            "Senegal",
    "Iraq":               "Iraq",
    "Norway":             "Norway",
    "Argentina":          "Argentina",
    "Algeria":            "Algeria",
    "Austria":            "Austria",
    "Jordan":             "Jordan",
    "Portugal":           "Portugal",
    "Congo DR":           "DR Congo",
    "Uzbekistan":         "Uzbekistan",
    "Colombia":           "Colombia",
    "England":            "England",
    "Croatia":            "Croatia",
    "Ghana":              "Ghana",
    "Panama":             "Panama",
}

POS_MAP = {
    "Goalkeepers": "goalkeepers",
    "Defenders":   "defenders",
    "Midfielders": "midfielders",
    "Forwards":    "forwards",
}


# ── Text helpers ──────────────────────────────────────────────────────────────

def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    return re.sub(r"\s+", " ", "".join(
        c for c in nfkd if not unicodedata.combining(c)
    )).strip().lower()


def tokenize(name: str) -> set[str]:
    parts = re.split(r"[\s\-]+", normalize(name))
    tokens = set()
    i = 0
    while i < len(parts):
        tokens.add(parts[i])
        # Arabic article: "al owais" → also emit "alowais" for cross-format matching
        if parts[i] == "al" and i + 1 < len(parts):
            tokens.add("al" + parts[i + 1])
        i += 1
    return tokens


def tokens_match(a: str, b: str) -> bool:
    """True if tokens are equal or one is a prefix of the other (len >= 3)."""
    if a == b:
        return True
    if len(a) >= 3 and b.startswith(a):
        return True
    if len(b) >= 3 and a.startswith(b):
        return True
    return False


def token_sim(a: str, b: str) -> float:
    ta, tb = tokenize(a), tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def espn_recall(espn_name: str, roster_name: str) -> float:
    """
    Recall-based score: fraction of ESPN name tokens found in roster name.
    Works well when ESPN uses short display names vs long official names.
    Uses prefix matching so 'Dan'→'Daniel', 'Nico'→'Nicolas', etc.
    """
    ta = tokenize(espn_name)
    tb = tokenize(roster_name)
    if not ta or not tb:
        return 0.0
    matched = sum(1 for a in ta if any(tokens_match(a, b) for b in tb))
    return matched / len(ta)


def combined_sim(espn_name: str, roster_name: str) -> float:
    return max(token_sim(espn_name, roster_name), espn_recall(espn_name, roster_name))


# ── ESPN parser ───────────────────────────────────────────────────────────────

def parse_espn(text: str) -> dict[str, dict[str, list[str]]]:
    """
    Returns {espn_team_name: {position_key: [player_name, ...]}}
    """
    squads: dict[str, dict[str, list[str]]] = {}
    current_team: str | None = None
    current_pos:  str | None = None

    # Known section headers to skip
    skip_re = re.compile(
        r"^(GROUP [A-Z]|JUMP TO|ESPN|.*kick.*off|Nations were|The final|"
        r"World Cup:|2026 World|Here are|Group [A-L]:|\-\s|Open Extended|"
        r"Final (?:squad|roster)|Share|Like|\d+\.?\d*K?$)",
        re.IGNORECASE,
    )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or skip_re.match(line):
            continue

        # Position line: "Goalkeepers: Name (Club), ..."
        pos_match = re.match(r"^(Goalkeepers|Defenders|Midfielders|Forwards):\s*(.+)$", line)
        if pos_match and current_team:
            current_pos = POS_MAP[pos_match.group(1)]
            players_raw = pos_match.group(2)
            names = []
            for entry in players_raw.split(","):
                entry = entry.strip()
                # Strip club in parentheses: "Name (Club)" or "Name (Club)." or unclosed "Name (Club"
                name = re.sub(r"\s*\([^)]*\)?\s*$", "", entry).strip().rstrip(".")
                if name and "(" not in name:
                    names.append(name)
            squads.setdefault(current_team, {})[current_pos] = names
            continue

        # Manager line
        mgr_match = re.match(r"^Manager:\s*(.+)$", line)
        if mgr_match and current_team:
            squads.setdefault(current_team, {})["manager"] = mgr_match.group(1).strip()
            current_pos = None
            continue

        # Team name — single line not matching any pattern above, no colon
        if ":" not in line and current_pos is None and line in TEAM_MAP:
            current_team = line
            continue

        # Fallback: bare team name detection
        if ":" not in line and len(line.split()) <= 4:
            for espn_name in TEAM_MAP:
                if normalize(line) == normalize(espn_name):
                    current_team = espn_name
                    current_pos = None
                    break

    return squads


# ── Matching ──────────────────────────────────────────────────────────────────

def best_match(espn_name: str, roster_players: list[dict]) -> tuple[int, float]:
    """Return (index, score) of best-matching player in roster_players."""
    best_idx, best_score = -1, 0.0
    for i, p in enumerate(roster_players):
        s = token_sim(espn_name, p["name"])
        if s > best_score:
            best_score = s
            best_idx = i
    return best_idx, best_score


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    with open(ROSTERS_PATH, encoding="utf-8") as f:
        rosters = json.load(f)
    with open(ESPN_PATH, encoding="utf-8") as f:
        espn_text = f.read()

    espn_squads = parse_espn(espn_text)
    print(f"Parsed {len(espn_squads)} teams from ESPN\n")

    updated = 0
    unmatched: list[str] = []

    for espn_team, espn_data in espn_squads.items():
        roster_key = TEAM_MAP.get(espn_team)
        if not roster_key or roster_key not in rosters:
            print(f"  SKIP (no rosters key): {espn_team}")
            continue

        roster = rosters[roster_key]
        if roster.get("released") is False:
            continue

        # Update manager name
        if "manager" in espn_data:
            old = roster.get("manager", "")
            new = espn_data["manager"]
            if old != new:
                roster["manager"] = new
                print(f"  MGR  {espn_team}: '{old}' → '{new}'")
                updated += 1

        # Build a flat index of all players in this team across all positions
        # so we can match even when ESPN and our data disagree on position.
        # flat_index: list of (pos_key, player_dict, list_ref)
        flat_index: list[tuple[str, dict, list]] = []
        for pos_key in ("goalkeepers", "defenders", "midfielders", "forwards"):
            for p in roster.get(pos_key, []):
                flat_index.append((pos_key, p, roster[pos_key]))

        matched_players: set[int] = set()  # indices into flat_index

        for pos_key, espn_names in espn_data.items():
            if pos_key == "manager":
                continue

            for espn_name in espn_names:
                best_fi, best_score = -1, 0.0
                for fi, (_, p, _) in enumerate(flat_index):
                    if fi in matched_players:
                        continue
                    s = combined_sim(espn_name, p["name"])
                    if s > best_score:
                        best_score = s
                        best_fi = fi

                if best_fi == -1:
                    unmatched.append(f"{espn_team} / {pos_key} / {espn_name} (no candidates)")
                    continue

                if best_score >= 0.35:
                    matched_players.add(best_fi)
                    _, player, _ = flat_index[best_fi]
                    old_name = player["name"]
                    if old_name != espn_name:
                        player["name"] = espn_name
                        player.pop("fotmob_name", None)
                        print(f"  NAME {espn_team}: '{old_name}' → '{espn_name}'")
                        updated += 1
                else:
                    _, best_p, _ = flat_index[best_fi]
                    unmatched.append(
                        f"{espn_team} / {pos_key} / {espn_name} "
                        f"(best={best_p['name']} score={best_score:.2f})"
                    )

    with open(ROSTERS_PATH, "w", encoding="utf-8") as f:
        json.dump(rosters, f, ensure_ascii=False, indent=2)

    print(f"\nUpdated {updated} names in {ROSTERS_PATH}")

    if unmatched:
        print(f"\n{len(unmatched)} unmatched ESPN players:")
        for u in unmatched:
            print(f"  - {u}")


if __name__ == "__main__":
    main()
