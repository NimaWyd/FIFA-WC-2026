# Scoreline Display Bug Fix — Design Spec
*Issue #68 | Date: 2026-05-07*

## Problem

The frontend always displays a home-win scoreline even when the outcome model predicts the away team is more likely to win.

**Root cause (two-part):**
1. The Poisson scoreline model has independent λ parameters that may give `λh > λa` (home team scores more) even when the ensemble outcome model predicts `away_win > home_win`.
2. When the frontend searches `top_scorelines` (top 5 by Poisson probability) for a scoreline matching the dominant outcome and finds none, it falls back to `top_scorelines[0]` — the highest-probability Poisson scoreline, which is typically a home win or draw.

The probability bars display correctly. Only the displayed "Predicted Score" is wrong.

## Fix (Frontend-only)

**File changed:** `frontend/src/app/page.tsx` only.

### 1. Extract `selectScoreline` helper

Extract the inline scoreline-selection logic from the JSX render block into a pure function at the top of the file (outside the component). This makes the logic testable and readable.

```ts
function selectScoreline(
  dominant: "H" | "A" | "D",
  topScorelinesArg: import("@/lib/types").Scoreline[],
  xgHome: number,
  xgAway: number
): [number, number] {
  const match = topScorelinesArg.find(({ scoreline }) => {
    const [h, a] = scoreline.split("-").map(Number);
    if (h + a > 6) return false;
    return dominant === "H" ? h > a : dominant === "A" ? a > h : h === a;
  });
  if (match) {
    const [h, a] = match.scoreline.split("-").map(Number);
    return [h, a];
  }
  // Synthesize minimal score consistent with dominant outcome
  const h = Math.min(3, Math.round(xgHome));
  const a = Math.min(3, Math.round(xgAway));
  if (dominant === "H") return h > a ? [h, a] : [a + 1, a];
  if (dominant === "A") return a > h ? [h, a] : [h, h + 1];
  const d = Math.min(h, a);
  return [d, d];
}
```

**Changes vs current code:**
- `hg + ag > 4` filter raised to `> 6` (avoids discarding valid 2-3, 3-2 etc.)
- Fallback changed from `top_scorelines[0]` to synthesis from `expected_goals`
- Synthesis ensures the displayed score always matches the dominant outcome

### 2. Update the JSX render block

Replace the current inline IIFE (~25 lines) that ends with `result.top_scorelines[0]` fallback with a call to `selectScoreline`:

```tsx
{result.top_scorelines.length > 0 && (() => {
  const p = result.probabilities;
  const dominant =
    p.home_win > p.draw && p.home_win > p.away_win ? "H" :
    p.away_win > p.draw && p.away_win > p.home_win ? "A" : "D";
  const [hg, ag] = selectScoreline(
    dominant,
    result.top_scorelines,
    result.expected_goals?.home ?? 1,
    result.expected_goals?.away ?? 1,
  );
  return (
    <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
      <MatchScoreboard
        homeTeam={result.home_team}
        awayTeam={result.away_team}
        homeGoals={hg}
        awayGoals={ag}
      />
    </div>
  );
})()}
```

## Test File

**New file:** `frontend/src/__tests__/scorelineSelection.test.ts`

Tests (6 total):

| Scenario | Input | Expected output |
|----------|-------|-----------------|
| Away-win scoreline found in top list | dominant="A", scorelines include "0-1" | `[0, 1]` |
| No away-win in top list → synthesize | dominant="A", all home-win scorelines, xg=1.2/0.8 | `[1, 2]` |
| Home-win found | dominant="H", scorelines include "2-1" | `[2, 1]` |
| No home-win → synthesize | dominant="H", all draws, xg=1.5/0.5 | `[2, 1]` (xg rounds to 2,1 → 2>1 ✓) |
| Draw found | dominant="D", scorelines include "1-1" | `[1, 1]` |
| No draw → synthesize | dominant="D", all non-draws, xg=1.8/1.3 | `[1, 1]` (min(2,1)=1) |

## Out of Scope

- Fixing the Poisson model's λ to be consistent with the outcome model
- Changing `top_n` in the backend
- Any change to ProbabilityBars (already correct)
