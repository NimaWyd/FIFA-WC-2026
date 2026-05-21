"""
Parse ESPN WC 2026 squad article text into rosters.json.

Usage:
    python scripts/parse_rosters.py

Reads:  espn_article.txt  (raw innerText from ESPN article)
Writes: frontend/src/lib/rosters.json
"""

import json
import re
import os

# ---------------------------------------------------------------------------
# ESPN name → canonical codebase name
# ---------------------------------------------------------------------------
ESPN_TO_CANONICAL = {
    "South Korea":       "Korea Republic",
    "Bosnia-Herzegovina":"Bosnia and Herzegovina",
    "Türkiye":           "Turkey",
    "Curacao":           "Curaçao",
    "Ivory Coast":       "Côte d'Ivoire",
    "Iran":              "IR Iran",
    "Cape Verde":        "Cape Verde Islands",
    "Congo DR":          "DR Congo",
}

CANONICAL_TEAMS = {
    "United States","Canada","Mexico","Germany","France","Spain","England",
    "Portugal","Netherlands","Belgium","Bosnia and Herzegovina","Croatia",
    "Czechia","Switzerland","Austria","Norway","Sweden","Turkey","Scotland",
    "Argentina","Brazil","Colombia","Uruguay","Ecuador","Paraguay",
    "Panama","Curaçao","Haiti","Morocco","Senegal","Egypt","Ghana",
    "Côte d'Ivoire","South Africa","DR Congo","Tunisia","Algeria",
    "Cape Verde Islands","Japan","Korea Republic","IR Iran","Australia",
    "Saudi Arabia","Iraq","Uzbekistan","Jordan","Qatar","New Zealand",
}


def parse_players(line: str) -> list[dict]:
    """Parse 'Name (Club), Name (Club), ...' into list of {name, club} dicts."""
    if not line.strip():
        return []
    players = []
    # Split on ), followed by optional whitespace and a comma or end
    # Pattern: "Name (Club)" repeated
    for m in re.finditer(r'([^,(]+?)\s*\(([^)]+)\)', line):
        name = m.group(1).strip().rstrip(',').strip()
        club = m.group(2).strip()
        if name:
            players.append({"name": name, "club": club})
    return players


def parse_article(text: str) -> dict:
    # Strip surrounding quotes if the file was saved as a JSON string
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        text = json.loads(text)

    rosters = {}

    # Split into lines
    lines = [l.strip() for l in text.replace('\\n', '\n').split('\n')]

    i = 0
    current_team = None
    current_roster = None

    position_keys = {
        "Goalkeepers": "goalkeepers",
        "Defenders":   "defenders",
        "Midfielders": "midfielders",
        "Forwards":    "forwards",
    }

    while i < len(lines):
        line = lines[i]

        # Detect GROUP headers (skip)
        if re.match(r'^GROUP\s+[A-L]$', line):
            i += 1
            continue

        # Detect team names
        candidate = ESPN_TO_CANONICAL.get(line, line)
        if candidate in CANONICAL_TEAMS:
            # Save previous team
            if current_team and current_roster is not None:
                rosters[current_team] = current_roster

            current_team = candidate
            current_roster = {
                "manager": "",
                "goalkeepers": [],
                "defenders": [],
                "midfielders": [],
                "forwards": [],
            }
            i += 1
            continue

        if current_roster is None:
            i += 1
            continue

        # Detect "Roster yet to be announced"
        if "yet to be announced" in line.lower():
            current_roster = {"released": False}
            i += 1
            continue

        # If already marked released, only look for manager
        if isinstance(current_roster, dict) and current_roster.get("released") is False:
            if line.startswith("Manager:"):
                mgr = line.replace("Manager:", "").strip()
                if mgr:
                    current_roster["manager"] = mgr
            i += 1
            continue

        # Position lines
        matched_pos = False
        for label, key in position_keys.items():
            if line.startswith(f"{label}:"):
                player_text = line[len(label)+1:].strip()
                current_roster[key] = parse_players(player_text)
                matched_pos = True
                break
        if matched_pos:
            i += 1
            continue

        # Manager
        if line.startswith("Manager:"):
            mgr = line.replace("Manager:", "").strip()
            if mgr:
                current_roster["manager"] = mgr
            i += 1
            continue

        i += 1

    # Save last team
    if current_team and current_roster is not None:
        rosters[current_team] = current_roster

    return rosters


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    article_path = os.path.join(repo_root, "espn_article.txt")
    output_path = os.path.join(repo_root, "frontend", "src", "lib", "rosters.json")

    with open(article_path, "r", encoding="utf-8") as f:
        text = f.read()

    rosters = parse_article(text)

    # Ensure every canonical team has an entry
    for team in CANONICAL_TEAMS:
        if team not in rosters:
            rosters[team] = {"released": False}

    # Stats
    released = [t for t, v in rosters.items() if not (isinstance(v, dict) and v.get("released") is False)]
    unreleased = [t for t, v in rosters.items() if isinstance(v, dict) and v.get("released") is False]

    print(f"Teams with rosters : {len(released)}")
    print(f"Teams not released : {len(unreleased)}")
    if unreleased:
        print("  Not released:", ", ".join(sorted(unreleased)))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rosters, f, ensure_ascii=False, indent=2)

    print(f"\nWritten to {output_path}")


if __name__ == "__main__":
    main()
