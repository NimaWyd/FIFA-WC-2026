# Scoreline Display Bug Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the frontend always displaying a home-win scoreline even when the away team has a higher predicted win probability.

**Architecture:** Extract the inline scoreline-selection logic from `page.tsx` into a pure function `selectScoreline` in `src/lib/scoreline.ts`. The function searches `top_scorelines` for a result matching the dominant outcome, and falls back to synthesizing a minimal score from `expected_goals` (instead of blindly using `top_scorelines[0]`). The fix is frontend-only — no model changes.

**Tech Stack:** TypeScript, Vitest, @testing-library/react (existing setup)

---

### Task 1: Write tests for `selectScoreline` and implement the function

**Files:**
- Create: `frontend/src/lib/scoreline.ts`
- Create: `frontend/src/__tests__/scorelineSelection.test.ts`

- [ ] **Step 1: Create a stub `frontend/src/lib/scoreline.ts`**

```ts
import type { Scoreline } from "./types";

export function selectScoreline(
  dominant: "H" | "A" | "D",
  topScorelinesArg: Scoreline[],
  xgHome: number,
  xgAway: number
): [number, number] {
  throw new Error("not implemented");
}
```

- [ ] **Step 2: Create `frontend/src/__tests__/scorelineSelection.test.ts`**

```ts
import { describe, it, expect } from 'vitest'
import { selectScoreline } from '@/lib/scoreline'
import type { Scoreline } from '@/lib/types'

function sc(scoreline: string, probability = 0.1): Scoreline {
  return { scoreline, probability }
}

describe('selectScoreline', () => {
  describe('matching scoreline found in top list', () => {
    it('returns away-win scoreline when dominant is A', () => {
      const top = [sc('1-0'), sc('0-0'), sc('0-1'), sc('2-0')]
      expect(selectScoreline('A', top, 1.2, 0.8)).toEqual([0, 1])
    })

    it('returns home-win scoreline when dominant is H', () => {
      const top = [sc('0-1'), sc('0-0'), sc('2-1'), sc('0-2')]
      expect(selectScoreline('H', top, 1.5, 0.8)).toEqual([2, 1])
    })

    it('returns draw scoreline when dominant is D', () => {
      const top = [sc('1-0'), sc('1-1'), sc('2-0')]
      expect(selectScoreline('D', top, 1.0, 1.0)).toEqual([1, 1])
    })

    it('skips scorelines where total goals > 6', () => {
      // 4-3 (sum=7) should be skipped; 0-1 should be found
      const top = [sc('4-3'), sc('0-1')]
      expect(selectScoreline('A', top, 1.0, 1.5)).toEqual([0, 1])
    })
  })

  describe('no matching scoreline → synthesise from xG', () => {
    it('synthesises away win when dominant is A and all scorelines are home wins', () => {
      const top = [sc('1-0'), sc('2-0'), sc('2-1'), sc('3-0'), sc('3-1')]
      // xgHome=1.2 → rounds to 1, xgAway=0.8 → rounds to 1 → a not > h → [h, h+1] = [1, 2]
      expect(selectScoreline('A', top, 1.2, 0.8)).toEqual([1, 2])
    })

    it('synthesises home win when dominant is H and all scorelines are draws', () => {
      const top = [sc('0-0'), sc('1-1'), sc('2-2')]
      // xgHome=1.5 → rounds to 2, xgAway=0.5 → rounds to 1 → h > a → [2, 1]
      expect(selectScoreline('H', top, 1.5, 0.5)).toEqual([2, 1])
    })

    it('synthesises draw when dominant is D and no draws in list', () => {
      const top = [sc('1-0'), sc('0-1'), sc('2-1')]
      // xgHome=1.8 → rounds to 2, xgAway=1.3 → rounds to 1 → d = min(2,1) = 1 → [1, 1]
      expect(selectScoreline('D', top, 1.8, 1.3)).toEqual([1, 1])
    })

    it('caps synthesised goals at 3', () => {
      const top = [sc('0-1'), sc('0-2')]
      // dominant H, xgHome=4.8 → rounds to 5 → capped at 3, xgAway=4.2 → rounds to 4 → capped at 3
      // h=3, a=3 → h not > a → [a+1, a] = [4, 3] but a+1 is not capped — that's fine, only xg is capped
      // Actually: h=min(3, round(4.8))=3, a=min(3, round(4.2))=3 → h not > a → [a+1, a] = [4, 3]
      expect(selectScoreline('H', top, 4.8, 4.2)).toEqual([4, 3])
    })
  })
})
```

