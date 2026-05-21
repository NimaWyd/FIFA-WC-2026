"""
Enrich rosters.json with ESPN player IDs and ages.

Reads:
  espn_player_links.json  — [{name, id, href}] from ESPN article
  frontend/src/lib/rosters.json

Writes:
  frontend/src/lib/rosters.json  (adds espn_id and age to each player)

Usage:
  python scripts/enrich_rosters.py
"""

import json, os, re, time, unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

BASE_API = "https://site.web.api.espn.com/apis/common/v3/sports/soccer/all/athletes/{id}"


def normalize(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace for fuzzy matching."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_name).strip().lower()


def fetch_age(player_id: str) -> int | None:
    url = BASE_API.format(id=player_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            athlete = data.get("athlete", data)
            return athlete.get("age")
    except Exception:
        return None


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    links_path = os.path.join(repo_root, "espn_player_links.json")
    rosters_path = os.path.join(repo_root, "frontend", "src", "lib", "rosters.json")

    with open(links_path, encoding="utf-8") as f:
        raw_links = json.load(f)

    with open(rosters_path, encoding="utf-8") as f:
        rosters = json.load(f)

    # Build lookup: normalized_name -> {id, name}
    # De-duplicate by keeping first occurrence
    name_to_espn: dict[str, dict] = {}
    for entry in raw_links:
        key = normalize(entry["name"])
        if key not in name_to_espn:
            name_to_espn[key] = {"id": entry["id"], "name": entry["name"]}

    print(f"ESPN links: {len(raw_links)} entries, {len(name_to_espn)} unique names")

    # Collect all unique IDs we need ages for
    unique_ids: set[str] = {v["id"] for v in name_to_espn.values()}
    print(f"Fetching ages for {len(unique_ids)} unique player IDs…")

    id_to_age: dict[str, int | None] = {}

    def fetch(pid):
        age = fetch_age(pid)
        return pid, age

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(fetch, pid): pid for pid in unique_ids}
        done = 0
        for future in as_completed(futures):
            pid, age = future.result()
            id_to_age[pid] = age
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(unique_ids)} fetched…")

    print(f"Ages fetched. Missing: {sum(1 for a in id_to_age.values() if a is None)}")

    # Enrich rosters
    matched = 0
    unmatched = []

    for team, roster in rosters.items():
        if isinstance(roster, dict) and roster.get("released") is False:
            continue
        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            for player in roster.get(pos, []):
                key = normalize(player["name"])
                if key in name_to_espn:
                    espn = name_to_espn[key]
                    player["espn_id"] = espn["id"]
                    age = id_to_age.get(espn["id"])
                    if age is not None:
                        player["age"] = age
                    matched += 1
                else:
                    unmatched.append(player["name"])

    print(f"\nMatched: {matched} players")
    if unmatched:
        print(f"Unmatched ({len(unmatched)}):", ", ".join(unmatched[:20]))

    with open(rosters_path, "w", encoding="utf-8") as f:
        json.dump(rosters, f, ensure_ascii=False, indent=2)

    print(f"\nWritten to {rosters_path}")


if __name__ == "__main__":
    main()
