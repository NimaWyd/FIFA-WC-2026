"""
One-time patch for rosters.json: Groups A, B, and G corrections.
Run from repo root: python scripts/patch_rosters_groups_a_b_g.py

Changes applied:
  Group A - Korea Republic: name format + 2 structural player fixes
  Group A - Czechia: 2 structural player fixes + 5 format/diacritic fixes
  Group B - Bosnia: 1 structural GK fix + 2 position moves
  Group B - Qatar: 2 ghost-player removals + 2 renames + 2 position moves + 2 additions
  Group G - IR Iran: 12 renames + 2 position moves + 1 ghost removal + 1 addition + manager
"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path

ROSTERS = Path("frontend/src/lib/rosters.json")


def rename(team_data, old_name, new_name):
    for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
        for p in team_data.get(pos, []):
            if p["name"] == old_name:
                p["name"] = new_name
                return True
    raise ValueError(f"Player '{old_name}' not found")


def find_player(team_data, name):
    for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
        for p in team_data.get(pos, []):
            if p["name"] == name:
                return pos, p
    raise ValueError(f"Player '{name}' not found")


def move_position(team_data, name, new_pos):
    old_pos, player = find_player(team_data, name)
    if old_pos == new_pos:
        return
    team_data[old_pos].remove(player)
    team_data.setdefault(new_pos, []).append(player)


def replace_player(team_data, old_name, new_player_dict):
    """Remove old_name and insert new player in same position slot."""
    for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
        lst = team_data.get(pos, [])
        for i, p in enumerate(lst):
            if p["name"] == old_name:
                lst[i] = new_player_dict
                return pos
    raise ValueError(f"Player '{old_name}' not found for replacement")


def remove_player(team_data, name):
    for pos in ("goalkeepers", "defenders", "midfielders", "forwards"):
        lst = team_data.get(pos, [])
        for p in lst:
            if p["name"] == name:
                lst.remove(p)
                return pos
    raise ValueError(f"Player '{name}' not found for removal")


def add_player(team_data, pos, player_dict):
    team_data.setdefault(pos, []).append(player_dict)


with open(ROSTERS, encoding="utf-8") as f:
    rosters = json.load(f)


# ── Group A: Korea Republic ───────────────────────────────────────────────────
kr = rosters["Korea Republic"]

# Format changes (same player, ESPN display name)
rename(kr, "Hyeonwoo Jo",  "Jo Hyun-Woo")
rename(kr, "Inbeom Hwang", "Hwang In-Beom")
rename(kr, "Jisung Eom",   "Um Ji-Sung")
rename(kr, "Hyeongyu Oh",  "Oh Hyun-Kyu")
rename(kr, "Guesung Cho",  "Cho Kyu-Sung")

# Gihyuk Lee (MID) is Lee Ki-Hyeok in ESPN — same player, wrong position
rename(kr, "Gihyuk Lee", "Lee Ki-Hyeok")
move_position(kr, "Lee Ki-Hyeok", "defenders")

# Wije Cho (DEF) not in ESPN — replace with Jo Yu-Min (Sharjah)
replace_player(kr, "Wije Cho", {
    "name": "Jo Yu-Min",
    "club": "Sharjah FC",
    "age": 22,
    "sofascore_id": "1026122",
})

print("Korea Republic ✓")


# ── Group A: Czechia ──────────────────────────────────────────────────────────
cz = rosters["Czechia"]

# Matěj Kovář (GK) not in ESPN — replace with Jan Koutny (Sigma Olomouc)
replace_player(cz, "Matěj Kovář", {
    "name": "Jan Koutny",
    "club": "FC Sigma Olomouc",
    "fotmob_id": "1664964",
})

# Pavel Šulc (FWD) not in ESPN — replace with Matej Vydra (Viktoria Plzen)
replace_player(cz, "Pavel Šulc", {
    "name": "Matej Vydra",
    "club": "FC Viktoria Plzen",
    "fotmob_id": "196308",
})

# Format fixes (diacritics to ESPN style)
rename(cz, "Jindřich Staněk",  "Jindrich Stanek")
rename(cz, "Lukáš Horníček",   "Lukas Hornicek")
rename(cz, "Vladimír Darida",  "Vladimir Darida")
rename(cz, "Lukáš Červ",       "Lukás Cerv")
rename(cz, "Lukáš Provod",     "Lukás Provod")

print("Czechia ✓")


# ── Group B: Bosnia and Herzegovina ──────────────────────────────────────────
bih = rosters["Bosnia and Herzegovina"]

# Mladen Jurkas (GK) not in ESPN — replace with Osman Hadzikic (Slaven Belupo)
replace_player(bih, "Mladen Jurkas", {
    "name": "Osman Hadzikic",
    "club": "NK Slaven Belupo",
    "fotmob_id": "488207",
})

# Position fixes: ESPN has both as MID, rosters had them as FWD
move_position(bih, "Kerim Alajbegovic",   "midfielders")
move_position(bih, "Esmir Bajraktarevic", "midfielders")

print("Bosnia and Herzegovina ✓")


# ── Group B: Qatar ────────────────────────────────────────────────────────────
qa = rosters["Qatar"]

# Ghost players not in ESPN — remove
remove_player(qa, "Ahmed Fathy M Abdoulla")
remove_player(qa, "Mohamed Naceur Manai")

# Name fixes (different transliteration)
rename(qa, "Ayoub Mohamed Aloui",    "Ayoub Al-Alawi")
# Gueye Seydinaissalaye = Issa Laye (Al Arabi) — rename and update fotmob_id
_, issa = find_player(qa, "Gueye Seydinaissalaye")
issa["name"]      = "Issa Laye"
issa["fotmob_id"] = "1839745"

# Position fixes: Jassim Gaber is MID per ESPN, Mohammed Mannai is MID per ESPN
move_position(qa, "Jassim Gaber",     "midfielders")
move_position(qa, "Mohammed Mannai",  "midfielders")

# Add missing FWDs
add_player(qa, "forwards", {
    "name":      "Ahmed Al-Ganehi",
    "club":      "Al-Gharafa SC",
    "fotmob_id": "1210913",
})
add_player(qa, "forwards", {
    "name":      "Mohammed Muntari",
    "club":      "Al-Gharafa SC",
    "fotmob_id": "431151",
})

print("Qatar ✓")


# ── Group G: IR Iran ──────────────────────────────────────────────────────────
ir = rosters["IR Iran"]

# Manager
ir["manager"] = "Amir Ghalenoei"

# GK renames
rename(ir, "Ali Reza Safarbeiranvand", "Alireza Beiranvand")
rename(ir, "Seyedpayam Niazmand",      "Payam Niazmand")
rename(ir, "Seyedhossein Hosseini",    "Hossein Hosseini")

# DEF renames
rename(ir, "Saleh Hardani Kherad",     "Saleh Hardani")
rename(ir, "Ehsan Haji Safi",          "Ehsan Hajsafi")
rename(ir, "Shojae Khalilzadeh",       "Shoka Khalilzadeh")
rename(ir, "Milad Mohammadikeshmarzi", "Milad Mohammadi")
rename(ir, "Mohammadhossein Kanani Zadegan", "Hossein Kanaani")
rename(ir, "Ali Nemati",               "Ali Nemati Omid Noorafkan")
rename(ir, "Ramin Rezaeiansemeskandi", "Ramin Rezaeian")
rename(ir, "Danial Iri",               "Danial Eiri")

# Arya Yousefi is MID per ESPN — move from DEF + rename
rename(ir, "Arya Yousefi", "Aria Yousefi")
move_position(ir, "Aria Yousefi", "midfielders")

# MID renames
rename(ir, "Saeid Ezatolahi Afagh",        "Saeid Ezatolahi")
rename(ir, "Alireza Jahanbakhsh Jirandeh", "Alireza Jahanbakhsh")
rename(ir, "Mohammad Mohebbi",             "Mohammad Mohebi")
rename(ir, "Seyed Saman Ghoddoos",         "Saman Ghoddos")
rename(ir, "Roozbeh Cheshmi",              "Rouzbeh Cheshmi")
rename(ir, "Mahdi Torabi",                 "Mehdi Torabi")
rename(ir, "Amirmohammad Razaghinia",      "Amir Mohammad Razzaghinia")

# Mehdi Ghayedi = Mehdi Ghaedi (ESPN MID) — rename + move from FWD
rename(ir, "Mehdi Ghayedi", "Mehdi Ghaedi")
move_position(ir, "Mehdi Ghaedi", "midfielders")

# FWD renames
rename(ir, "Ali Alipourghara",                        "Ali Alipour")
rename(ir, "Amirhossein Hosseinzadehtazehgheshlagh",  "Amirhossein Hosseinzadeh")

# Ghost player not in ESPN
remove_player(ir, "Shahriyar Moghanloo")

# Add missing FWD: Amirhossein Mahmoudi (Persepolis)
add_player(ir, "forwards", {
    "name":      "Amirhossein Mahmoudi",
    "club":      "Persepolis FC",
    "fotmob_id": "1844610",
})

print("IR Iran ✓")


# ── Saudi Arabia (Group H): trivial name fix ──────────────────────────────────
sa = rosters["Saudi Arabia"]
rename(sa, "Firas Al-Buraikan", "Firas Al Buraikan")
print("Saudi Arabia (partial) ✓")


# ── Save ──────────────────────────────────────────────────────────────────────
with open(ROSTERS, "w", encoding="utf-8") as f:
    json.dump(rosters, f, ensure_ascii=False, indent=2)

print(f"\nSaved {ROSTERS}")

# ── Verify counts ─────────────────────────────────────────────────────────────
for team in ["Korea Republic", "Czechia", "Bosnia and Herzegovina", "Qatar", "IR Iran"]:
    t = rosters[team]
    total = sum(len(t.get(p, [])) for p in ("goalkeepers","defenders","midfielders","forwards"))
    print(f"  {team}: {total} players")
