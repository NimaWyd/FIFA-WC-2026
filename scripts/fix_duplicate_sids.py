"""
Fix all duplicate sofascore_ids in rosters.json, delete stale images,
and download correct ones from FotMob.
"""
import json, sys, time, requests
from pathlib import Path
from urllib.parse import quote

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROSTERS  = Path("frontend/src/lib/rosters.json")
OUT_DIR  = Path("frontend/public/players")
FOTMOB_SEARCH = "https://apigw.fotmob.com/searchapi/suggest?term={term}"
FOTMOB_IMAGE  = "https://images.fotmob.com/image_resources/playerimages/{id}.png"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"}

# ── Correct sofascore_ids from research agents ──────────────────────────────
FIXES = {
    # Czechia
    "Adam Ševínský":        "1146039",
    "Adam Hložek":          "963801",
    "Jan Koutny":           "1416941",
    "Jan Kuchta":           "824139",
    "Tomáš Vlček":          "907174",
    "Matěj Hadaš":          "1394149",
    "Ondrej Kricfaluši":    "1133093",
    "Ondřej Mihálik":       "361308",
    "Lukas Ambros":         "1142171",
    "Lukas Sadílek":        "280637",
    "David Planka":         "1149245",
    # Mexico
    "Luis Rey":             "1097368",
    "Bryan González":       "1002384",
    "Luis Chávez":          "757770",
    "César Huerta":         "905257",
    "Julián Araujo":        "978150",
    "Efrain Álvarez":       "931736",
    # Paraguay
    "Diego León":           "1900795",
    "Diego Gonzalez":       "1106593",
    "Oscar Romero":         "146416",
    "Ángel Romero":         "1197041",
    "Alcides Benitez":      "1185702",
    "Alan Nuñez":           "1116982",
    "Juan Espínola":        "805426",
    # Korea Republic
    "Kim Tae-Hyun":         "1185871",
    "Lee Ki-Hyeok":         "1103520",
    # Argentina
    "Anibal Moreno":        "977677",
    "Matías Soulé":         "1082406",
    "Lisandro Martínez":    "859999",
    "Zaid Romero":          "1108450",
    "Nicolás Capaldo":      "973564",
    "Nicolas Domínguez":    "871765",
    "Ezequiel Fernández":   "1003012",
    # Norway
    "Sander Tangvik":       "1030355",
    # Egypt
    "Mohamed Abdelmonemn":  "967030",   # note the extra 'n' in rosters.json
    # Jordan
    "Ahmad Al-Juiadi":      "1014310",
    # Qatar
    "Mohammed Mannai":      "1083016",
    # New Zealand
    "Ben Old":              "1122425",
    # IR Iran
    "Mehdi Torabi":         "812953",
    "Mehdi Ghaedi":         "881182",
}

# ── Load rosters ─────────────────────────────────────────────────────────────
with open(ROSTERS, encoding="utf-8") as f:
    rosters = json.load(f)

old_sids = {}   # player_name -> old sofascore_id (for stale image cleanup)
changed  = 0

for team, roster in rosters.items():
    if isinstance(roster, dict) and roster.get("released") is False:
        continue

    # Fix duplicate Jesús Angulo in Mexico (two different players)
    if team == "Mexico":
        seen_angulo = False
        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            for p in roster.get(pos, []):
                if p["name"] == "Jesús Angulo":
                    if seen_angulo:
                        old_sids[p["name"] + "_2"] = p.get("sofascore_id")
                        p["sofascore_id"] = "829624"
                        changed += 1
                    seen_angulo = True

    # Remove Tunisia Elias Saad duplicate
    if team == "Tunisia":
        for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
            players = roster.get(pos, [])
            seen = set()
            deduped = []
            for p in players:
                key = (p["name"], p.get("sofascore_id"))
                if key not in seen:
                    seen.add(key)
                    deduped.append(p)
            if len(deduped) < len(players):
                print(f"  Removed duplicate Elias Saad from Tunisia {pos}")
                roster[pos] = deduped

    # Apply fixes from FIXES dict
    for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
        for p in roster.get(pos, []):
            new_sid = FIXES.get(p["name"])
            if new_sid and p.get("sofascore_id") != new_sid:
                old_sids[p["name"]] = p.get("sofascore_id")
                print(f"  {team}: {p['name']}  {p.get('sofascore_id')} -> {new_sid}")
                p["sofascore_id"] = new_sid
                changed += 1

print(f"\nUpdated {changed} player IDs")

with open(ROSTERS, "w", encoding="utf-8") as f:
    json.dump(rosters, f, indent=2, ensure_ascii=False)
print("rosters.json saved")

# ── Delete stale images ───────────────────────────────────────────────────────
deleted = 0
for name, old_sid in old_sids.items():
    if old_sid:
        stale = OUT_DIR / f"p{old_sid}.jpg"
        # Only delete if no other player still uses this sid
        still_used = False
        for team2, roster2 in rosters.items():
            if isinstance(roster2, dict) and roster2.get("released") is False:
                continue
            for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
                for p in roster2.get(pos, []):
                    if p.get("sofascore_id") == old_sid:
                        still_used = True
        if not still_used and stale.exists():
            stale.unlink()
            deleted += 1
            print(f"  Deleted stale p{old_sid}.jpg ({name})")
print(f"Deleted {deleted} stale images")

# ── Download correct images via FotMob ───────────────────────────────────────
def fotmob_search(name):
    try:
        r = requests.get(FOTMOB_SEARCH.format(term=quote(name)), headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        for group in r.json().get("squadMemberSuggest", []):
            for opt in group.get("options", []):
                payload = opt.get("payload", {})
                if not payload.get("isCoach"):
                    return str(payload.get("id", ""))
    except:
        pass
    return None

def download_image(fotmob_id, dest):
    try:
        r = requests.get(FOTMOB_IMAGE.format(id=fotmob_id), headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 1500:
            dest.write_bytes(r.content)
            return True
    except:
        pass
    return False

# Collect all players with new sids that don't have images yet
to_download = []
for team, roster in rosters.items():
    if isinstance(roster, dict) and roster.get("released") is False:
        continue
    for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
        for p in roster.get(pos, []):
            sid = p.get("sofascore_id")
            if sid and p["name"] in FIXES and not (OUT_DIR / f"p{sid}.jpg").exists():
                to_download.append((p["name"], sid))

print(f"\nDownloading {len(to_download)} new images...")
dl_ok = dl_fail = 0
for name, sid in to_download:
    fid = fotmob_search(name)
    time.sleep(0.4)
    if fid and download_image(fid, OUT_DIR / f"p{sid}.jpg"):
        dl_ok += 1
        print(f"  OK    {name} -> p{sid}.jpg")
    else:
        dl_fail += 1
        print(f"  MISS  {name}")

print(f"\nDone. Downloaded {dl_ok}, missed {dl_fail}")
