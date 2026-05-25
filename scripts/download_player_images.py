"""
Download SofaScore player/manager images into frontend/public/players/.

Usage (run from repo root):
    python scripts/download_player_images.py

Images are saved as:
    frontend/public/players/p{sofascore_id}.jpg   (players)
    frontend/public/players/m{sofascore_id}.jpg   (managers)

Already-downloaded files are skipped automatically.
"""

import json
import time
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Install requests first:  pip install requests")

ROSTERS_PATH = Path("frontend/src/lib/rosters.json")
OUT_DIR = Path("frontend/public/players")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}
DELAY = 0.15  # seconds between requests to be polite


def fetch_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and r.content:
            dest.write_bytes(r.content)
            return True
        return False
    except Exception:
        return False


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(ROSTERS_PATH, encoding="utf-8") as f:
        rosters = json.load(f)

    # Collect all (id, type) pairs
    jobs: list[tuple[str, str]] = []  # (sofascore_id, "p" | "m")

    for team, roster in rosters.items():
        mgr_id = roster.get("manager_sofascore_id")
        if mgr_id:
            jobs.append((str(mgr_id), "m"))

        if roster.get("released") is False:
            continue

        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            for player in roster.get(pos, []):
                sid = player.get("sofascore_id")
                if sid:
                    jobs.append((str(sid), "p"))

    total = len(jobs)
    downloaded = skipped = failed = 0

    for i, (sid, kind) in enumerate(jobs, 1):
        dest = OUT_DIR / f"{kind}{sid}.jpg"

        if dest.exists():
            skipped += 1
            if i % 100 == 0:
                print(f"  [{i}/{total}] {skipped} skipped, {downloaded} downloaded, {failed} failed")
            continue

        entity = "player" if kind == "p" else "manager"
        url = f"https://api.sofascore.com/api/v1/{entity}/{sid}/image"

        ok = fetch_image(url, dest)
        if ok:
            downloaded += 1
        else:
            failed += 1

        if i % 50 == 0 or i == total:
            print(f"  [{i}/{total}] {skipped} skipped, {downloaded} downloaded, {failed} failed")

        time.sleep(DELAY)

    print(f"\nDone. {downloaded} new images, {skipped} already existed, {failed} failed.")


if __name__ == "__main__":
    main()