- [ ] **Step 3: Run tests — verify they fail with "not implemented"**

```bash
cd frontend && npm run test:run -- src/__tests__/scorelineSelection.test.ts 2>&1; cd ..
```

Expected: All 8 tests fail with `Error: not implemented`.

- [ ] **Step 4: Implement `selectScoreline` in `frontend/src/lib/scoreline.ts`**

Replace the stub with:

```ts
import type { Scoreline } from "./types";

export function selectScoreline(
  dominant: "H" | "A" | "D",
  topScorelinesArg: Scoreline[],
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
  const h = Math.min(3, Math.round(xgHome));
  const a = Math.min(3, Math.round(xgAway));
  if (dominant === "H") return h > a ? [h, a] : [a + 1, a];
  if (dominant === "A") return a > h ? [h, a] : [h, h + 1];
  const d = Math.min(h, a);
  return [d, d];
}
```

- [ ] **Step 5: Run tests — verify all 8 pass**

```bash
cd frontend && npm run test:run -- src/__tests__/scorelineSelection.test.ts 2>&1; cd ..
```

Expected: `Tests 8 passed (8)`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/scoreline.ts frontend/src/__tests__/scorelineSelection.test.ts
git commit -m "feat: add selectScoreline helper with synthesised fallback (#68)"
```

---

### Task 2: Wire `selectScoreline` into `page.tsx` and verify full suite

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Add import to `frontend/src/app/page.tsx`**

At the top of the file, after the existing imports, add:

```ts
import { selectScoreline } from "@/lib/scoreline";
```

- [ ] **Step 2: Replace the inline scoreline IIFE in `frontend/src/app/page.tsx`**

Find and replace this block (currently around lines 285–312):

```tsx
                {result.top_scorelines.length > 0 && (() => {
                  const p = result.probabilities;
                  const dominant =
                    p.home_win > p.draw && p.home_win > p.away_win ? "H" :
                    p.away_win > p.draw && p.away_win > p.home_win ? "A" : "D";
                  const matching = result.top_scorelines.find((s) => {
                    const parts = s.scoreline.split("-");
                    const hg = parseInt(parts[0] ?? "0", 10);
                    const ag = parseInt(parts[1] ?? "0", 10);
                    if (hg + ag > 4) return false;
                    if (dominant === "H") return hg > ag;
                    if (dominant === "A") return ag > hg;
                    return hg === ag;
                  });
                  const scoreline = (matching ?? result.top_scorelines[0]).scoreline.split("-");
                  const hg = parseInt(scoreline[0] ?? "0", 10);
                  const ag = parseInt(scoreline[1] ?? "0", 10);
                  return (
                    <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6">
                      <MatchScoreboard
                        homeTeam={result.home_team}
                        awayTeam={result.away_team}
                        homeGoals={isNaN(hg) ? 0 : hg}
                        awayGoals={isNaN(ag) ? 0 : ag}
                      />
                    </div>
                  );
                })()}
```

Replace with:

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

- [ ] **Step 3: Run the full test suite**

```bash
cd frontend && npm run test:run 2>&1; cd ..
```

Expected: `Tests 30 passed (6 files)` — the 22 existing tests plus 8 new ones all pass.

- [ ] **Step 4: Commit and close issue**

```bash
git add frontend/src/app/page.tsx
git commit -m "fix: use selectScoreline to show correct score for away-win predictions, closes #68"
```
