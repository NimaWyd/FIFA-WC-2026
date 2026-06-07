# Design: Update All Team Rosters from FIFA Official PDF

**Date:** 2026-06-06  
**Status:** Approved

## Overview

Replace the entire `frontend/src/lib/rosters.json` with data from the official FIFA World Cup 2026 squad list PDF (`SquadLists-English.pdf`). For each of the 48 teams, update player names, ages, positions, and clubs. Preserve existing `espn_id` and `sofascore_id` for players who can be fuzzy-matched against the current roster. After updating the JSON, download FotMob portrait images for all players that have a `sofascore_id`.

## Source Data

- **PDF URL:** `https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf`
- **PDF structure:** 48 pages, one team per page, 26 players per team
- **Player row format:** `{shirt#} {POS} {SORT_LAST} {short_first} {full_first(s)} {LAST_NAME_CAPS} {SHIRT_NAME_CAPS} {DOB DD/MM/YYYY} {Club (CTY)} {HEIGHT}`
- **Coach row format:** `Head coach {SORT_LAST} {first_display} {full_first(s)} {LAST_NAME_CAPS} {Nationality}`
- **Parsed with:** `pdfplumber` (already installed)

## Script

**File:** `scripts/update_rosters_from_pdf.py`  
**Run from repo root:** `python scripts/update_rosters_from_pdf.py`

### Steps

1. **Download PDF** — fetch from FIFA URL into a `tempfile.NamedTemporaryFile`; print progress

2. **Parse PDF (48 pages)**
   - Skip the 4 header lines (SQUAD LIST, FIFA World Cup, date range, team name + code)
   - Skip the column-header line (`# POS PLAYER NAME …`)
   - For each player line, use a regex anchored on:
     - Left: `^\d+\s+(GK|DF|MF|FW)\s+`
     - Right: `(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d{2,3})$`
   - The name blob between position and DOB is: `{SORT_LAST} {short_first} {full_first(s)} {LAST_NAME_CAPS} {SHIRT_NAME_CAPS}`
   - **Name extraction:** scan tokens right-to-left from the name blob to peel off the all-caps SHIRT_NAME, then the all-caps LAST_NAME(S); what remains before them (after the initial SORT_LAST prefix) is FIRST_NAME(S)
   - **Display name:** `{FIRST_NAME(S)} + title_case({LAST_NAME(S)})` — e.g., `"Ramiz Larbi Zerrouki"`, `"Anis Hadj Moussa"`
   - **Club:** strip trailing ` (CTY)` suffix — `"Lille OSC (FRA)"` → `"Lille OSC"`
   - **Age:** compute from DOB to tournament start date June 11, 2026 (floor to whole years)
   - **Position mapping:** `GK → goalkeepers`, `DF → defenders`, `MF → midfielders`, `FW → forwards`
   - Parse `Head coach` line for manager name using same name-extraction logic

3. **Team name mapping**
   - PDF header format: `"Algeria (ALG)"` — strip the ` (CTY)` suffix to get canonical name
   - Build a lookup dict mapping normalized PDF names to existing rosters.json keys (handle known differences: `"Ir Republic of"` → `"Iran"`, `"USA"` → `"United States"`, `"Côte dIvoire"` → `"Ivory Coast"`, etc.)
   - Any unmapped team is logged as a warning

4. **Fuzzy-match to preserve IDs**
   - For each new player, normalize name (strip accents, lowercase, sort tokens)
   - Compare against all existing players on the same team
   - Match threshold: token-set similarity ≥ 0.6
   - On match: copy `espn_id` and `sofascore_id` to new player entry
   - On no match: player gets no IDs (will show ESPN photo or initials on frontend)

5. **Manager handling**
   - Extract manager name from PDF `Head coach` line
   - Preserve `manager_sofascore_id` from existing rosters.json (unchanged)
   - Update `manager` field with PDF name

6. **Write rosters.json**
   - Full replacement of `frontend/src/lib/rosters.json`
   - Schema per player: `{ name, club, age, espn_id?, sofascore_id? }`
   - Schema per team: `{ manager, manager_sofascore_id?, goalkeepers[], defenders[], midfielders[], forwards[] }`
   - Print a summary: teams updated, players total, ID-match rate, players without IDs

7. **Download images**
   - After writing rosters.json, invoke `download_player_images.py` via `subprocess` (or prompt user to run it separately)
   - Default: prompt the user whether to run it immediately (it takes ~15–20 min)

## Edge Cases

- **Accented characters in all-caps names:** `"BELAÏD"`, `"AÏT-NOURI"` — title_case must handle diacritics: `str.title()` or custom function that handles hyphens (`"Aït-Nouri"`)
- **Compound last names:** `"HADJ MOUSSA"`, `"ABU AL-JAZAR"` — multiple all-caps tokens; peel them as a group
- **Short_first ≠ full_first:** `"Vladimir"` → `"Vladimir"` (same); `"Ramy"` (Bensebaini's display name) → FIRST_NAME(S) col = `"Amir Selmane Rami"` — always use the FIRST_NAME(S) column for display, not the short_first in the PLAYER NAME column
- **Null byte in PDF text:** `Ra\x00k` — strip null bytes before parsing
- **Teams with `released: false` in old rosters.json:** overwrite them fully (they now have official squads)
- **pdfplumber FontBBox warnings:** suppress with `warnings.filterwarnings("ignore")`

## What's NOT Changed

- `espn_id` and `sofascore_id` for matched players (preserved via fuzzy-match)
- `manager_sofascore_id` (preserved from existing data)
- `download_player_images.py` and `fotmob_retry.py` scripts (unchanged)

## Limitations

- New players (not in old roster) will have no `sofascore_id` → no FotMob photo downloaded. Run `enrich_sofascore.py` separately after this script to fill in IDs for new players.
- Manager photos are not re-downloaded by this script.
