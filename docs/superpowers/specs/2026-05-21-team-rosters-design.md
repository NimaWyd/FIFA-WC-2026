# Team Rosters Feature — Design Spec
Date: 2026-05-21
Issue: #141

## Summary

Add WC 2026 squad rosters (players by position + manager) to each team's profile page. Data is scraped once from ESPN and stored as a static JSON file in the frontend. Teams that haven't released their roster show a "not yet announced" message.

---

## Data

### Source
ESPN article: https://www.espn.com/soccer/story/_/id/48757621/2026-world-cup-squad-lists-players-announced-all-48-teams

### Storage
`frontend/src/lib/rosters.json`

Scraped once with Playwright MCP during implementation. A re-scrape script (`scripts/scrape_rosters.py`) is provided for future updates.

### Shape

```typescript
interface Player {
  name: string;   // e.g. "Kylian Mbappé"
  club: string;   // e.g. "Real Madrid"
  age: number;    // e.g. 26
}

interface TeamRoster {
  manager: string;         // e.g. "Didier Deschamps"
  goalkeepers: Player[];
  defenders: Player[];
  midfielders: Player[];
  forwards: Player[];
}

// rosters.json root type
type RostersData = Record<string, TeamRoster | { released: false }>;
```

Team keys use the canonical names already used in the codebase (matching `WC2026_TEAMS` and `wc2026Groups.ts`), e.g. `"Korea Republic"`, `"IR Iran"`, `"Côte d'Ivoire"`.

Teams not yet in the ESPN article are stored as `{ released: false }`.

---

## Files

### New
| File | Purpose |
|------|---------|
| `frontend/src/lib/rosters.json` | Scraped roster data for all 48 teams |
| `frontend/src/components/RosterSection.tsx` | Squad display UI component |
| `scripts/scrape_rosters.py` | Re-scrape script using requests + BeautifulSoup |

### Modified
| File | Change |
|------|--------|
| `frontend/src/lib/types.ts` | Add `Player`, `TeamRoster`, `RostersData` types |
| `frontend/src/app/teams/[name]/TeamProfilePage.tsx` | Import `rosters.json`, render `<RosterSection>` below Group Stage Fixtures |

---

## UI — RosterSection Component

### Props
```typescript
interface Props {
  team: string;   // canonical team name
}
```

The component imports `rosters.json` and looks up the entry by team name.

### Layout

**Unreleased state:**
A single muted card: "Squad not yet announced" with a small note that it will update when the team publishes their roster.

**Released state:**
A card with two visual zones:

1. **Manager row** — sits above the position groups, styled with a subtle separator. Shows name (white, semi-bold) and "Head Coach" label (muted, small).

2. **Position groups** — four sections in order: Goalkeepers · Defenders · Midfielders · Forwards. Each section has:
   - A small uppercase label (e.g. "GOALKEEPERS · 3")
   - A responsive grid of player cards

3. **Player card** — each player shows:
   - Name (white, bold, `text-sm`)
   - Club (slate-400, `text-xs`)
   - Age badge (small pill, e.g. "26")

### Styling
Follows existing `TeamProfilePage` visual language: `bg-navy-800`, `border-navy-600`, `rounded-2xl`, Framer Motion `fadeUp` variant for the section entrance. Position label color matches the team's confederation accent color (passed via CSS or derived from existing `CONF_CONFIG`).

---

## Placement in TeamProfilePage

`<RosterSection>` is inserted as a new `<motion.div variants={fadeUp}>` block between "Group Stage Fixtures" and the "Predict CTA" section.

---

## Re-scrape Script (`scripts/scrape_rosters.py`)

- Uses `requests` + `BeautifulSoup` (or Playwright if ESPN blocks simple HTTP)
- Outputs `frontend/src/lib/rosters.json`
- Prints a summary: teams found, teams missing (marked as `released: false`)
- Run with: `python scripts/scrape_rosters.py`

---

## Out of Scope
- Player photos
- Player statistics (caps, goals)
- Updating rosters at runtime
- Backend API endpoint for rosters
