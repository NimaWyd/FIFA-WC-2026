# FIFA WC 2026 Predictor — UI Redesign

**Date:** 2026-05-10  
**Status:** Approved  
**Scope:** `frontend/` only — no backend changes

---

## Goal

Replace the current flat dark UI with a full FIFA.com-inspired World Cup theme. Add a real trophy photo hero with a floating animation. Restyle all existing components using the official FIFA 2026 color tokens. No new features or backend changes.

---

## Design Tokens

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#090b14` | Page background |
| `--surface` | `#0e1020` | Card backgrounds |
| `--surface2` | `#151829` | Input backgrounds, secondary surfaces |
| `--border` | `#1e2340` | Card borders, dividers |
| `--fifa-blue` | `#1a3fff` | CTAs, active tabs, hover borders, group labels, prob bars |
| `--gold` | `#f5c842` | Trophy glow, title gradient, WC badge, accents |
| `--gold-dim` | `#c9a227` | Secondary gold |
| `--text` | `#ffffff` | Primary text |
| `--text-sub` | `#8b93b8` | Secondary text, labels |
| `--text-dim` | `#4a5280` | Muted text, placeholders |
| `--green` | `#00d48a` | Success / win indicators |
| `--red` | `#ff3b5c` | Loss / error indicators |

---

## Components

### 1. Global Layout (`layout.tsx`, `globals.css`)
- Set `--bg` as body background
- Inject CSS custom properties as `:root` variables
- Font stays Inter (already loaded)

### 2. Header (in `page.tsx`)
- Replace existing header with sticky two-row header:
  - **Top bar:** `FIFA` wordmark (electric blue, bold, tracked) + `WC 2026™` gold badge, max-width container
  - **Tab bar:** unchanged tab logic, restyled — blue 3px underline on active, `--text-dim` inactive

### 3. Hero Section (new, replaces flat header title area)
- Full-width panel above the tab bar
- Background: `radial-gradient(ellipse at 50% -10%, #0d1d8a, #090b14 55%)` + diagonal stripe texture overlay (`repeating-linear-gradient` at -45deg, 28px pitch, 1.2% opacity)
- Two additional corner glows: green bottom-left, blue bottom-right (very subtle)
- Trophy image (`trophy_nobg.png`) centered, `height: 200px`, `object-fit: contain`
- Trophy filter: `drop-shadow(0 0 40px rgba(245,200,66,0.8)) drop-shadow(0 0 80px rgba(26,63,255,0.4))`
- Trophy animation: `float` keyframe — `translateY(0)` → `translateY(-18px)` → back, 4s ease-in-out infinite
- Eyebrow text: "FIFA WORLD CUP 2026™" in `--fifa-blue`, 11px, 700, 3px letter-spacing, uppercase
- Title: gradient text `linear-gradient(135deg, #fff 30%, var(--gold) 100%)`, 28px, 900 weight
- Subtitle: `--text-sub`, 13px
- CTA button: `--fifa-blue` background, white text, 700, 14px, `border-radius: 6px`, blue box-shadow — scrolls to predictor on click

### 4. Cards (`bg-[#0d1428]` → CSS var)
- All card containers: `background: var(--surface)`, `border: 1px solid var(--border)`, `border-radius: 12px`
- Hover state on interactive cards: `border-color: var(--fifa-blue)`, `transform: translateY(-2px)`

### 5. Inputs & Buttons (`TeamCombobox`, `StageSelect`, date input)
- Background: `var(--surface2)`, border: `var(--border)`
- Focus ring: `var(--fifa-blue)`
- `PredictButton`: full-width, `--fifa-blue` background, `box-shadow: 0 4px 20px rgba(26,63,255,0.4)`

### 6. Probability Bars (`ProbabilityBars.tsx`)
- Track: `var(--border)`
- Fill: `linear-gradient(90deg, var(--fifa-blue), #5b8fff)`

### 7. Winner Callout (`WinnerCallout.tsx`)
- Win highlight pill: `rgba(26,63,255,0.08)` background, `--fifa-blue` border, `#5b8fff` text

### 8. Score Display (`MatchScoreboard.tsx`)
- Score numbers: gradient text `linear-gradient(135deg, #fff, var(--gold))`

### 9. Group Bracket / Match Cards (`GroupBracket.tsx`, `GroupView.tsx`)
- Group label: `--fifa-blue`, uppercase, 700, tracked
- Match card hover: `border-color: var(--fifa-blue)`, slight lift

### 10. Metadata & Badges (`MetadataBadge.tsx`)
- Restyle to use `--surface2` background, `--border` border, `--text-sub` text

---

## Trophy Asset

- File: `frontend/public/trophy_nobg.png` (white background already removed)
- Referenced in the hero via `<Image>` (Next.js) with `priority` flag
- No external image requests

---

## What Does NOT Change

- All existing component logic, hooks, API calls, state management
- Backend (`fifa-2026-predictor/`) — untouched
- Feature set — no new features, no removed features
- Routing and tab switching logic

---

## Files to Touch

| File | Change |
|---|---|
| `frontend/src/app/globals.css` | Add CSS custom properties, update base styles |
| `frontend/src/app/layout.tsx` | Minor — ensure dark class and bg token |
| `frontend/src/app/page.tsx` | Add Hero section, restyle header, apply tokens |
| `frontend/src/components/ProbabilityBars.tsx` | Blue gradient fill |
| `frontend/src/components/WinnerCallout.tsx` | Blue win pill |
| `frontend/src/components/MatchScoreboard.tsx` | Gold gradient score |
| `frontend/src/components/PredictButton.tsx` | FIFA blue, box-shadow |
| `frontend/src/components/GroupBracket.tsx` | Group label color, hover |
| `frontend/src/components/GroupView.tsx` | Match card hover border |
| `frontend/src/components/MetadataBadge.tsx` | Restyle badge |
| `frontend/src/components/ScorelineGrid.tsx` | Dark surface, blue accent headers |
| `frontend/src/components/ExpectedGoals.tsx` | Dark surface, blue/gold bar colors |
| `frontend/src/components/ExplanationPanel.tsx` | Dark surface, text token colors |
| `frontend/public/trophy_nobg.png` | Add trophy asset |
