"""
Update FIFA rankings to April 2026 official values across:
  - fifa-2026-predictor/data/processed/fifa_rankings.csv
  - fifa-2026-predictor/src/data/team_identity.py

Source: FIFA official rankings released 01 April 2026
        (via SofaScore mirror, verified against FIFA.com top 10)
"""

import csv, re, os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(REPO, "fifa-2026-predictor", "data", "processed", "fifa_rankings.csv")
TI_PATH  = os.path.join(REPO, "fifa-2026-predictor", "src", "data", "team_identity.py")

# April 2026 official FIFA rankings — canonical codebase names
RANKINGS_2026 = {
    "France": 1, "Spain": 2, "Argentina": 3, "England": 4,
    "Portugal": 5, "Brazil": 6, "Netherlands": 7, "Morocco": 8,
    "Belgium": 9, "Germany": 10, "Croatia": 11, "Italy": 12,
    "Colombia": 13, "Senegal": 14, "Mexico": 15, "United States": 16,
    "Uruguay": 17, "Japan": 18, "Switzerland": 19, "Denmark": 20,
    "IR Iran": 21, "Turkey": 22, "Ecuador": 23, "Austria": 24,
    "Korea Republic": 25, "Nigeria": 26, "Australia": 27, "Algeria": 28,
    "Egypt": 29, "Canada": 30, "Norway": 31, "Ukraine": 32,
    "Panama": 33, "Côte d'Ivoire": 34, "Poland": 35, "Sweden": 38,
    "Paraguay": 40, "Czechia": 41, "Hungary": 42, "Scotland": 43,
    "Tunisia": 44, "Cameroon": 45, "DR Congo": 46, "Greece": 47,
    "Slovakia": 48, "Venezuela": 49, "Uzbekistan": 50, "Costa Rica": 51,
    "Mali": 52, "Peru": 53, "Chile": 54, "Qatar": 55,
    "Romania": 56, "Iraq": 57, "Slovenia": 58, "South Africa": 60,
    "Saudi Arabia": 61, "Burkina Faso": 62, "Jordan": 63, "Albania": 64,
    "Bosnia and Herzegovina": 65, "Honduras": 66, "Cape Verde Islands": 69,
    "Ghana": 74, "Curaçao": 82, "Haiti": 83, "New Zealand": 85,
    # Additional teams in existing CSV
    "Serbia": 39, "Albania": 64, "Montenegro": 81,
    "North Macedonia": 67, "Georgia": 72, "Iceland": 75,
    "Bolivia": 76, "Israel": 77, "Finland": 73, "Ireland": 59,
}


def update_csv():
    # Read existing CSV to preserve any teams not in our update
    existing = {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing[row["team"]] = int(row["fifa_rank"])

    # Apply updates
    updated = 0
    for team, rank in RANKINGS_2026.items():
        if team in existing and existing[team] != rank:
            print(f"  {team}: {existing[team]} -> {rank}")
            existing[team] = rank
            updated += 1
        elif team not in existing:
            existing[team] = rank

    # Write back sorted by rank
    rows = sorted(existing.items(), key=lambda x: x[1])
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["team", "fifa_rank"])
        for team, rank in rows:
            writer.writerow([team, rank])

    print(f"\nCSV: {updated} ranks updated, {len(rows)} total teams")


def update_team_identity():
    with open(TI_PATH, encoding="utf-8") as f:
        content = f.read()

    updated = 0
    for team, new_rank in RANKINGS_2026.items():
        # Match the team entry and its fifa_rank_2025 value
        # Pattern handles both inline and multi-line dicts
        pattern = rf'("{re.escape(team)}".*?fifa_rank_2025":\s*)(\d+|None)'
        def replacer(m):
            nonlocal updated
            old = m.group(2)
            if old != str(new_rank):
                updated += 1
            return m.group(1) + str(new_rank)
        content = re.sub(pattern, replacer, content, flags=re.DOTALL)

    with open(TI_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"team_identity.py: {updated} ranks updated")


if __name__ == "__main__":
    print("=== Updating FIFA rankings to April 2026 ===\n")
    print("CSV changes:")
    update_csv()
    print()
    update_team_identity()
    print("\nDone. Run seed_fifa_rankings if teams.csv needs regenerating.")
