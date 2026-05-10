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

Defines the WC2026 group structure as a Python constant — mirrors `frontend/src/lib/wc2026Groups.ts` but kept in the backend to avoid any frontend/backend coupling:

```python
WC2026_GROUPS: list[dict] = [
    {"id": "A", "teams": ["Mexico", "Korea Republic", "South Africa", "Czechia"], "matches": [...]},
    ...  # all 12 groups, 48 group stage matches with home/away/date
]
```

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
