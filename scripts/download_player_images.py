"""
Download player and manager portrait images from Transfermarkt into frontend/public/players/.

Usage (run from repo root):
    python scripts/download_player_images.py

Images are saved as:
    frontend/public/players/p{sofascore_id}.jpg   (players)
    frontend/public/players/m{manager_sofascore_id}.jpg  (managers)

Already-downloaded files are skipped. Failed lookups are logged to
frontend/public/players/_failed.txt so you can retry manually.

Uses Transfermarkt's internal quickselect JSON API — no API key required.
A 1-second delay between requests keeps well within rate limits.
With ~1000 players + 48 managers this takes around 20-25 minutes.
"""

import json
import sys
import time
import unicodedata
import re
from pathlib import Path
from urllib.parse import quote

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

ROSTERS_PATH = Path("frontend/src/lib/rosters.json")
OUT_DIR      = Path("frontend/public/players")
FAILED_LOG   = OUT_DIR / "_failed.txt"

TM_SEARCH = "https://www.transfermarkt.com/ceapi/quickselect/query/{query}"
HEADERS   = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.transfermarkt.com/",
    "X-Requested-With": "XMLHttpRequest",
}

DELAY       = 1.0
MAX_RETRIES = 3


# ── Name helpers ──────────────────────────────────────────────────────────────

def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    return re.sub(r"\s+", " ", "".join(
        c for c in nfkd if not unicodedata.combining(c)
    )).strip().lower()


def token_sim(a: str, b: str) -> float:
    ta, tb = set(normalize(a).split()), set(normalize(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


# ── Transfermarkt API ─────────────────────────────────────────────────────────

def _tm_get(name: str) -> dict | None:
    """Call TM quickselect, trying original name then ASCII-stripped fallback."""
    ascii_ver = normalize(name)
    queries = list(dict.fromkeys([name, ascii_ver]))  # deduplicate while preserving order

    for q in queries:
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.get(
                    TM_SEARCH.format(query=quote(q)),
                    headers=HEADERS,
                    timeout=10,
                )
                if r.status_code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"    [rate limited] waiting {wait}s …")
                    time.sleep(wait)
                    continue
                if r.status_code == 200:
                    return r.json()
                break
            except Exception:
                time.sleep(2)

    return None


def _best_image(data: dict, name: str, pool_keys: list[str]) -> str | None:
    """Pick the best-matching entry from TM results and return its image URL."""
    best_img, best_score = None, 0.0

    for key in pool_keys:
        for entry in data.get(key, []):
            entry_name = entry.get("name") or ""
            score = token_sim(name, entry_name)
            if score > best_score:
                best_score = score
                # TM returns "image" in quickselect; fall back to CDN construction
                img = entry.get("image") or entry.get("img")
                if not img:
                    eid = entry.get("id")
                    if eid:
                        img = (
                            f"https://img.tm-aws.com/image/trainer/medium/t{eid}.jpg"
                            if key == "trainers"
                            else f"https://img.tm-aws.com/image/players/medium/p{eid}.jpg"
                        )
                best_img = img

    return best_img if best_score >= 0.45 else None


def search_tm(name: str, kind: str = "player") -> str | None:
    """
    Search Transfermarkt for a player or coach by name.
    Returns the portrait image URL, or None if not found.
    kind: "player" | "coach"
    """
    data = _tm_get(name)
    if not data:
        return None

    # Coaches often appear in "trainers"; players in "players".
    # If primary pool is empty we also check the other one as fallback.
    pool_keys = ["trainers", "players"] if kind == "coach" else ["players", "trainers"]
    return _best_image(data, name, pool_keys)


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if r.status_code == 200 and len(r.content) > 1500:
            dest.write_bytes(r.content)
            return True
        return False
    except Exception:
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(ROSTERS_PATH, encoding="utf-8") as f:
        rosters = json.load(f)

    # (display_label, search_name, dest_path, kind)
    jobs: list[tuple[str, str, Path, str]] = []

    for team, roster in rosters.items():
        # Manager
        mgr_name = roster.get("manager")
        mgr_sid  = roster.get("manager_sofascore_id")
        if mgr_name and mgr_sid:
            jobs.append((
                f"{mgr_name} [{team}] (coach)",
                mgr_name,
                OUT_DIR / f"m{mgr_sid}.jpg",
                "coach",
            ))

        if roster.get("released") is False:
            continue

        # Players — only those with sofascore_id (ESPN CDN covers the rest)
        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            for p in roster.get(pos, []):
                sid = p.get("sofascore_id")
                if not sid:
                    continue
                jobs.append((
                    f"{p['name']} [{team}]",
                    p["name"],
                    OUT_DIR / f"p{sid}.jpg",
                    "player",
                ))

    total = len(jobs)
    downloaded = skipped = failed = 0
    failed_names: list[str] = []

    print(f"Total entries : {total}")
    print(f"Estimated time: {total * DELAY / 60:.0f}–{total * DELAY * 1.5 / 60:.0f} min\n")

    for i, (display, search_name, dest, kind) in enumerate(jobs, 1):
        if dest.exists():
            skipped += 1
            continue

        img_url = search_tm(search_name, kind)
        time.sleep(DELAY)

        if not img_url:
            failed += 1
            failed_names.append(display)
        else:
            if download_image(img_url, dest):
                downloaded += 1
                print(f"  [{i}/{total}] OK   {display}")
            else:
                failed += 1
                failed_names.append(display)

        if i % 50 == 0 or i == total:
            print(f"  [{i}/{total}] downloaded={downloaded} skipped={skipped} failed={failed}")

    if failed_names:
        FAILED_LOG.write_text("\n".join(failed_names), encoding="utf-8")
        print(f"\nFailed entries logged to {FAILED_LOG}")

    print(f"\nDone. {downloaded} downloaded, {skipped} already existed, {failed} not found/failed.")


if __name__ == "__main__":
    main()
