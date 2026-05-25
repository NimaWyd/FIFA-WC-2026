"""
Download manager (and optionally player) photos from Wikipedia.

Usage (run from repo root):
    python scripts/download_manager_images.py

Saves:
    frontend/public/players/m{sofascore_id}.jpg   managers
    frontend/public/players/p{sofascore_id}.jpg   players without ESPN id (--players flag)

Run with --players to also attempt downloading images for players who have a
sofascore_id but no espn_id.
"""

import json
import sys
import time
import unicodedata
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

ROSTERS_PATH = Path("frontend/src/lib/rosters.json")
OUT_DIR = Path("frontend/public/players")
HEADERS = {"User-Agent": "FIFA-WC-2026-App/1.0 (educational; github.com/nimaa)"}
DELAY = 0.6
MAX_RETRIES = 3


def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def wiki_summary(title: str) -> dict | None:
    """Fetch Wikipedia REST summary for a page title, return JSON or None."""
    encoded = requests.utils.quote(title.replace(" ", "_"), safe="")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                continue
            return None
        except Exception:
            time.sleep(1)
    return None


def find_thumbnail(name: str, extra_terms: list[str] | None = None) -> str | None:
    """Try several Wikipedia title variants; return thumbnail URL or None."""
    ascii_name = normalize(name)
    candidates = [name, ascii_name]

    if extra_terms:
        for term in extra_terms:
            candidates += [f"{name} ({term})", f"{ascii_name} ({term})"]

    seen = set()
    for title in candidates:
        if title in seen:
            continue
        seen.add(title)

        data = wiki_summary(title)
        time.sleep(DELAY)

        if not data:
            continue

        # Reject disambiguation pages
        if data.get("type") == "disambiguation":
            continue

        thumb = data.get("thumbnail", {}).get("source")
        if thumb:
            return thumb

    return None


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if r.status_code == 200 and len(r.content) > 1000:
            dest.write_bytes(r.content)
            return True
        return False
    except Exception:
        return False


def process_batch(jobs: list[tuple[str, str, Path]], label: str):
    total = len(jobs)
    ok = skipped = failed = 0

    for i, (name, search_name, dest) in enumerate(jobs, 1):
        if dest.exists():
            skipped += 1
            continue

        thumb = find_thumbnail(search_name, extra_terms=["football manager", "footballer"])

        if thumb:
            if download_image(thumb, dest):
                ok += 1
                print(f"  [{i}/{total}] OK  {name}")
            else:
                failed += 1
                print(f"  [{i}/{total}] ERR download failed: {name}")
        else:
            failed += 1
            print(f"  [{i}/{total}] --- not found: {name}")

        time.sleep(DELAY)

    print(f"\n{label}: {ok} downloaded, {skipped} skipped, {failed} not found/failed\n")


def main():
    include_players = "--players" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(ROSTERS_PATH, encoding="utf-8") as f:
        rosters = json.load(f)

    # --- Managers ---
    manager_jobs: list[tuple[str, str, Path]] = []
    for team, roster in rosters.items():
        sid = roster.get("manager_sofascore_id")
        mgr = roster.get("manager")
        if sid and mgr:
            dest = OUT_DIR / f"m{sid}.jpg"
            manager_jobs.append((f"{mgr} ({team})", mgr, dest))

    print(f"=== Managers ({len(manager_jobs)}) ===")
    process_batch(manager_jobs, "Managers")

    if not include_players:
        print("Skipping players (pass --players to include them).")
        return

    # --- Players without ESPN id ---
    player_jobs: list[tuple[str, str, Path]] = []
    for team, roster in rosters.items():
        if roster.get("released") is False:
            continue
        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            for p in roster.get(pos, []):
                if p.get("sofascore_id") and not p.get("espn_id"):
                    dest = OUT_DIR / f"p{p['sofascore_id']}.jpg"
                    player_jobs.append((f"{p['name']} ({team})", p["name"], dest))

    print(f"=== Players without ESPN id ({len(player_jobs)}) ===")
    process_batch(player_jobs, "Players")


if __name__ == "__main__":
    main()
