# FIFA UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat dark UI with a full FIFA.com-inspired World Cup theme: real floating trophy hero, electric blue + gold tokens, restyled cards/components throughout.

**Architecture:** Extend `tailwind.config.ts` with FIFA color tokens, add float keyframe animation in `globals.css`, copy the trophy asset to `public/`, then restyle components top-down — Hero → Header → buttons → result cards → group views.

**Tech Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS, Framer Motion, `next/image`

---

## File Map

| File | Change |
|---|---|
| `frontend/public/trophy_nobg.png` | Copy trophy asset (no background) |
| `frontend/tailwind.config.ts` | Add `fifa`, `surface`, `border-fifa` color tokens |
| `frontend/src/app/globals.css` | Add `@keyframes float`, `@keyframes fade-in`, CSS vars |
| `frontend/src/app/page.tsx` | Add Hero section, restyle header top-bar + tab-bar |
| `frontend/src/components/PredictButton.tsx` | FIFA blue enabled state |
| `frontend/src/components/ProbabilityBars.tsx` | Blue gradient bar fill |
| `frontend/src/components/WinnerCallout.tsx` | Blue win-pill highlight |
| `frontend/src/components/MatchScoreboard.tsx` | Gold gradient score numbers |
| `frontend/src/components/GroupBracket.tsx` | FIFA blue group label, blue hover border |
| `frontend/src/components/GroupView.tsx` | Blue hover borders on fixture cards |
| `frontend/src/components/ScorelineGrid.tsx` | Blue top-scoreline accent |
| `frontend/src/components/ExpectedGoals.tsx` | Blue home bar, gold away bar |
| `frontend/src/components/ExplanationPanel.tsx` | Surface2 stat cells, blue border toggle |
| `frontend/src/components/MetadataBadge.tsx` | Surface2 pills |

---

## Task 1: Trophy asset + Tailwind tokens + global animation

**Files:**
- Create: `frontend/public/trophy_nobg.png`
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Copy the trophy image to public/**

```bash
cp "C:/Users/Nimaa/OneDrive/Desktop/FIFA-WC-2026/.superpowers/brainstorm/1309-1778428415/content/trophy_nobg.png" \
   "C:/Users/Nimaa/OneDrive/Desktop/FIFA-WC-2026/frontend/public/trophy_nobg.png"
```

Verify: `ls frontend/public/trophy_nobg.png` — file should exist, size > 10KB.

- [ ] **Step 2: Extend Tailwind config with FIFA tokens**

Replace the full content of `frontend/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        navy: {
          900: "#090b14",
          800: "#0e1020",
          700: "#151829",
          600: "#1e2340",
        },
        pitch: {
          500: "#1a7a3c",
          400: "#22a052",
          300: "#2ec665",
        },
        gold: {
          500: "#f5c842",
          400: "#e8c84a",
          300: "#fde68a",
          dim: "#c9a227",
        },
        fifa: {
          blue: "#1a3fff",
          "blue-dark": "#0d1d8a",
          "blue-light": "#5b8fff",
        },
      },
      animation: {
        float: "float 4s ease-in-out infinite",
        "fade-in": "fade-in 0.6s ease-out both",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-18px)" },
        },
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 3: Update globals.css**

Replace the full content of `frontend/src/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: #090b14;
  color: white;
}

/* Diagonal texture overlay — reusable via class */
.hero-texture::after {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    -45deg,
    rgba(255, 255, 255, 0.012) 0px,
    rgba(255, 255, 255, 0.012) 1px,
    transparent 1px,
    transparent 28px
  );
  pointer-events: none;
}

