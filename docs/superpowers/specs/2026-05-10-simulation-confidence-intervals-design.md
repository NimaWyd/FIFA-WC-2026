# Design: Tournament Simulation & Confidence Intervals

**Issues:** #22 (Simulation mode), #20 (Confidence Interval)
**Date:** 2026-05-10
**Status:** Approved

---

## Overview

Two additive features built on top of the existing ensemble model and API — no retraining required.

1. **Simulate tab (#22):** Run the full WC2026 tournament 1000x via Monte Carlo simulation. Show per-team probabilities for each stage: group advancement, R32, QF, SF, Final, Champion.
2. **Confidence intervals (#20):** Show uncertainty ranges on match predictor results, derived from the spread across the ensemble's 3 component models (XGBoost, LogReg, MLP).

---

## Architecture

```
Backend                              Frontend
─────────────────────────────────────────────────────────
GET /api/v1/simulate             →   New "Simulate" tab
  Monte Carlo simulation              SimulationPanel.tsx
  1000 iterations, server-side        useSimulation.ts hook
  cached after first call             Full 48-team table
  returns TeamSimResult[]             + champion podium

POST /api/v1/predict             →   Existing results panel
  (modified — adds confidence)        ProbabilityBars.tsx
  min/max across XGB/LogReg/MLP       gets optional confidence
  per outcome, no extra compute       prop → ± range display
```

---

## Backend

### New module: `src/simulation/wc2026_bracket.py`

Defines both the group structure and the exact R32 bracket as Python constants — mirrors `frontend/src/lib/wc2026Groups.ts` on the backend.

**Group structure:** 12 groups (A–L), 4 teams each, 48 group stage matches.

**R32 bracket** (WC2026 format — different from all previous World Cups):

| Match | Matchup |
|-------|---------|
| 73 | Runner-up A vs Runner-up B |
| 74 | Winner E vs Best 3rd (A/B/C/D/F) |
| 75 | Winner F vs Runner-up C |
| 76 | Winner C vs Runner-up F |
| 77 | Winner I vs Best 3rd (C/D/F/G/H) |
| 78 | Runner-up E vs Runner-up I |
| 79 | Winner A vs Best 3rd (C/E/F/H/I) |
| 80 | Winner L vs Best 3rd (E/H/I/J/K) |
| 81 | Winner D vs Best 3rd (B/E/F/I/J) |
| 82 | Winner G vs Best 3rd (A/E/H/I/J) |
| 83 | Runner-up K vs Runner-up L |
| 84 | Winner H vs Runner-up J |
| 85 | Winner B vs Best 3rd (E/F/G/I/J) |
| 86 | Winner J vs Runner-up H |
| 87 | Winner K vs Best 3rd (D/E/I/J/L) |
| 88 | Runner-up D vs Runner-up G |

**3rd-place seeding:** Each "Best 3rd" slot has an eligible group list (shown above). After identifying the 8 best third-place teams, assign each to the slot whose eligible groups include their origin group. Where multiple slots are eligible, assign randomly — this matches FIFA's Annex C logic at a level of precision acceptable for Monte Carlo averaging.

This is the single source of truth for the simulation bracket on the backend.

### New module: `src/simulation/tournament.py`

**`build_tournament_states(history_df, cfg) → TeamStateTracker`**
- Replays all match history strictly before `2026-06-11` through `TeamStateTracker`
- Called once; the returned tracker snapshot is treated as **read-only** — it is never updated with simulated match results
- All match predictions throughout the simulation (group stage and knockout rounds) use pre-tournament Elo/form from this snapshot

**`predict_match_proba(home, away, tracker, model, cfg) → dict[str, float]`**
- Builds a feature row from the tracker snapshot via `build_match_row()`
- Calls `model.predict_proba()` directly — does NOT call `services.predict()` to avoid re-replaying history per call
- Returns `{"home_win": float, "draw": float, "away_win": float}`

**`simulate_once(tracker, model, cfg) → dict[str, str]`**
- Simulates all 48 group stage matches by sampling outcomes from predicted probabilities
- Computes group standings: sort by pts → GD → GF
- Top 2 from each of 12 groups → 24 teams advance automatically
- Collect all 12 third-place finishers → rank by pts → GD → GF → top 8 advance
- 3rd-place bracket seeding: randomly assigned to open R32 slots (noise washes out over 1000 runs)
- Simulates R32 → QF → SF → Final; records stage reached per team
- Returns `{team_name: stage}` where stage ∈ `{"group_exit", "round_of_32", "quarter_final", "semi_final", "final", "champion"}` for all 48 teams

**`run_simulation(n=1000) → SimulationResponse`**
- Calls `simulate_once` n times
- Aggregates stage counts → divides by n → returns per-team probabilities

### New route: `GET /api/v1/simulate`

```python
@router.get("/simulate", response_model=SimulationResponse, tags=["simulation"])
def simulate() -> SimulationResponse:
    ...
```

Results cached in `services.py` as `_simulation_cache` (same singleton pattern as `_model`). Cache is valid for the lifetime of the server process.

### New schemas

```python
class TeamSimResult(BaseModel):
    team: str
    group: str
    group_exit: float      # P(eliminated in group stage)
    round_of_32: float     # P(reach R32)
    quarter_final: float
    semi_final: float
    final: float
    champion: float

class SimulationResponse(BaseModel):
    n_simulations: int
    teams: list[TeamSimResult]
    generated_at: str      # ISO timestamp of when simulation ran
```

### Modified `/predict` response

Add `confidence` to `PredictResponse` and `services.predict()`:

```python
class ConfidenceInterval(BaseModel):
    home_win: tuple[float, float]   # (min, max) across XGB/LogReg/MLP
    draw: tuple[float, float]
    away_win: tuple[float, float]

class PredictResponse(BaseModel):
    ...  # existing fields unchanged
    confidence: Optional[ConfidenceInterval] = None
```

In `services.py`, extract individual model predictions from `EnsembleModel` before blending. `confidence` is `None` if the loaded model is not an ensemble.

---

## Frontend

### New tab

Add `"simulate"` to the `Tab` union type in `page.tsx`. Tab bar:
`Group Stage | Predict Match | Simulate`

### New files

**`src/hooks/useSimulation.ts`**
- Fetches `GET /simulate` on mount
- Returns `{ data, loading, error }`
- Same pattern as `useTeams.ts`

**`src/components/SimulationPanel.tsx`**
- Champion podium: top 3–5 teams by `champion` probability, shown as large flag + name + % cards
- Full sortable table: all 48 teams, columns = Group | Advance | R32 | QF | SF | Final | Champion
- Probability cells rendered as colored pills — green shade proportional to value
- Default sort: by `champion` descending
- Clicking any column header re-sorts

### Modified files

**`src/lib/types.ts`** — add:
```ts
export interface ConfidenceInterval {
  home_win: [number, number];
  draw: [number, number];
  away_win: [number, number];
}

export interface TeamSimResult {
  team: string;
  group: string;
  group_exit: number;
  round_of_32: number;
  quarter_final: number;
  semi_final: number;
  final: number;
  champion: number;
}

export interface SimulationResponse {
  n_simulations: number;
  teams: TeamSimResult[];
  generated_at: string;
}

// PredictResponse gets:
confidence?: ConfidenceInterval;
```

**`src/lib/api.ts`** — add:
```ts
export async function fetchSimulation(): Promise<SimulationResponse> {
  const res = await fetchWithTimeout(`${BASE}/simulate`, {}, 60_000); // longer timeout
  return handleResponse<SimulationResponse>(res);
}
```

**`src/components/ProbabilityBars.tsx`** — add optional `confidence?: ConfidenceInterval` prop. When present, render a thin lighter bar behind each main bar showing the low→high range, with a small `± X%` label (where X = half the spread, rounded).

---

## Data Flow: Simulation

```
services.simulate()
  └─ build_tournament_states()          # replay history once
  └─ run_simulation(n=1000)
       └─ simulate_once() × 1000
            ├─ predict all group matches (48 calls to predict_match_proba)
            ├─ compute standings (pts → GD → GF)
            ├─ pick top 2 per group (24 teams)
            ├─ pick best 8 third-place teams (by pts → GD → GF)
            ├─ randomly seed 3rd-place into bracket slots
            └─ simulate R32 → QF → SF → Final
  └─ aggregate counts / n → probabilities
  └─ cache result
```

---

## Error Handling

- `/simulate` returns 503 if model not loaded (same as `/predict`)
- `confidence` is omitted (null) if model artifact is not `EnsembleModel`
- `useSimulation` hook surfaces error state; `SimulationPanel` shows an error card
- `/simulate` timeout on frontend set to 60s (simulation can take a few seconds)

---

## Out of Scope

- Re-running simulation on demand from the UI (cache is server-lifetime)
- Knockout bracket visualization (tree diagram) — table only for now
- Confidence intervals on simulation results (simulation spread is itself the uncertainty)
- Updating simulation as WC matches are played (future issue)
