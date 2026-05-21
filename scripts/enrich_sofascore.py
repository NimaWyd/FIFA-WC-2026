"""
Match SofaScore player IDs into rosters.json using squad data fetched via browser.

Reads:
  sofascore_squads.json  — {canonicalTeam: [{id, name, shortName}]} from Playwright
  frontend/src/lib/rosters.json

Writes:
  frontend/src/lib/rosters.json  (adds sofascore_id to each matched player)
"""

import json, re, unicodedata, os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQUADS_PATH = os.path.join(REPO_ROOT, "sofascore_squads.json")
ROSTERS_PATH = os.path.join(REPO_ROOT, "frontend", "src", "lib", "rosters.json")


def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_name).strip().lower()


def token_similarity(a: str, b: str) -> float:
    ta = set(normalize(a).split())
    tb = set(normalize(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def best_match(player_name: str, candidates: list) -> int | None:
    best_id, best_score = None, 0.0
    for c in candidates:
        score = token_similarity(player_name, c["name"])
        # also try shortName
        if c.get("shortName"):
            score = max(score, token_similarity(player_name, c["shortName"]))
        if score > best_score:
            best_score = score
            best_id = c["id"]
    return best_id if best_score >= 0.5 else None


def main():
    with open(SQUADS_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    # Playwright saves evaluate() result as a JSON string when it returns JSON.stringify(...)
    squads = json.loads(raw) if isinstance(raw, str) else raw
    with open(ROSTERS_PATH, encoding="utf-8") as f:
        rosters = json.load(f)

    total = matched = already_had = 0

    for team, roster in rosters.items():
        if isinstance(roster, dict) and roster.get("released") is False:
            continue
        sf_players = squads.get(team, [])

        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            for player in roster.get(pos, []):
                total += 1
                if player.get("sofascore_id"):
                    already_had += 1
                    continue
                pid = best_match(player["name"], sf_players)
                if pid:
                    player["sofascore_id"] = str(pid)
                    matched += 1

    print(f"Total players : {total}")
    print(f"Already had   : {already_had}")
    print(f"Newly matched : {matched}")
    print(f"Still missing : {total - already_had - matched}")

    with open(ROSTERS_PATH, "w", encoding="utf-8") as f:
        json.dump(rosters, f, ensure_ascii=False, indent=2)
    print(f"\nWritten to {ROSTERS_PATH}")


if __name__ == "__main__":
    main()
