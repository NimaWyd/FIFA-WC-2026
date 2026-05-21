"""
Enrich rosters.json with ESPN player IDs and ages.

Pass 1: match players linked in the ESPN article (espn_player_links.json)
Pass 2: search ESPN for remaining unmatched players via the search API

Reads:
  espn_player_links.json  — [{name, id}] from ESPN article
  frontend/src/lib/rosters.json

Writes:
  frontend/src/lib/rosters.json  (adds espn_id and age to each player)

Usage:
  python scripts/enrich_rosters.py
"""

import json, os, re, unicodedata, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

ATHLETE_API = "https://site.web.api.espn.com/apis/common/v3/sports/soccer/all/athletes/{id}"
SEARCH_API  = "https://site.api.espn.com/apis/search/v2?query={q}&limit=3&type=player"
HEADERS     = {"User-Agent": "Mozilla/5.0"}


def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_name).strip().lower()


def name_similarity(a: str, b: str) -> float:
    ta = set(normalize(a).split())
    tb = set(normalize(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def fetch_age(player_id: str) -> int | None:
    url = ATHLETE_API.format(id=player_id)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            athlete = data.get("athlete", data)
            return athlete.get("age")
    except Exception:
        return None


def search_espn(name: str) -> str | None:
    """Search ESPN for a player by name, return ESPN player ID or None."""
    q = urllib.parse.quote(name)
    url = SEARCH_API.format(q=q)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        for section in data.get("results", []):
            if section.get("type") != "player":
                continue
            for item in section.get("contents", []):
                result_name = item.get("displayName", "")
                if name_similarity(name, result_name) >= 0.75:
                    web_link = item.get("link", {}).get("web", "")
                    m = re.search(r"/id/(\d+)/", web_link)
                    if m:
                        return m.group(1)
        return None
    except Exception:
        return None


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    links_path   = os.path.join(repo_root, "espn_player_links.json")
    rosters_path = os.path.join(repo_root, "frontend", "src", "lib", "rosters.json")

    with open(links_path, encoding="utf-8") as f:
        raw_links = json.load(f)
    with open(rosters_path, encoding="utf-8") as f:
        rosters = json.load(f)

    # ── Pass 1: direct article link matching ─────────────────────────────────
    name_to_espn: dict[str, str] = {}
    for entry in raw_links:
        key = normalize(entry["name"])
        if key not in name_to_espn:
            name_to_espn[key] = entry["id"]

    print(f"Pass 1: {len(name_to_espn)} players from article links")

    pass1_matched, unmatched_players = [], []
    for team, roster in rosters.items():
        if isinstance(roster, dict) and roster.get("released") is False:
            continue
        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            for player in roster.get(pos, []):
                key = normalize(player["name"])
                if key in name_to_espn:
                    player["espn_id"] = name_to_espn[key]
                    pass1_matched.append(player)
                else:
                    unmatched_players.append(player)

    print(f"  Matched: {len(pass1_matched)} | Unmatched: {len(unmatched_players)}")

    # ── Pass 1b: fetch ages for article-linked players ────────────────────────
    unique_ids = {p["espn_id"] for p in pass1_matched}
    print(f"\nFetching ages for {len(unique_ids)} article-linked players…")
    id_to_age: dict[str, int | None] = {}

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(fetch_age, pid): pid for pid in unique_ids}
        done = 0
        for fut in as_completed(futures):
            pid, age = futures[fut], fut.result()
            id_to_age[pid] = age
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(unique_ids)}")

    for player in pass1_matched:
        age = id_to_age.get(player["espn_id"])
        if age is not None:
            player["age"] = age

    missing_ages = sum(1 for a in id_to_age.values() if a is None)
    print(f"  Ages fetched. Missing: {missing_ages}")

    # ── Pass 2: ESPN search for unmatched players ─────────────────────────────
    print(f"\nPass 2: searching ESPN for {len(unmatched_players)} unmatched players…")
    pass2_found, pass2_ids = 0, []

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(search_espn, p["name"]): p for p in unmatched_players}
        done = 0
        for fut in as_completed(futures):
            player = futures[fut]
            pid = fut.result()
            done += 1
            if pid:
                player["espn_id"] = pid
                pass2_ids.append(pid)
                pass2_found += 1
            if done % 50 == 0:
                print(f"  {done}/{len(unmatched_players)}")

    print(f"  Found: {pass2_found}/{len(unmatched_players)}")

    # Fetch ages for pass-2 players
    if pass2_ids:
        print(f"  Fetching ages for {len(pass2_ids)} pass-2 players…")
        with ThreadPoolExecutor(max_workers=15) as ex:
            futures = {ex.submit(fetch_age, pid): pid for pid in set(pass2_ids)}
            for fut in as_completed(futures):
                pid, age = futures[fut], fut.result()
                id_to_age[pid] = age

        for player in unmatched_players:
            if player.get("espn_id"):
                age = id_to_age.get(player["espn_id"])
                if age is not None:
                    player["age"] = age

    # ── Summary ───────────────────────────────────────────────────────────────
    still_missing = [p["name"] for p in unmatched_players if not p.get("espn_id")]
    total = len(pass1_matched) + len(unmatched_players)
    total_with_id = sum(1 for p in pass1_matched + unmatched_players if p.get("espn_id"))
    print(f"\nTotal players: {total} | With ESPN ID: {total_with_id} | No photo: {len(still_missing)}")
    if still_missing:
        print("No photo:", ", ".join(still_missing[:10]))

    with open(rosters_path, "w", encoding="utf-8") as f:
        json.dump(rosters, f, ensure_ascii=False, indent=2)
    print(f"\nWritten to {rosters_path}")


if __name__ == "__main__":
    main()
