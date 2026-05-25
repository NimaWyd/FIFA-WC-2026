"""
Download player and manager portrait images from FotMob into frontend/public/players/.

Usage (run from repo root):
    python scripts/download_player_images.py

Images are saved as:
    frontend/public/players/p{sofascore_id}.jpg   (players)
    frontend/public/players/m{manager_sofascore_id}.jpg  (managers)

Already-downloaded files are skipped. Failed lookups are logged to
frontend/public/players/_failed.txt so you can retry manually.

Uses FotMob's public search API — no API key required.
A 0.5-second delay between requests keeps well within rate limits.
With ~1000 players + 48 managers this takes around 10-15 minutes.
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

# Force UTF-8 output on Windows (avoids cp1252 crashes on accented player names)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROSTERS_PATH = Path("frontend/src/lib/rosters.json")
OUT_DIR      = Path("frontend/public/players")
FAILED_LOG   = OUT_DIR / "_failed.txt"

FOTMOB_SEARCH = "https://apigw.fotmob.com/searchapi/suggest?term={term}"
FOTMOB_IMAGE  = "https://images.fotmob.com/image_resources/playerimages/{id}.png"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

DELAY       = 0.5
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


# ── FotMob API ────────────────────────────────────────────────────────────────

def search_fotmob(name: str, is_coach: bool = False) -> str | None:
    """
    Search FotMob for a player or coach by name.
    Returns a FotMob player ID, or None if not found.
    """
    ascii_ver = normalize(name)
    queries = list(dict.fromkeys([name, ascii_ver]))  # original then ASCII, deduplicated

    for q in queries:
        url = FOTMOB_SEARCH.format(term=quote(q))
        for attempt in range(MAX_RETRIES):
            try:
                r = requests.get(url, headers=HEADERS, timeout=10)
                if r.status_code == 429:
                    wait = 5 * (attempt + 1)
                    print(f"    [rate limited] waiting {wait}s …")
                    time.sleep(wait)
                    continue
                if r.status_code != 200:
                    break
                data = r.json()
                break
            except Exception:
                time.sleep(1)
                data = None
        else:
            data = None

        if not data:
            continue

        options = []
        for group in data.get("squadMemberSuggest", []):
            options.extend(group.get("options", []))

        # Score each candidate: name similarity + role bonus
        best_id, best_score = None, 0.0
        for opt in options:
            raw_text = opt.get("text", "")
            # FotMob format: "Player Name|id"
            candidate_name = raw_text.split("|")[0]
            payload = opt.get("payload", {})

            sim = token_sim(name, candidate_name)
            role_match = payload.get("isCoach", False) == is_coach
            score = sim + (0.1 if role_match else 0.0)

            if score > best_score:
                best_score = score
                best_id = payload.get("id")

        if best_id and best_score >= 0.5:
            return str(best_id)

    return None


def download_image(fotmob_id: str, dest: Path) -> bool:
    url = FOTMOB_IMAGE.format(id=fotmob_id)
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

    # Remove stale test files from development
    for test_file in OUT_DIR.glob("test_*"):
        test_file.unlink()

    with open(ROSTERS_PATH, encoding="utf-8") as f:
        rosters = json.load(f)

    # (display_label, search_name, dest_path, is_coach)
    jobs: list[tuple[str, str, Path, bool]] = []

    for team, roster in rosters.items():
        # Manager
        mgr_name = roster.get("manager")
        mgr_sid  = roster.get("manager_sofascore_id")
        if mgr_name and mgr_sid:
            jobs.append((
                f"{mgr_name} [{team}] (coach)",
                mgr_name,
                OUT_DIR / f"m{mgr_sid}.jpg",
                True,
            ))

        if roster.get("released") is False:
            continue

        # Players — only those with sofascore_id (ESPN CDN covers the rest live)
        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            for p in roster.get(pos, []):
                sid = p.get("sofascore_id")
                if not sid:
                    continue
                jobs.append((
                    f"{p['name']} [{team}]",
                    p["name"],
                    OUT_DIR / f"p{sid}.jpg",
                    False,
                ))

    total = len(jobs)
    downloaded = skipped = failed = 0
    failed_names: list[str] = []

    print(f"Total entries : {total}")
    print(f"Estimated time: {total * DELAY / 60:.0f}–{total * DELAY * 1.5 / 60:.0f} min\n")

    for i, (display, search_name, dest, is_coach) in enumerate(jobs, 1):
        if dest.exists():
            skipped += 1
            continue

        fotmob_id = search_fotmob(search_name, is_coach)
        time.sleep(DELAY)

        if not fotmob_id:
            failed += 1
            failed_names.append(display)
        else:
            if download_image(fotmob_id, dest):
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
