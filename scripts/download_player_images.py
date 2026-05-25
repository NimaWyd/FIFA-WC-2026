"""
Download player and manager headshots from TheSportsDB into frontend/public/players/.

Usage (run from repo root):
    python scripts/download_player_images.py

Images are saved as:
    frontend/public/players/p{sofascore_id}.jpg   (players)
    frontend/public/players/m{sofascore_id}.jpg   (managers)

Already-downloaded files are skipped. Failed lookups are logged to
frontend/public/players/_failed.txt so you can retry manually.

TheSportsDB free tier (API key 3) allows ~1 req/sec. The script uses a
2-second delay to stay well within limits. With ~1100 total entries this
takes around 35-40 minutes. Do NOT run while the API is rate-limiting
you (HTTP 429) -- wait a few hours and try again.
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
OUT_DIR      = Path("frontend/public/players")
FAILED_LOG   = OUT_DIR / "_failed.txt"
API_BASE     = "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"
HEADERS      = {"User-Agent": "FIFA-WC-2026-App/1.0 (educational project)"}
DELAY        = 2.0   # seconds between API calls — respect free tier limit
MAX_RETRIES  = 3


def ascii_name(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def search_thumb(name: str) -> str | None:
    """
    Search TheSportsDB for a player/manager by name.
    Returns the strThumb URL of the best match, or None.
    Tries the original name first, then an ASCII-stripped variant.
    """
    candidates = [name]
    ascii = ascii_name(name)
    if ascii != name:
        candidates.append(ascii)

    for query in candidates:
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.get(API_BASE, params={"p": query},
                                 headers=HEADERS, timeout=10)
                if r.status_code == 429:
                    wait = 5 * (attempt + 1)
                    print(f"    [rate limited] waiting {wait}s ...")
                    time.sleep(wait)
                    continue
                if r.status_code != 200:
                    break
                hits = r.json().get("player") or []
                # Pick the first hit that has a thumbnail
                thumb = next((h["strThumb"] for h in hits if h.get("strThumb")), None)
                if thumb:
                    return thumb
                break  # got a response but no photo — try next candidate
            except Exception:
                time.sleep(1)

    return None


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if r.status_code == 200 and len(r.content) > 2000:
            dest.write_bytes(r.content)
            return True
        return False
    except Exception:
        return False


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(ROSTERS_PATH, encoding="utf-8") as f:
        rosters = json.load(f)

    # Build job list: (display_name, search_name, dest_path)
    jobs: list[tuple[str, str, Path]] = []

    for team, roster in rosters.items():
        # Managers
        mgr_name = roster.get("manager")
        mgr_sid  = roster.get("manager_sofascore_id")
        if mgr_name and mgr_sid:
            dest = OUT_DIR / f"m{mgr_sid}.jpg"
            jobs.append((f"{mgr_name} [{team}]", mgr_name, dest))

        if roster.get("released") is False:
            continue

        # Players
        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            for p in roster.get(pos, []):
                sid = p.get("sofascore_id")
                if not sid:
                    continue
                dest = OUT_DIR / f"p{sid}.jpg"
                jobs.append((f"{p['name']} [{team}]", p["name"], dest))

    total     = len(jobs)
    downloaded = skipped = failed = 0
    failed_names: list[str] = []

    print(f"Total entries: {total}  (skipping already-downloaded files)")
    print(f"Estimated time: {total * DELAY / 60:.0f}-{total * DELAY * 1.5 / 60:.0f} min\n")

    for i, (display, search, dest) in enumerate(jobs, 1):
        if dest.exists():
            skipped += 1
            continue

        thumb = search_thumb(search)
        time.sleep(DELAY)

        if not thumb:
            failed += 1
            failed_names.append(display)
            if i % 25 == 0 or i == total:
                print(f"  [{i}/{total}] downloaded={downloaded} skipped={skipped} failed={failed}")
            continue

        ok = download_image(thumb, dest)
        if ok:
            downloaded += 1
            print(f"  [{i}/{total}] OK  {display}")
        else:
            failed += 1
            failed_names.append(display)

        if i % 25 == 0 or i == total:
            print(f"  [{i}/{total}] downloaded={downloaded} skipped={skipped} failed={failed}")

    # Write failed log
    if failed_names:
        FAILED_LOG.write_text("\n".join(failed_names), encoding="utf-8")
        print(f"\nFailed entries logged to {FAILED_LOG}")

    print(f"\nDone. {downloaded} downloaded, {skipped} already existed, {failed} not found/failed.")


if __name__ == "__main__":
    main()