.scrollbar-thin::-webkit-scrollbar { width: 6px; }
.scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
.scrollbar-thin::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
```

- [ ] **Step 4: Verify dev server starts cleanly**

```bash
cd frontend && npm run dev
```

Expected: server starts on port 3000, no TypeScript or Tailwind errors in terminal.

- [ ] **Step 5: Commit**

```bash
git add frontend/public/trophy_nobg.png frontend/tailwind.config.ts frontend/src/app/globals.css
git commit -m "feat: add FIFA theme tokens, float animation, trophy asset"
```

---

## Task 2: Hero section + Header restyle in page.tsx

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Add next/image import and update the header + hero**

Replace the `<main>` return block in `frontend/src/app/page.tsx`. Only the JSX changes — all hooks/state/handlers above are untouched.

Replace this block (lines 102–155, the `<main>` opening + header div):

```tsx
  return (
    <main className="min-h-screen bg-[#0a0e1a]">
      {/* Header */}
      <div className="border-b border-slate-800 bg-[#0d1428]">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <TrophyIcon className="h-7 w-7 text-[#d4af37] flex-shrink-0" />
          <div>
            <h1 className="text-lg font-bold text-white leading-tight">FIFA WC 2026 Predictor</h1>
            <p className="text-xs text-slate-400">AI-powered match outcome predictions</p>
          </div>
        </div>

        {/* Tab bar */}
        <div className="max-w-4xl mx-auto px-4 flex items-center gap-0 border-t border-slate-800/50">
          <button
            onClick={() => setTab("bracket")}
            className={`px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
              tab === "bracket"
                ? "border-[#d4af37] text-[#d4af37]"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Group Stage
          </button>
          <button
            onClick={() => setTab("predictor")}
            className={`px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
              tab === "predictor"
                ? "border-[#d4af37] text-[#d4af37]"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            Predict Match
          </button>
          {tab === "predictor" && (
            <div className="ml-auto flex items-center gap-2 py-2">
              <span className="text-xs text-slate-500">
                {showAllTeams ? "All teams" : "WC 2026 only"}
              </span>
              <button
                onClick={() => {
                  setShowAllTeams((v) => !v);
                  setHomeTeam(null);
                  setAwayTeam(null);
                  reset();
                }}
                className="text-xs px-2 py-1 rounded border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
              >
                {showAllTeams ? "Filter WC26" : "Show all"}
              </button>
            </div>
          )}
        </div>
      </div>
```

With:

```tsx
  return (
    <main className="min-h-screen bg-navy-900">
      {/* ── Sticky top bar ── */}
      <div className="sticky top-0 z-50 bg-navy-900/95 backdrop-blur border-b border-navy-600">
        <div className="max-w-4xl mx-auto px-4 h-11 flex items-center gap-3">
          <span className="text-fifa-blue font-black text-sm tracking-[3px] uppercase">FIFA</span>
          <span className="text-[10px] font-bold text-gold-500 bg-gold-500/10 border border-gold-500/25 rounded px-2 py-0.5 tracking-wider">
            WC 2026™
          </span>
          <span className="flex-1" />
          <span className="text-[11px] text-slate-500 hidden sm:block">Predictor · Powered by AI</span>
        </div>
      </div>

      {/* ── Hero ── */}
      <div className="hero-texture relative overflow-hidden bg-gradient-to-b from-fifa-blue-dark via-navy-900 to-navy-900">
        {/* corner glows */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute bottom-0 left-1/4 w-64 h-40 bg-green-500/5 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-64 h-40 bg-fifa-blue/10 rounded-full blur-3xl" />
        </div>
        <div className="relative z-10 max-w-4xl mx-auto px-4 py-10 flex flex-col items-center gap-4 text-center animate-fade-in">
          <p className="text-fifa-blue text-[11px] font-bold tracking-[3px] uppercase">FIFA World Cup 2026™</p>
          <Image
            src="/trophy_nobg.png"
            alt="FIFA World Cup Trophy"
            width={90}
            height={220}
            priority
            className="animate-float drop-shadow-[0_0_40px_rgba(245,200,66,0.8)]"
          />
          <h1 className="text-3xl font-black leading-tight bg-gradient-to-br from-white via-white to-gold-500 bg-clip-text text-transparent">
            FIFA WC 2026 Predictor
          </h1>
          <p className="text-sm text-slate-500 max-w-sm">
            AI-powered match outcome predictions for the biggest tournament on Earth
          </p>
          <button
            onClick={() => setTab("predictor")}
            className="mt-1 px-7 py-3 bg-fifa-blue text-white text-sm font-bold rounded-lg shadow-[0_4px_24px_rgba(26,63,255,0.5)] hover:bg-fifa-blue/90 transition-colors"
          >
            Predict a Match
          </button>
        </div>
      </div>

      {/* ── Tab bar ── */}
      <div className="bg-navy-800 border-b border-navy-600">
        <div className="max-w-4xl mx-auto px-4 flex items-center gap-0">
          <button
            onClick={() => setTab("bracket")}
            className={`px-5 py-3.5 text-sm font-semibold border-b-[3px] transition-colors ${
              tab === "bracket"
                ? "border-fifa-blue text-white"
                : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            Group Stage
          </button>
          <button
            onClick={() => setTab("predictor")}
            className={`px-5 py-3.5 text-sm font-semibold border-b-[3px] transition-colors ${
              tab === "predictor"
                ? "border-fifa-blue text-white"
                : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            Predict Match
          </button>
          {tab === "predictor" && (
            <div className="ml-auto flex items-center gap-2 py-2">
              <span className="text-xs text-slate-500">
                {showAllTeams ? "All teams" : "WC 2026 only"}
              </span>
              <button
                onClick={() => {
                  setShowAllTeams((v) => !v);
                  setHomeTeam(null);
                  setAwayTeam(null);
                  reset();
                }}
                className="text-xs px-2 py-1 rounded border border-navy-600 text-slate-500 hover:text-white hover:border-slate-500 transition-colors"
              >
                {showAllTeams ? "Filter WC26" : "Show all"}
              </button>
            </div>
          )}
        </div>
      </div>
```

- [ ] **Step 2: Add `Image` import at the top of page.tsx**

Add to the existing imports (after the `"use client"` line):

```tsx
import Image from "next/image";
```

Also remove the `TrophyIcon` import since it's no longer used:

```tsx
// Remove this line:
import { TrophyIcon, ArrowsRightLeftIcon } from "@heroicons/react/24/solid";
// Replace with:
import { ArrowsRightLeftIcon } from "@heroicons/react/24/solid";
```

- [ ] **Step 3: Update the content area background and card backgrounds**

In the same file, find the outer content wrapper div (line ~157):
```tsx
      <div className="max-w-4xl mx-auto px-4 py-6 flex flex-col gap-6">
```
Change to:
```tsx
      <div className="max-w-4xl mx-auto px-4 py-6 flex flex-col gap-6 bg-navy-900 min-h-screen">
```

Find the "Select Match" card (line ~174):
```tsx
            <div className="bg-[#0d1428] rounded-2xl border border-slate-800 p-6 flex flex-col gap-5">
```
Change to:
```tsx
            <div className="bg-navy-800 rounded-2xl border border-navy-600 p-6 flex flex-col gap-5">
```

Find the date input className (line ~235):
```tsx
                        className="rounded-lg bg-[#111d3c] border border-slate-600 text-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#d4af37] [color-scheme:dark]"
```
Change to:
```tsx
                        className="rounded-lg bg-navy-700 border border-navy-600 text-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-fifa-blue [color-scheme:dark]"
```

Find the swap button:
```tsx
                      className="mb-0.5 p-2.5 rounded-lg bg-[#111d3c] border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:text-slate-400 disabled:hover:border-slate-700"
```
Change to:
```tsx
                      className="mb-0.5 p-2.5 rounded-lg bg-navy-700 border border-navy-600 text-slate-400 hover:text-white hover:border-fifa-blue transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:text-slate-400 disabled:hover:border-navy-600"
```

Find all result card wrappers (`bg-[#0d1428] rounded-2xl border border-slate-800 p-6`), there are 5 occurrences — replace all with:
```tsx
bg-navy-800 rounded-2xl border border-navy-600 p-6
```

Find the stage/date label:
```tsx
                    <span className="bg-[#111d3c] border border-slate-700 px-2 py-0.5 rounded-full text-xs">
```
Change to:
```tsx
                    <span className="bg-navy-700 border border-navy-600 px-2 py-0.5 rounded-full text-xs">
```

- [ ] **Step 4: Check in browser**

Open http://localhost:3000 — confirm:
- Top bar shows FIFA wordmark + WC 2026™ badge
- Hero renders with floating trophy photo and gradient title
- Tab bar has blue underline on active tab
- Content area is dark navy

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat: add FIFA hero section and restyle header/tabs"
```

---

## Task 3: PredictButton — FIFA blue

**Files:**
- Modify: `frontend/src/components/PredictButton.tsx`

- [ ] **Step 1: Replace enabled-state styling**

Replace the full file content:

```tsx
"use client";
import clsx from "clsx";

interface Props {
  loading: boolean;
  disabled: boolean;
  onClick: () => void;
}

export default function PredictButton({ loading, disabled, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      aria-busy={loading}
      className={clsx(
        "w-full py-4 rounded-xl font-bold text-base tracking-wide transition-all duration-200",
        disabled || loading
          ? "bg-navy-700 text-slate-600 cursor-not-allowed"
          : "bg-fifa-blue text-white hover:bg-fifa-blue/90 shadow-[0_4px_20px_rgba(26,63,255,0.4)] hover:shadow-[0_4px_28px_rgba(26,63,255,0.6)]"
      )}
    >
      {loading ? (
        <span className="flex items-center justify-center gap-2">
          <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
          </svg>
          Predicting…
        </span>
      ) : (
        "Predict Outcome"
      )}
    </button>
  );
}
```

- [ ] **Step 2: Verify in browser**

Select two teams and confirm the button renders in electric blue with a blue glow shadow.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PredictButton.tsx
git commit -m "feat: restyle PredictButton to FIFA blue"
```

---

## Task 4: ProbabilityBars — blue gradient fill

**Files:**
- Modify: `frontend/src/components/ProbabilityBars.tsx`

- [ ] **Step 1: Replace the full file**

```tsx
"use client";
import { motion } from "framer-motion";
import type { Probabilities } from "@/lib/types";

interface Props {
  probabilities: Probabilities;
  homeTeam: string;
  awayTeam: string;
}

export default function ProbabilityBars({ probabilities, homeTeam, awayTeam }: Props) {
  const sum = probabilities.home_win + probabilities.draw + probabilities.away_win;
  const malformed = Math.abs(sum - 1.0) > 0.01;

  const bars = [
    { label: homeTeam,  value: probabilities.home_win, color: "from-fifa-blue to-fifa-blue-light" },
    { label: "Draw",    value: probabilities.draw,     color: "from-slate-500 to-slate-400" },
    { label: awayTeam,  value: probabilities.away_win, color: "from-gold-dim to-gold-500" },
  ];

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Match Outcome</h3>
      {malformed && (
        <p className="text-xs text-amber-400">
          Warning: probabilities sum to {(sum * 100).toFixed(1)}% — data may be malformed.
        </p>
      )}
      {bars.map((bar, i) => (
        <div key={bar.label} className="flex items-center gap-3">
          <span className="w-32 text-sm text-slate-300 truncate text-right">{bar.label}</span>
          <div className="flex-1 bg-navy-600 rounded-full h-7 overflow-hidden relative">
            <motion.div
              className={`h-full rounded-full bg-gradient-to-r ${bar.color}`}
              initial={{ width: 0 }}
              animate={{ width: `${(bar.value * 100).toFixed(1)}%` }}
              transition={{ duration: 0.6, delay: i * 0.15, ease: "easeOut" }}
            />
          </div>
          <span className="w-14 text-sm font-bold text-white text-right">
            {(bar.value * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Run a prediction and verify bars render in blue/grey/gold.**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ProbabilityBars.tsx
git commit -m "feat: restyle ProbabilityBars with FIFA blue gradient"
```

---

## Task 5: WinnerCallout — blue win highlight

**Files:**
- Modify: `frontend/src/components/WinnerCallout.tsx`

- [ ] **Step 1: Replace the full file**

```tsx
"use client";
import FlagIcon from "@/components/FlagIcon";
import type { Probabilities } from "@/lib/types";

interface Props {
  probabilities: Probabilities;
  homeTeam: string;
  awayTeam: string;
}

export default function WinnerCallout({ probabilities, homeTeam, awayTeam }: Props) {
  const { home_win, draw, away_win } = probabilities;

  let winnerLabel: string;
  let winnerPct: number;
  let isDraw: boolean;

  if (draw >= home_win && draw >= away_win) {
    winnerLabel = "Draw";
    winnerPct = draw;
    isDraw = true;
  } else if (home_win >= away_win) {
    winnerLabel = homeTeam;
    winnerPct = home_win;
    isDraw = false;
  } else {
    winnerLabel = awayTeam;
    winnerPct = away_win;
    isDraw = false;
  }

  return (
    <div className="flex flex-col gap-1 pb-4 mb-2 border-b border-navy-600">
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Predicted Winner
      </span>
      <div className="flex items-center gap-3">
        {!isDraw && (
          <FlagIcon team={winnerLabel} className="w-10 h-7 rounded flex-shrink-0" />
        )}
        <span className="text-lg font-bold text-white">{winnerLabel}</span>
        <span className="ml-auto text-lg font-bold px-3 py-0.5 rounded-lg bg-fifa-blue/10 border border-fifa-blue/40 text-fifa-blue-light">
          {(winnerPct * 100).toFixed(1)}%
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify probability pill renders in blue.**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/WinnerCallout.tsx
git commit -m "feat: restyle WinnerCallout with FIFA blue win pill"
```

---

## Task 6: MatchScoreboard — gold gradient score

**Files:**
- Modify: `frontend/src/components/MatchScoreboard.tsx`

- [ ] **Step 1: Replace the full file**

```tsx
"use client";
import FlagIcon from "@/components/FlagIcon";

interface Props {
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  compact?: boolean;
}

function teamLabel(name: string) {
  return name === "United States" ? "USA" : name;
}

export default function MatchScoreboard({ homeTeam, awayTeam, homeGoals, awayGoals, compact = false }: Props) {
  if (compact) {
    return (
      <div className="flex items-center gap-1 bg-navy-700 rounded-lg px-2.5 py-1 border border-gold-500/40 flex-shrink-0">
        <span className="text-sm font-bold text-gold-500 w-4 text-center tabular-nums">{homeGoals}</span>
        <span className="text-slate-500 text-xs">–</span>
        <span className="text-sm font-bold text-gold-500 w-4 text-center tabular-nums">{awayGoals}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Predicted Score</h3>
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 flex flex-col items-center gap-2">
          <FlagIcon team={homeTeam} className="w-16 h-12 rounded" />
          <span className="text-sm font-semibold text-white text-center">{teamLabel(homeTeam)}</span>
        </div>
        <div className="flex items-center gap-3 px-8 py-4 bg-navy-700 rounded-2xl border border-gold-500/40">
          <span className="text-5xl font-black tabular-nums bg-gradient-to-br from-white to-gold-500 bg-clip-text text-transparent">
            {homeGoals}
          </span>
          <span className="text-3xl text-slate-500 font-light">–</span>
          <span className="text-5xl font-black tabular-nums bg-gradient-to-br from-white to-gold-500 bg-clip-text text-transparent">
            {awayGoals}
          </span>
        </div>
        <div className="flex-1 flex flex-col items-center gap-2">
          <FlagIcon team={awayTeam} className="w-16 h-12 rounded" />
          <span className="text-sm font-semibold text-white text-center">{teamLabel(awayTeam)}</span>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run a prediction and verify score numbers show white-to-gold gradient.**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MatchScoreboard.tsx
git commit -m "feat: restyle MatchScoreboard with gold gradient score"
```

---

## Task 7: GroupBracket — FIFA blue accents

**Files:**
- Modify: `frontend/src/components/GroupBracket.tsx`

- [ ] **Step 1: Replace the full file**

```tsx
"use client";
import { WC2026_GROUPS, WCGroup } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";

interface Props {
  onSelectGroup: (group: WCGroup) => void;
}

const HOST_COLORS: Record<string, string> = {
  Mexico: "text-green-400",
  "United States": "text-blue-400",
  Canada: "text-red-400",
};

export default function GroupBracket({ onSelectGroup }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white">Group Stage</h2>
        <span className="text-xs text-slate-500">12 groups · 48 teams</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {WC2026_GROUPS.map((group) => (
          <button
            key={group.id}
            onClick={() => onSelectGroup(group)}
            className="bg-navy-800 border border-navy-600 rounded-xl p-4 text-left hover:border-fifa-blue hover:bg-navy-700 transition-all group"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold tracking-widest text-fifa-blue uppercase">
                Group {group.id}
              </span>
              <span className="text-xs text-slate-600 group-hover:text-slate-400 transition-colors">
                6 matches →
              </span>
            </div>
            <div className="flex flex-col gap-1.5">
              {group.teams.map((team) => (
                <div key={team} className="flex items-center gap-2">
                  <FlagIcon team={team} className="w-5 h-3.5 rounded-sm flex-shrink-0" />
                  <span className={`text-sm font-medium ${HOST_COLORS[team] ?? "text-slate-300"}`}>
                    {team === "United States" ? "USA" : team}
                  </span>
                </div>
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Check Group Stage tab — group cards should hover with blue border.**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/GroupBracket.tsx
git commit -m "feat: restyle GroupBracket with FIFA blue group labels and hover"
```

---

## Task 8: GroupView — blue fixture card hover + button restyle

**Files:**
- Modify: `frontend/src/components/GroupView.tsx`

- [ ] **Step 1: Replace hardcoded color strings**

In `frontend/src/components/GroupView.tsx`, make these targeted replacements:

Back button (line ~142):
```tsx
// Before:
className="p-1.5 rounded-lg bg-[#0d1428] border border-slate-800 text-slate-400 hover:text-white hover:border-slate-600 transition-colors"
// After:
className="p-1.5 rounded-lg bg-navy-800 border border-navy-600 text-slate-400 hover:text-white hover:border-fifa-blue transition-colors"
```

"Predict All" button (line ~152):
```tsx
// Before:
className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#d4af37] text-[#0a0e1a] text-sm font-bold hover:bg-[#e8c84a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
// After:
className="flex items-center gap-2 px-4 py-2 rounded-xl bg-fifa-blue text-white text-sm font-bold hover:bg-fifa-blue/90 shadow-[0_2px_12px_rgba(26,63,255,0.4)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
```

Teams strip container (line ~178):
```tsx
// Before:
className="bg-[#0d1428] border border-slate-800 rounded-xl p-4"
// After:
className="bg-navy-800 border border-navy-600 rounded-xl p-4"
```

Host label (line ~187):
```tsx
// Before:
<span className="text-[10px] text-[#d4af37]">Host</span>
// After:
<span className="text-[10px] text-gold-500">Host</span>
```

Fixture card container (line ~200):
```tsx
// Before:
className="bg-[#0d1428] border border-slate-800 rounded-xl p-4 flex items-center gap-3"
// After:
className="bg-navy-800 border border-navy-600 rounded-xl p-4 flex items-center gap-3 hover:border-fifa-blue transition-colors"
```

Per-match Predict button (line ~249):
```tsx
// Before:
className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[#d4af37]/10 border border-[#d4af37]/30 text-[#d4af37] text-xs font-semibold hover:bg-[#d4af37]/20 hover:border-[#d4af37]/60 transition-all"
// After:
className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg bg-fifa-blue/10 border border-fifa-blue/30 text-fifa-blue-light text-xs font-semibold hover:bg-fifa-blue/20 hover:border-fifa-blue/60 transition-all"
```

- [ ] **Step 2: Click into a group and verify fixture cards, back button, and Predict All render correctly.**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/GroupView.tsx
git commit -m "feat: restyle GroupView with FIFA blue buttons and fixture cards"
```

---

## Task 9: Remaining result components

**Files:**
- Modify: `frontend/src/components/ScorelineGrid.tsx`
- Modify: `frontend/src/components/ExpectedGoals.tsx`
- Modify: `frontend/src/components/ExplanationPanel.tsx`
- Modify: `frontend/src/components/MetadataBadge.tsx`

- [ ] **Step 1: Replace ScorelineGrid.tsx**

```tsx
"use client";
import clsx from "clsx";
import type { Scoreline } from "@/lib/types";

interface Props {
  scorelines: Scoreline[];
}

export default function ScorelineGrid({ scorelines }: Props) {
  if (!scorelines || scorelines.length === 0) {
    return (
      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Top Scorelines</h3>
        <p className="text-slate-500 text-sm">No scoreline probabilities available.</p>
      </div>
    );
  }

  const max = Math.max(...scorelines.map((s) => s.probability));
  const safeMax = max > 0 ? max : 1;

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Top Scorelines</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
        {scorelines.map((s, i) => (
          <div
            key={s.scoreline}
            className={clsx(
              "flex flex-col items-center justify-center rounded-xl py-4 px-2 bg-navy-700 border",
              i === 0 ? "border-fifa-blue" : "border-navy-600"
            )}
          >
            <span className={clsx("text-2xl font-bold", i === 0 ? "text-fifa-blue-light" : "text-white")}>
              {s.scoreline}
            </span>
            <span className="text-xs text-slate-400 mt-1">{(s.probability * 100).toFixed(1)}%</span>
            <div className="w-full bg-navy-600 rounded-full h-1 mt-2">
              <div
                className={clsx("h-1 rounded-full", i === 0 ? "bg-fifa-blue" : "bg-slate-500")}
                style={{ width: `${(s.probability / safeMax) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Replace ExpectedGoals.tsx**

```tsx
"use client";

interface Props {
  xg: { home: number; away: number };
  homeTeam: string;
  awayTeam: string;
}

export default function ExpectedGoals({ xg, homeTeam, awayTeam }: Props) {
  const total = xg.home + xg.away;
  const homePct = total === 0 ? 50 : (xg.home / total) * 100;

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Expected Goals (xG)</h3>
      <div className="flex items-center justify-between gap-6">
        <div className="flex-1 text-center">
          <div className="text-4xl font-bold text-fifa-blue-light">{xg.home.toFixed(2)}</div>
          <div className="text-sm text-slate-400 mt-1 truncate">{homeTeam}</div>
        </div>
        <div className="text-slate-500 font-bold text-xl">vs</div>
        <div className="flex-1 text-center">
          <div className="text-4xl font-bold text-gold-500">{xg.away.toFixed(2)}</div>
          <div className="text-sm text-slate-400 mt-1 truncate">{awayTeam}</div>
        </div>
      </div>
      <div className="flex h-2 rounded-full overflow-hidden">
        <div className="bg-fifa-blue transition-all duration-500" style={{ width: `${homePct}%` }} />
        <div className="bg-gold-500 flex-1" />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Replace ExplanationPanel.tsx**

```tsx
"use client";
import { useState } from "react";
import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/20/solid";
import type { Explanation } from "@/lib/types";

interface Props {
  explanation: Explanation;
  homeTeam: string;
  awayTeam: string;
}

function StatRow({ label, home, away }: { label: string; home: string; away: string }) {
  return (
    <div className="grid grid-cols-3 gap-2 text-sm py-2 border-b border-navy-600">
      <span className="text-slate-400">{label}</span>
      <span className="text-center text-white font-mono">{home}</span>
      <span className="text-center text-white font-mono">{away}</span>
    </div>
  );
}

export default function ExplanationPanel({ explanation, homeTeam, awayTeam }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex flex-col gap-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-sm font-semibold text-slate-400 uppercase tracking-wider hover:text-white transition-colors"
      >
        {open ? <ChevronUpIcon className="h-4 w-4" /> : <ChevronDownIcon className="h-4 w-4" />}
        Model Explanation
      </button>
      {open && (
        <div className="bg-navy-700 rounded-xl p-4 border border-navy-600">
          <div className="grid grid-cols-3 gap-2 text-xs font-bold uppercase tracking-wider text-slate-500 pb-2 border-b border-navy-600 mb-1">
            <span>Stat</span>
            <span className="text-center truncate">{homeTeam}</span>
            <span className="text-center truncate">{awayTeam}</span>
          </div>
          <StatRow label="Elo Rating" home={explanation.home_elo.toFixed(0)} away={explanation.away_elo.toFixed(0)} />
          <StatRow label="Form (PPG)" home={explanation.home_form.toFixed(2)} away={explanation.away_form.toFixed(2)} />
          <StatRow label="FIFA Rank" home={`#${explanation.home_rank}`} away={`#${explanation.away_rank}`} />
          <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div className="bg-navy-800 rounded-lg p-3">
              <div className="text-slate-400 text-xs">Elo Win Prob</div>
              <div className="text-white font-bold">{(explanation.elo_win_prob * 100).toFixed(1)}%</div>
            </div>
            <div className="bg-navy-800 rounded-lg p-3">
              <div className="text-slate-400 text-xs">Competition Weight</div>
              <div className="text-white font-bold">{explanation.competition_weight.toFixed(2)}</div>
            </div>
            <div className="bg-navy-800 rounded-lg p-3">
              <div className="text-slate-400 text-xs">Same Confederation</div>
              <div className="text-white font-bold">{explanation.is_same_confederation ? "Yes" : "No"}</div>
            </div>
            <div className="bg-navy-800 rounded-lg p-3">
              <div className="text-slate-400 text-xs">Elo Diff</div>
              <div className="text-white font-bold">{explanation.elo_diff > 0 ? "+" : ""}{explanation.elo_diff.toFixed(0)}</div>
            </div>
          </div>
          {explanation.data_note && (
            <p className="mt-3 text-xs text-slate-500 italic">{explanation.data_note}</p>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Replace MetadataBadge.tsx**

```tsx
import type { PredictResponse } from "@/lib/types";

interface Props {
  result: PredictResponse;
}

export default function MetadataBadge({ result }: Props) {
  const modelType = result.metadata?.model_type as string | undefined;
  const trainingCutoff = result.metadata?.training_cutoff as string | undefined;
  const scoreline = result.metadata?.scoreline_model_status as string | undefined;
  const available = scoreline !== "unavailable";
  const predictionTs = result.metadata?.prediction_timestamp as string | undefined;

  const timeLabel = predictionTs
    ? new Date(predictionTs).toLocaleTimeString()
    : new Date().toLocaleTimeString();
  const timePrefix = predictionTs ? "Predicted at" : "Viewed at";

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
      {modelType && (
        <span className="bg-navy-700 border border-navy-600 px-2 py-1 rounded-full">{modelType}</span>
      )}
      {trainingCutoff && (
        <span className="bg-navy-700 border border-navy-600 px-2 py-1 rounded-full">
          Trained to {trainingCutoff}
        </span>
      )}
      <span className="flex items-center gap-1 bg-navy-700 border border-navy-600 px-2 py-1 rounded-full">
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${available ? "bg-green-400" : "bg-red-500"}`} />
        Scoreline model {available ? "active" : "inactive"}
      </span>
      <span className="bg-navy-700 border border-navy-600 px-2 py-1 rounded-full">
        {timePrefix} {timeLabel}
      </span>
    </div>
  );
}
```

- [ ] **Step 5: Run a full prediction in the browser and verify all result panels look correct.**

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ScorelineGrid.tsx \
        frontend/src/components/ExpectedGoals.tsx \
        frontend/src/components/ExplanationPanel.tsx \
        frontend/src/components/MetadataBadge.tsx
git commit -m "feat: restyle result components with FIFA theme"
```

---

## Done

After Task 9, the full FIFA theme is live. Run `npm run build` in `frontend/` to confirm no TypeScript errors before calling it complete.
