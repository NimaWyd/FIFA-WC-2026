# Tournament Simulation & Confidence Intervals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full WC2026 Monte Carlo tournament simulation tab and per-prediction confidence intervals derived from the ensemble's three component models.

**Architecture:** Confidence intervals are extracted from XGB/LogReg/MLP individual outputs already computed inside `EnsembleModel.predict_proba` and appended to the existing `/predict` response. The simulation runs 1000 full WC2026 tournaments server-side using a pre-computed `TeamStateTracker` snapshot and the existing ensemble, caches the result in memory, and exposes it via a new `GET /simulate` endpoint. The frontend adds a third "Simulate" tab showing per-team stage probabilities.

**Tech Stack:** Python (FastAPI, numpy, pandas, joblib), scikit-learn ensemble, Next.js 14 / TypeScript / Tailwind CSS / Framer Motion

---

## File Map

**Create:**
- `fifa-2026-predictor/src/simulation/__init__.py`
- `fifa-2026-predictor/src/simulation/wc2026_bracket.py` — group teams + match schedule + R32 bracket
- `fifa-2026-predictor/src/simulation/tournament.py` — simulation logic
- `fifa-2026-predictor/tests/test_simulation.py` — simulation tests
- `frontend/src/hooks/useSimulation.ts` — fetch + cache simulation results
- `frontend/src/components/SimulationPanel.tsx` — champion podium + sortable table

**Modify:**
- `fifa-2026-predictor/src/api/schemas.py` — add `ConfidenceInterval`, `TeamSimResult`, `SimulationResponse`; add `confidence` to `PredictResponse`
- `fifa-2026-predictor/src/api/services.py` — extract per-model CI in `predict()`; add `simulate()` with cache
- `fifa-2026-predictor/src/api/routes.py` — add `GET /simulate`
- `frontend/src/lib/types.ts` — add `ConfidenceInterval`, `TeamSimResult`, `SimulationResponse`; add `confidence?` to `PredictResponse`
- `frontend/src/lib/api.ts` — add `fetchSimulation()`
- `frontend/src/components/ProbabilityBars.tsx` — add optional `confidence` prop + ± range display
- `frontend/src/app/page.tsx` — add "Simulate" tab

---

## Task 1: Backend CI — schemas + extraction

**Files:**
- Modify: `fifa-2026-predictor/src/api/schemas.py`
- Modify: `fifa-2026-predictor/src/api/services.py`
- Create: `fifa-2026-predictor/tests/test_confidence_intervals.py`

- [ ] **Step 1: Write failing test**

```python
# fifa-2026-predictor/tests/test_confidence_intervals.py
"""Tests for ensemble confidence interval extraction (issue #20)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.ensemble_model import EnsembleModel


def _make_dummy_ensemble() -> EnsembleModel:
    """Build a minimal EnsembleModel with stub pipelines for testing."""
    from unittest.mock import MagicMock

    def _make_pipeline(probs: list[float]):
        pipeline = MagicMock()
        pipeline.predict_proba.return_value = np.array([probs])
        clf = MagicMock()
        clf.classes_ = np.array([0, 1, 2])
        pipeline.named_steps = {"classifier": clf}
        return pipeline

    draw_sub = MagicMock()
    draw_sub.predict_proba.return_value = np.array([[0.3, 0.3]])  # class 1 = 0.3

    return EnsembleModel(
        xgb_pipeline=_make_pipeline([0.2, 0.3, 0.5]),    # A=0.2, D=0.3, H=0.5
        logreg_pipeline=_make_pipeline([0.3, 0.3, 0.4]), # A=0.3, D=0.3, H=0.4
        mlp_pipeline=_make_pipeline([0.25, 0.35, 0.40]), # A=0.25, D=0.35, H=0.40
        draw_submodel=draw_sub,
        per_class_weights=np.array([[1/3, 1/3, 1/3], [1/3, 1/3, 1/3], [1/3, 1/3, 1/3]]),
        draw_blend_weight=0.3,
        feature_cols=["elo_diff_home_away"],
    )


def test_extract_per_model_probas_returns_correct_shape():
    """_extract_ci should return (3, 3) array — 3 models × 3 classes."""
    from src.api.services import _extract_ensemble_ci
    ensemble = _make_dummy_ensemble()
    X = pd.DataFrame([{"elo_diff_home_away": 50.0}])
    ci = _extract_ensemble_ci(ensemble, X)
    assert ci is not None
    assert "home_win" in ci and "draw" in ci and "away_win" in ci
    lo, hi = ci["home_win"]
    assert 0.0 <= lo <= hi <= 1.0


def test_ci_bounds_bracket_blended_value():
    """The blended prediction should fall within [lo, hi] for each outcome."""
    from src.api.services import _extract_ensemble_ci
    ensemble = _make_dummy_ensemble()
    X = pd.DataFrame([{"elo_diff_home_away": 50.0}])
    ci = _extract_ensemble_ci(ensemble, X)
    blended = ensemble.predict_proba(X)[0]  # [A, D, H]
    assert ci["home_win"][0] <= blended[2] <= ci["home_win"][1]
    assert ci["draw"][0] <= blended[1] <= ci["draw"][1]
    assert ci["away_win"][0] <= blended[0] <= ci["away_win"][1]


def test_non_ensemble_returns_none():
    """_extract_ensemble_ci returns None for non-EnsembleModel inputs."""
    from src.api.services import _extract_ensemble_ci
    assert _extract_ensemble_ci(object(), pd.DataFrame()) is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd fifa-2026-predictor
pytest tests/test_confidence_intervals.py -v
```
Expected: ImportError or AttributeError — `_extract_ensemble_ci` does not exist yet.

- [ ] **Step 3: Add `ConfidenceInterval` to schemas and `confidence` to `PredictResponse`**

In `fifa-2026-predictor/src/api/schemas.py`, add after the `Probabilities` class:

```python
class ConfidenceInterval(BaseModel):
    home_win: tuple[float, float]   # (min, max) across XGB / LogReg / MLP
    draw: tuple[float, float]
    away_win: tuple[float, float]
```

And add `confidence` as an optional field on `PredictResponse`:

```python
class PredictResponse(BaseModel):
    home_team: str
    away_team: str
    match_date: str
    probabilities: Probabilities
    top_scorelines: list[Scoreline]
    expected_goals: dict[str, float]
    explanation: Explanation
    metadata: dict[str, Any]
    confidence: Optional[ConfidenceInterval] = None   # ← add this line
```

- [ ] **Step 4: Add `_extract_ensemble_ci` to services.py**

In `fifa-2026-predictor/src/api/services.py`, add the import at the top of the file (with the other model imports):

```python
from src.models.ensemble_model import EnsembleModel
```

Then add this function before the `predict()` function:

```python
def _extract_ensemble_ci(
    model: Any, feature_row: "pd.DataFrame"
) -> Optional[dict[str, tuple[float, float]]]:
    """Extract per-model probabilities from EnsembleModel; return None if not applicable."""
    if not isinstance(model, EnsembleModel):
        return None
    try:
        p_xgb = model._get_base_proba(model.xgb_pipeline, feature_row)[0]   # [A, D, H]
        p_logreg = model._get_base_proba(model.logreg_pipeline, feature_row)[0]
        p_mlp = model._get_base_proba(model.mlp_pipeline, feature_row)[0]
        all_p = np.array([p_xgb, p_logreg, p_mlp])  # (3 models, 3 classes)
        return {
            "home_win": (float(all_p[:, 2].min()), float(all_p[:, 2].max())),
            "draw":     (float(all_p[:, 1].min()), float(all_p[:, 1].max())),
            "away_win": (float(all_p[:, 0].min()), float(all_p[:, 0].max())),
        }
    except Exception:
        return None
```

Add `import numpy as np` to services.py if not already present (check first).

- [ ] **Step 5: Wire CI into `predict()` return value**

In `services.py` `predict()`, after the `probabilities` dict is built (around line 253), add:

```python
confidence = _extract_ensemble_ci(model, feature_row)
```

Then in the `return` dict at the end of `predict()`, add the confidence key:

```python
return {
    ...existing keys...,
    "confidence": confidence,
}
```

- [ ] **Step 6: Wire CI into the route response**

In `fifa-2026-predictor/src/api/routes.py`, update the `predict` route's return to pass `confidence`:

```python
return schemas.PredictResponse(
    home_team=result["home_team"],
    away_team=result["away_team"],
    match_date=result["match_date"],
    probabilities=schemas.Probabilities(**result["probabilities"]),
    top_scorelines=[schemas.Scoreline(**s) for s in result["top_scorelines"]],
    expected_goals=result["expected_goals"],
    explanation=schemas.Explanation(**result["explanation"]),
    metadata=result["metadata"],
    confidence=schemas.ConfidenceInterval(**result["confidence"]) if result.get("confidence") else None,
)
```

- [ ] **Step 7: Run tests to confirm they pass**

```
cd fifa-2026-predictor
pytest tests/test_confidence_intervals.py -v
```
Expected: 3 PASSED

- [ ] **Step 8: Commit**

```bash
git add fifa-2026-predictor/src/api/schemas.py fifa-2026-predictor/src/api/services.py fifa-2026-predictor/src/api/routes.py fifa-2026-predictor/tests/test_confidence_intervals.py
git commit -m "feat: add confidence intervals to /predict response (issue #20)"
```

---

## Task 2: Frontend CI — types + ProbabilityBars

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/components/ProbabilityBars.tsx`

- [ ] **Step 1: Add `ConfidenceInterval` to types.ts**

In `frontend/src/lib/types.ts`, add after the `Probabilities` interface:

```ts
export interface ConfidenceInterval {
  home_win: [number, number];
  draw: [number, number];
  away_win: [number, number];
}
```

Add `confidence?: ConfidenceInterval;` to `PredictResponse`:

```ts
export interface PredictResponse {
  home_team: string;
  away_team: string;
  match_date: string;
  probabilities: Probabilities;
  top_scorelines: Scoreline[];
  expected_goals: { home: number; away: number };
  explanation: Explanation;
  metadata: Record<string, unknown>;
  confidence?: ConfidenceInterval;   // ← add this line
}
```

- [ ] **Step 2: Update `ProbabilityBars.tsx` to accept and render CI**

Replace the entire file content:

```tsx
"use client";
import { motion } from "framer-motion";
import type { Probabilities, ConfidenceInterval } from "@/lib/types";

interface Props {
  probabilities: Probabilities;
  homeTeam: string;
  awayTeam: string;
  confidence?: ConfidenceInterval;
}

export default function ProbabilityBars({ probabilities, homeTeam, awayTeam, confidence }: Props) {
  const sum = probabilities.home_win + probabilities.draw + probabilities.away_win;
  const malformed = Math.abs(sum - 1.0) > 0.01;

  const bars = [
    {
      label: homeTeam,
      value: probabilities.home_win,
      color: "from-fifa-blue to-fifa-blue-light",
      ci: confidence?.home_win,
    },
    {
      label: "Draw",
      value: probabilities.draw,
      color: "from-slate-500 to-slate-400",
      ci: confidence?.draw,
    },
    {
      label: awayTeam,
      value: probabilities.away_win,
      color: "from-gold-dim to-gold-500",
      ci: confidence?.away_win,
    },
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
            {bar.ci && (
              <div
                className="absolute h-full rounded-full bg-white/10"
                style={{
                  left: `${(bar.ci[0] * 100).toFixed(1)}%`,
                  width: `${((bar.ci[1] - bar.ci[0]) * 100).toFixed(1)}%`,
                }}
              />
            )}
            <motion.div
              className={`h-full rounded-full bg-gradient-to-r ${bar.color}`}
              initial={{ width: 0 }}
              animate={{ width: `${(bar.value * 100).toFixed(1)}%` }}
              transition={{ duration: 0.6, delay: i * 0.15, ease: "easeOut" }}
            />
          </div>
          <div className="w-14 text-right">
            <span className="text-sm font-bold text-white">{(bar.value * 100).toFixed(1)}%</span>
            {bar.ci && (
              <p className="text-[10px] text-slate-500 leading-tight">
                ±{(((bar.ci[1] - bar.ci[0]) / 2) * 100).toFixed(1)}%
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Pass `confidence` to `ProbabilityBars` in page.tsx**

In `frontend/src/app/page.tsx`, find the `<ProbabilityBars>` usage and add the `confidence` prop:

```tsx
<ProbabilityBars
  probabilities={result.probabilities}
  homeTeam={result.home_team}
  awayTeam={result.away_team}
  confidence={result.confidence}
/>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/components/ProbabilityBars.tsx frontend/src/app/page.tsx
git commit -m "feat: show confidence interval range on probability bars (issue #20)"
```

---

## Task 3: Simulation bracket data

**Files:**
- Create: `fifa-2026-predictor/src/simulation/__init__.py`
- Create: `fifa-2026-predictor/src/simulation/wc2026_bracket.py`

- [ ] **Step 1: Write failing test for bracket structure**

Create `fifa-2026-predictor/tests/test_simulation.py`:

```python
"""Tests for WC2026 tournament simulation (issue #22)."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_bracket_has_12_groups():
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    assert len(WC2026_GROUPS) == 12


def test_each_group_has_4_teams_and_6_matches():
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    for group in WC2026_GROUPS:
        assert len(group["teams"]) == 4, f"Group {group['id']} has wrong team count"
        assert len(group["matches"]) == 6, f"Group {group['id']} has wrong match count"


def test_bracket_has_48_unique_teams():
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    all_teams = [t for g in WC2026_GROUPS for t in g["teams"]]
    assert len(all_teams) == 48
    assert len(set(all_teams)) == 48, "Duplicate teams found"


def test_r32_has_16_matchups():
    from src.simulation.wc2026_bracket import WC2026_R32
    assert len(WC2026_R32) == 16


def test_r32_has_8_third_place_slots():
    from src.simulation.wc2026_bracket import WC2026_R32
    third_slots = [m for m in WC2026_R32 if m["slot1_type"] == "3rd" or m["slot2_type"] == "3rd"]
    assert len(third_slots) == 8
```

- [ ] **Step 2: Run test to confirm it fails**

```
cd fifa-2026-predictor
pytest tests/test_simulation.py::test_bracket_has_12_groups -v
```
Expected: ModuleNotFoundError

- [ ] **Step 3: Create `src/simulation/__init__.py`**

```python
# fifa-2026-predictor/src/simulation/__init__.py
```
(empty file)

- [ ] **Step 4: Create `wc2026_bracket.py`**

```python
# fifa-2026-predictor/src/simulation/wc2026_bracket.py
"""WC2026 group structure and R32 bracket — backend counterpart to frontend/src/lib/wc2026Groups.ts."""
from __future__ import annotations

WC2026_GROUPS: list[dict] = [
    {
        "id": "A",
        "teams": ["Mexico", "Korea Republic", "South Africa", "Czechia"],
        "matches": [
            {"home": "Mexico", "away": "South Africa", "date": "2026-06-11"},
            {"home": "Korea Republic", "away": "Czechia", "date": "2026-06-12"},
            {"home": "Mexico", "away": "Korea Republic", "date": "2026-06-18"},
            {"home": "Czechia", "away": "South Africa", "date": "2026-06-18"},
            {"home": "Czechia", "away": "Mexico", "date": "2026-06-25"},
            {"home": "South Africa", "away": "Korea Republic", "date": "2026-06-25"},
        ],
    },
    {
        "id": "B",
        "teams": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
        "matches": [
            {"home": "Canada", "away": "Bosnia and Herzegovina", "date": "2026-06-12"},
            {"home": "Qatar", "away": "Switzerland", "date": "2026-06-13"},
            {"home": "Switzerland", "away": "Bosnia and Herzegovina", "date": "2026-06-18"},
            {"home": "Canada", "away": "Qatar", "date": "2026-06-18"},
            {"home": "Switzerland", "away": "Canada", "date": "2026-06-24"},
            {"home": "Bosnia and Herzegovina", "away": "Qatar", "date": "2026-06-24"},
        ],
    },
    {
        "id": "C",
        "teams": ["Brazil", "Morocco", "Scotland", "Haiti"],
        "matches": [
            {"home": "Brazil", "away": "Morocco", "date": "2026-06-13"},
            {"home": "Haiti", "away": "Scotland", "date": "2026-06-13"},
            {"home": "Scotland", "away": "Morocco", "date": "2026-06-19"},
            {"home": "Brazil", "away": "Haiti", "date": "2026-06-19"},
            {"home": "Morocco", "away": "Haiti", "date": "2026-06-24"},
            {"home": "Scotland", "away": "Brazil", "date": "2026-06-24"},
        ],
    },
    {
        "id": "D",
        "teams": ["United States", "Paraguay", "Australia", "Turkey"],
        "matches": [
            {"home": "United States", "away": "Paraguay", "date": "2026-06-12"},
            {"home": "Australia", "away": "Turkey", "date": "2026-06-14"},
            {"home": "United States", "away": "Australia", "date": "2026-06-19"},
            {"home": "Turkey", "away": "Paraguay", "date": "2026-06-19"},
            {"home": "Turkey", "away": "United States", "date": "2026-06-25"},
            {"home": "Paraguay", "away": "Australia", "date": "2026-06-25"},
        ],
    },
    {
        "id": "E",
        "teams": ["Germany", "Côte d'Ivoire", "Ecuador", "Curaçao"],
        "matches": [
            {"home": "Germany", "away": "Curaçao", "date": "2026-06-14"},
            {"home": "Côte d'Ivoire", "away": "Ecuador", "date": "2026-06-14"},
            {"home": "Germany", "away": "Côte d'Ivoire", "date": "2026-06-20"},
            {"home": "Ecuador", "away": "Curaçao", "date": "2026-06-20"},
            {"home": "Ecuador", "away": "Germany", "date": "2026-06-25"},
            {"home": "Curaçao", "away": "Côte d'Ivoire", "date": "2026-06-25"},
        ],
    },
    {
        "id": "F",
        "teams": ["Netherlands", "Japan", "Sweden", "Tunisia"],
        "matches": [
            {"home": "Netherlands", "away": "Japan", "date": "2026-06-14"},
            {"home": "Sweden", "away": "Tunisia", "date": "2026-06-14"},
            {"home": "Netherlands", "away": "Sweden", "date": "2026-06-20"},
            {"home": "Tunisia", "away": "Japan", "date": "2026-06-20"},
            {"home": "Tunisia", "away": "Netherlands", "date": "2026-06-25"},
            {"home": "Japan", "away": "Sweden", "date": "2026-06-25"},
        ],
    },
    {
        "id": "G",
        "teams": ["Belgium", "Egypt", "IR Iran", "New Zealand"],
        "matches": [
            {"home": "Belgium", "away": "Egypt", "date": "2026-06-15"},
            {"home": "IR Iran", "away": "New Zealand", "date": "2026-06-15"},
            {"home": "Belgium", "away": "IR Iran", "date": "2026-06-21"},
            {"home": "New Zealand", "away": "Egypt", "date": "2026-06-21"},
            {"home": "New Zealand", "away": "Belgium", "date": "2026-06-26"},
            {"home": "Egypt", "away": "IR Iran", "date": "2026-06-26"},
        ],
    },
    {
        "id": "H",
        "teams": ["Spain", "Saudi Arabia", "Uruguay", "Cape Verde Islands"],
        "matches": [
            {"home": "Spain", "away": "Cape Verde Islands", "date": "2026-06-15"},
            {"home": "Saudi Arabia", "away": "Uruguay", "date": "2026-06-15"},
            {"home": "Spain", "away": "Saudi Arabia", "date": "2026-06-21"},
            {"home": "Uruguay", "away": "Cape Verde Islands", "date": "2026-06-21"},
            {"home": "Uruguay", "away": "Spain", "date": "2026-06-26"},
            {"home": "Cape Verde Islands", "away": "Saudi Arabia", "date": "2026-06-26"},
        ],
    },
    {
        "id": "I",
        "teams": ["France", "Senegal", "Norway", "Iraq"],
        "matches": [
            {"home": "France", "away": "Senegal", "date": "2026-06-16"},
            {"home": "Iraq", "away": "Norway", "date": "2026-06-16"},
            {"home": "France", "away": "Iraq", "date": "2026-06-22"},
            {"home": "Norway", "away": "Senegal", "date": "2026-06-22"},
            {"home": "Norway", "away": "France", "date": "2026-06-26"},
            {"home": "Senegal", "away": "Iraq", "date": "2026-06-26"},
        ],
    },
    {
        "id": "J",
        "teams": ["Argentina", "Algeria", "Austria", "Jordan"],
        "matches": [
            {"home": "Argentina", "away": "Algeria", "date": "2026-06-16"},
            {"home": "Austria", "away": "Jordan", "date": "2026-06-16"},
            {"home": "Argentina", "away": "Austria", "date": "2026-06-22"},
            {"home": "Jordan", "away": "Algeria", "date": "2026-06-22"},
            {"home": "Jordan", "away": "Argentina", "date": "2026-06-27"},
            {"home": "Algeria", "away": "Austria", "date": "2026-06-27"},
        ],
    },
    {
        "id": "K",
        "teams": ["Portugal", "Uzbekistan", "Colombia", "DR Congo"],
        "matches": [
            {"home": "Portugal", "away": "DR Congo", "date": "2026-06-17"},
            {"home": "Uzbekistan", "away": "Colombia", "date": "2026-06-17"},
            {"home": "Portugal", "away": "Uzbekistan", "date": "2026-06-23"},
            {"home": "Colombia", "away": "DR Congo", "date": "2026-06-23"},
            {"home": "Colombia", "away": "Portugal", "date": "2026-06-27"},
            {"home": "DR Congo", "away": "Uzbekistan", "date": "2026-06-27"},
        ],
    },
    {
        "id": "L",
        "teams": ["England", "Croatia", "Ghana", "Panama"],
        "matches": [
            {"home": "England", "away": "Croatia", "date": "2026-06-17"},
            {"home": "Ghana", "away": "Panama", "date": "2026-06-17"},
            {"home": "England", "away": "Ghana", "date": "2026-06-23"},
            {"home": "Panama", "away": "Croatia", "date": "2026-06-23"},
            {"home": "Panama", "away": "England", "date": "2026-06-27"},
            {"home": "Croatia", "away": "Ghana", "date": "2026-06-27"},
        ],
    },
]

# R32 bracket — source: Wikipedia "2026 FIFA World Cup knockout stage"
# slot_type: "W" = group winner, "RU" = runner-up, "3rd" = best 3rd-place
# eligible_groups: for "3rd" slots, the set of groups whose 3rd-place team can fill this slot
WC2026_R32: list[dict] = [
    {"match": 73, "slot1_type": "RU", "slot1_group": "A", "slot2_type": "RU", "slot2_group": "B"},
    {"match": 74, "slot1_type": "W",  "slot1_group": "E", "slot2_type": "3rd", "eligible_groups": {"A","B","C","D","F"}},
    {"match": 75, "slot1_type": "W",  "slot1_group": "F", "slot2_type": "RU", "slot2_group": "C"},
    {"match": 76, "slot1_type": "W",  "slot1_group": "C", "slot2_type": "RU", "slot2_group": "F"},
    {"match": 77, "slot1_type": "W",  "slot1_group": "I", "slot2_type": "3rd", "eligible_groups": {"C","D","F","G","H"}},
    {"match": 78, "slot1_type": "RU", "slot1_group": "E", "slot2_type": "RU", "slot2_group": "I"},
    {"match": 79, "slot1_type": "W",  "slot1_group": "A", "slot2_type": "3rd", "eligible_groups": {"C","E","F","H","I"}},
    {"match": 80, "slot1_type": "W",  "slot1_group": "L", "slot2_type": "3rd", "eligible_groups": {"E","H","I","J","K"}},
    {"match": 81, "slot1_type": "W",  "slot1_group": "D", "slot2_type": "3rd", "eligible_groups": {"B","E","F","I","J"}},
    {"match": 82, "slot1_type": "W",  "slot1_group": "G", "slot2_type": "3rd", "eligible_groups": {"A","E","H","I","J"}},
    {"match": 83, "slot1_type": "RU", "slot1_group": "K", "slot2_type": "RU", "slot2_group": "L"},
    {"match": 84, "slot1_type": "W",  "slot1_group": "H", "slot2_type": "RU", "slot2_group": "J"},
    {"match": 85, "slot1_type": "W",  "slot1_group": "B", "slot2_type": "3rd", "eligible_groups": {"E","F","G","I","J"}},
    {"match": 86, "slot1_type": "W",  "slot1_group": "J", "slot2_type": "RU", "slot2_group": "H"},
    {"match": 87, "slot1_type": "W",  "slot1_group": "K", "slot2_type": "3rd", "eligible_groups": {"D","E","I","J","L"}},
    {"match": 88, "slot1_type": "RU", "slot1_group": "D", "slot2_type": "RU", "slot2_group": "G"},
]
```

- [ ] **Step 5: Run bracket tests**

```
cd fifa-2026-predictor
pytest tests/test_simulation.py -k "bracket" -v
```
Expected: 5 PASSED

- [ ] **Step 6: Commit**

```bash
git add fifa-2026-predictor/src/simulation/ fifa-2026-predictor/tests/test_simulation.py
git commit -m "feat: add WC2026 bracket data for simulation (issue #22)"
```

---

## Task 4: Simulation core logic

**Files:**
- Create: `fifa-2026-predictor/src/simulation/tournament.py`
- Modify: `fifa-2026-predictor/tests/test_simulation.py`

- [ ] **Step 1: Write failing tests for simulation logic**

Append to `fifa-2026-predictor/tests/test_simulation.py`:

```python
import numpy as np


def _make_stub_model():
    """Stub model that always returns 60% home / 20% draw / 20% away."""
    from unittest.mock import MagicMock
    model = MagicMock()
    # predict_proba returns (n, 3) ordered [A=0, D=1, H=2]
    model.predict_proba.return_value = np.array([[0.20, 0.20, 0.60]])
    clf = MagicMock()
    clf.classes_ = np.array([0, 1, 2])
    model.named_steps = {"classifier": clf}
    return model


def _make_stub_tracker():
    """Stub TeamStateTracker that returns fixed Elo and form values."""
    from unittest.mock import MagicMock
    import pandas as pd
    tracker = MagicMock()
    # build_match_row calls these tracker methods
    tracker.elo.return_value = 1500.0
    tracker.form.return_value = 1.5
    tracker.form_window.return_value = 1.5
    tracker.goals_for.return_value = 1.3
    tracker.goals_against.return_value = 1.1
    tracker.rest_days.return_value = 7
    tracker.attack_rating.return_value = 0.0
    tracker.defense_rating.return_value = 0.0
    tracker.adj_form.return_value = 1.5
    tracker.adj_attack.return_value = 0.0
    tracker.adj_defense.return_value = 0.0
    tracker.win_streak.return_value = 0
    tracker.loss_streak.return_value = 0
    tracker.unbeaten_streak.return_value = 0
    tracker.draw_rate.return_value = 0.25
    tracker.h2h_record.return_value = {"wins": 0, "draws": 0, "losses": 0}
    return tracker


def test_simulate_once_returns_all_48_teams():
    from src.simulation.tournament import simulate_once
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    all_teams = {t for g in WC2026_GROUPS for t in g["teams"]}
    rng = np.random.default_rng(42)
    result = simulate_once(_make_stub_tracker(), _make_stub_model(), {}, rng)
    assert set(result.keys()) == all_teams


def test_simulate_once_returns_valid_stages():
    from src.simulation.tournament import simulate_once
    valid_stages = {"group_exit", "round_of_32", "quarter_final", "semi_final", "final", "champion"}
    rng = np.random.default_rng(42)
    result = simulate_once(_make_stub_tracker(), _make_stub_model(), {}, rng)
    for team, stage in result.items():
        assert stage in valid_stages, f"{team} has invalid stage: {stage}"


def test_simulate_once_exactly_one_champion():
    from src.simulation.tournament import simulate_once
    rng = np.random.default_rng(42)
    result = simulate_once(_make_stub_tracker(), _make_stub_model(), {}, rng)
    champions = [t for t, s in result.items() if s == "champion"]
    assert len(champions) == 1


def test_run_simulation_probabilities_sum_to_one_per_team():
    from src.simulation.tournament import run_simulation
    results = run_simulation(_make_stub_tracker(), _make_stub_model(), {}, n=50)
    for team_result in results["teams"]:
        total = (
            team_result["group_exit"] + team_result["round_of_32"] +
            team_result["quarter_final"] + team_result["semi_final"] +
            team_result["final"] + team_result["champion"]
        )
        assert abs(total - 1.0) < 0.01, f"{team_result['team']} probs sum to {total}"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd fifa-2026-predictor
pytest tests/test_simulation.py -k "simulate" -v
```
Expected: ImportError — `simulate_once` not defined yet.

- [ ] **Step 3: Create `tournament.py`**

```python
# fifa-2026-predictor/src/simulation/tournament.py
"""Monte Carlo simulation of the WC2026 tournament."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from src.data.team_identity import get_confederation, get_fifa_rank
from src.features.match_row_builder import build_match_row
from src.features.state_tracker import TeamStateTracker
from src.simulation.wc2026_bracket import WC2026_GROUPS, WC2026_R32

_TOURNAMENT_DATE = pd.Timestamp("2026-06-11")
_COMPETITION = "FIFA World Cup"


def build_tournament_states(history_df: pd.DataFrame, cfg: dict) -> TeamStateTracker:
    """Replay all match history before the tournament start; return the tracker snapshot."""
    from src.data.schema import ensure_match_schema
    history = ensure_match_schema(history_df)
    history = history[history["date"] < _TOURNAMENT_DATE].sort_values("date")
    tracker = TeamStateTracker(cfg)
    tracker.replay_history(history)
    return tracker


def predict_match_proba(
    home: str, away: str, tracker: TeamStateTracker, model: Any, cfg: dict,
    match_date: pd.Timestamp = _TOURNAMENT_DATE,
    stage: str = "Group Stage",
) -> dict[str, float]:
    """Return {home_win, draw, away_win} using the pre-built tracker snapshot."""
    from src.models.common import TARGET_MAP
    record = build_match_row(
        tracker=tracker,
        home_team=home,
        away_team=away,
        match_date=match_date,
        competition=_COMPETITION,
        neutral=True,
        home_confederation=get_confederation(home),
        away_confederation=get_confederation(away),
        home_fifa_rank=get_fifa_rank(home),
        away_fifa_rank=get_fifa_rank(away),
        tournament_stage=stage,
        elo_inactivity_halflife=float(cfg.get("features", {}).get("elo_inactivity_halflife", 0.0)),
    )
    feature_row = pd.DataFrame([record])
    probs_raw = model.predict_proba(feature_row)[0]
    clf = model.named_steps["classifier"]
    prob_by_class = {int(c): float(p) for c, p in zip(clf.classes_, probs_raw)}
    return {
        "home_win": prob_by_class.get(TARGET_MAP["H"], 0.0),
        "draw":     prob_by_class.get(TARGET_MAP["D"], 0.0),
        "away_win": prob_by_class.get(TARGET_MAP["A"], 0.0),
    }


def _sample_goals(outcome: str, rng: np.random.Generator) -> tuple[int, int]:
    """Sample a plausible scoreline consistent with the given outcome."""
    if outcome == "H":
        hg = 1 + int(rng.poisson(0.8))
        ag = int(rng.poisson(0.5))
        if hg <= ag:
            ag = max(0, hg - 1)
    elif outcome == "A":
        hg = int(rng.poisson(0.5))
        ag = 1 + int(rng.poisson(0.8))
        if ag <= hg:
            hg = max(0, ag - 1)
    else:
        g = int(rng.poisson(0.9))
        hg, ag = g, g
    return hg, ag


def _compute_group_standings(
    group_teams: list[str],
    records: dict[str, dict],
) -> list[str]:
    """Return teams sorted by pts → GD → GF (descending)."""
    return sorted(
        group_teams,
        key=lambda t: (records[t]["pts"], records[t]["gd"], records[t]["gf"]),
        reverse=True,
    )


def _assign_third_place_teams(
    best_third: list[tuple[str, str]],  # [(team, group_id), ...]
) -> dict[int, str]:
    """Assign 8 best 3rd-place teams to R32 slots using eligibility constraints.

    Uses a greedy most-constrained-first approach.
    Returns {match_number: team}.
    """
    third_slots = [(m["match"], m["eligible_groups"]) for m in WC2026_R32 if m["slot2_type"] == "3rd"]

    # Score each team by how many slots it qualifies for
    scored = []
    for team, group in best_third:
        eligible_idxs = [i for i, (_, groups) in enumerate(third_slots) if group in groups]
        scored.append((len(eligible_idxs), team, group))
    scored.sort()  # most constrained first

    assigned: dict[int, str] = {}  # match_number -> team
    used_idxs: set[int] = set()

    for _, team, group in scored:
        for i, (match_num, eligible_groups) in enumerate(third_slots):
            if i not in used_idxs and group in eligible_groups:
                assigned[match_num] = team
                used_idxs.add(i)
                break
        else:
            # Fallback: assign to any remaining open slot
            for i, (match_num, _) in enumerate(third_slots):
                if i not in used_idxs:
                    assigned[match_num] = team
                    used_idxs.add(i)
                    break

    return assigned


def _simulate_knockout_round(
    matchups: list[tuple[str, str]],
    tracker: TeamStateTracker,
    model: Any,
    cfg: dict,
    stage: str,
    rng: np.random.Generator,
) -> tuple[list[str], dict[str, str]]:
    """Simulate one knockout round. Returns (winners, {eliminated_team: stage})."""
    winners = []
    eliminated = {}
    for home, away in matchups:
        probs = predict_match_proba(home, away, tracker, model, cfg, stage=stage)
        # Knockout: no draws — redistribute draw probability equally
        p_h = probs["home_win"] + probs["draw"] / 2
        p_a = probs["away_win"] + probs["draw"] / 2
        total = p_h + p_a
        winner = home if rng.random() < p_h / total else away
        loser = away if winner == home else home
        winners.append(winner)
        eliminated[loser] = stage
    return winners, eliminated


def simulate_once(
    tracker: TeamStateTracker,
    model: Any,
    cfg: dict,
    rng: np.random.Generator,
) -> dict[str, str]:
    """Run one full WC2026 simulation. Returns {team: stage_reached} for all 48 teams."""
    results: dict[str, str] = {}
    records: dict[str, dict] = {}

    # ── Group stage ──────────────────────────────────────────────────────
    for group in WC2026_GROUPS:
        for team in group["teams"]:
            records[team] = {"pts": 0, "gd": 0, "gf": 0}
        for match in group["matches"]:
            h, a = match["home"], match["away"]
            probs = predict_match_proba(h, a, tracker, model, cfg)
            outcome = rng.choice(
                ["H", "D", "A"],
                p=[probs["home_win"], probs["draw"], probs["away_win"]],
            )
            hg, ag = _sample_goals(outcome, rng)
            if outcome == "H":
                records[h]["pts"] += 3
            elif outcome == "D":
                records[h]["pts"] += 1
                records[a]["pts"] += 1
            else:
                records[a]["pts"] += 3
            records[h]["gd"] += hg - ag
            records[a]["gd"] += ag - hg
            records[h]["gf"] += hg
            records[a]["gf"] += ag

    # ── Determine standings ───────────────────────────────────────────────
    group_finishers: dict[str, list[str]] = {}
    for group in WC2026_GROUPS:
        group_finishers[group["id"]] = _compute_group_standings(group["teams"], records)

    winners = {gid: teams[0] for gid, teams in group_finishers.items()}
    runners_up = {gid: teams[1] for gid, teams in group_finishers.items()}

    # 4th place teams are eliminated
    for gid, teams in group_finishers.items():
        results[teams[3]] = "group_exit"

    # ── Best 8 third-place teams ──────────────────────────────────────────
    third_place: list[tuple[str, str]] = [
        (teams[2], gid) for gid, teams in group_finishers.items()
    ]
    third_sorted = sorted(
        third_place,
        key=lambda x: (records[x[0]]["pts"], records[x[0]]["gd"], records[x[0]]["gf"]),
        reverse=True,
    )
    best_third = third_sorted[:8]
    for team, _ in third_sorted[8:]:
        results[team] = "group_exit"

    # ── Assign 3rd-place teams to R32 slots ──────────────────────────────
    third_assignments = _assign_third_place_teams(best_third)

    # ── Build R32 matchups ────────────────────────────────────────────────
    r32_matchups: list[tuple[str, str]] = []
    for slot in WC2026_R32:
        team1 = winners[slot["slot1_group"]] if slot["slot1_type"] == "W" else runners_up[slot["slot1_group"]]
        if slot["slot2_type"] == "RU":
            team2 = runners_up[slot["slot2_group"]]
        else:
            team2 = third_assignments.get(slot["match"], best_third[0][0])
        r32_matchups.append((team1, team2))

    # ── Knockout rounds ───────────────────────────────────────────────────
    round_names = ["round_of_32", "quarter_final", "semi_final", "final"]
    current = r32_matchups
    for round_name in round_names[:-1]:
        survivors, elim = _simulate_knockout_round(current, tracker, model, cfg, round_name, rng)
        results.update(elim)
        current = [(survivors[i], survivors[i + 1]) for i in range(0, len(survivors), 2)]

    # Final
    assert len(current) == 1
    (finalist1, finalist2) = current[0]
    probs = predict_match_proba(finalist1, finalist2, tracker, model, cfg, stage="Final")
    p_h = probs["home_win"] + probs["draw"] / 2
    p_a = probs["away_win"] + probs["draw"] / 2
    total = p_h + p_a
    champion = finalist1 if rng.random() < p_h / total else finalist2
    runner_up = finalist2 if champion == finalist1 else finalist1
    results[champion] = "champion"
    results[runner_up] = "final"

    return results


def run_simulation(
    tracker: TeamStateTracker,
    model: Any,
    cfg: dict,
    n: int = 1000,
) -> dict:
    """Run n simulations. Returns dict ready for SimulationResponse."""
    from src.simulation.wc2026_bracket import WC2026_GROUPS

    all_teams = {t: g["id"] for g in WC2026_GROUPS for t in g["teams"]}
    stage_keys = ["group_exit", "round_of_32", "quarter_final", "semi_final", "final", "champion"]
    counts: dict[str, dict[str, int]] = {t: {s: 0 for s in stage_keys} for t in all_teams}

    rng = np.random.default_rng()
    for _ in range(n):
        sim_result = simulate_once(tracker, model, cfg, rng)
        for team, stage in sim_result.items():
            counts[team][stage] += 1

    teams_out = []
    for team, group_id in all_teams.items():
        teams_out.append({
            "team": team,
            "group": group_id,
            **{s: round(counts[team][s] / n, 4) for s in stage_keys},
        })

    return {
        "n_simulations": n,
        "teams": teams_out,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
```

- [ ] **Step 4: Run simulation tests**

```
cd fifa-2026-predictor
pytest tests/test_simulation.py -k "simulate" -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add fifa-2026-predictor/src/simulation/tournament.py fifa-2026-predictor/tests/test_simulation.py
git commit -m "feat: add Monte Carlo tournament simulation logic (issue #22)"
```

---

## Task 5: Simulation API endpoint

**Files:**
- Modify: `fifa-2026-predictor/src/api/schemas.py`
- Modify: `fifa-2026-predictor/src/api/services.py`
- Modify: `fifa-2026-predictor/src/api/routes.py`

- [ ] **Step 1: Add simulation schemas**

In `fifa-2026-predictor/src/api/schemas.py`, add at the end:

```python
# ---------------------------------------------------------------------------
# /simulate
# ---------------------------------------------------------------------------

class TeamSimResult(BaseModel):
    team: str
    group: str
    group_exit: float
    round_of_32: float
    quarter_final: float
    semi_final: float
    final: float
    champion: float


class SimulationResponse(BaseModel):
    n_simulations: int
    teams: list[TeamSimResult]
    generated_at: str
```

- [ ] **Step 2: Add `simulate()` to services.py with in-memory cache**

Add these lines near the top of `services.py` with the other module-level singletons (after `_tournament_model_loaded`):

```python
_simulation_cache: Optional[dict] = None
```

Add this function after `_get_tournament_model()`:

```python
def simulate(n: int = 1000) -> dict:
    """Run tournament simulation (cached for server lifetime)."""
    global _simulation_cache
    if _simulation_cache is not None:
        return _simulation_cache

    model = _get_model()
    if model is None:
        raise RuntimeError("No trained model artifact found.")
    history_df = _get_history()
    if history_df is None:
        raise RuntimeError("No match history file found.")
    cfg = _get_cfg()

    from src.simulation.tournament import build_tournament_states, run_simulation
    tracker = build_tournament_states(history_df, cfg)
    _simulation_cache = run_simulation(tracker, model, cfg, n=n)
    return _simulation_cache
```

- [ ] **Step 3: Add `/simulate` route**

In `fifa-2026-predictor/src/api/routes.py`, add after the `/predict` route:

```python
# ---------------------------------------------------------------------------
# /simulate
# ---------------------------------------------------------------------------

@router.get("/simulate", response_model=schemas.SimulationResponse, tags=["simulation"])
def simulate_tournament() -> schemas.SimulationResponse:
    """Run 1000 Monte Carlo WC2026 simulations (cached after first call).

    Returns per-team probabilities for each stage: group exit, R32, QF, SF,
    Final, and Champion.
    """
    try:
        result = services.simulate(n=1000)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        log.error("Simulation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}")

    return schemas.SimulationResponse(
        n_simulations=result["n_simulations"],
        teams=[schemas.TeamSimResult(**t) for t in result["teams"]],
        generated_at=result["generated_at"],
    )
```

- [ ] **Step 4: Commit**

```bash
git add fifa-2026-predictor/src/api/schemas.py fifa-2026-predictor/src/api/services.py fifa-2026-predictor/src/api/routes.py
git commit -m "feat: add GET /simulate endpoint for tournament simulation (issue #22)"
```

---

## Task 6: Frontend — types, API client, hook

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/useSimulation.ts`

- [ ] **Step 1: Add simulation types to `types.ts`**

Append to `frontend/src/lib/types.ts`:

```ts
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
```

- [ ] **Step 2: Add `fetchSimulation` to `api.ts`**

Append to `frontend/src/lib/api.ts`:

```ts
export async function fetchSimulation(): Promise<SimulationResponse> {
  const res = await fetchWithTimeout(`${BASE}/simulate`, {}, 90_000);
  return handleResponse<SimulationResponse>(res);
}
```

Also add `SimulationResponse` to the import from `./types` at the top of `api.ts`:

```ts
import type { TeamInfo, PredictRequest, PredictResponse, ModelInfo, SimulationResponse } from "./types";
```

- [ ] **Step 3: Create `useSimulation.ts`**

```ts
// frontend/src/hooks/useSimulation.ts
"use client";
import { useEffect, useState } from "react";
import { fetchSimulation } from "@/lib/api";
import type { SimulationResponse } from "@/lib/types";

export function useSimulation() {
  const [data, setData] = useState<SimulationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchSimulation()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/hooks/useSimulation.ts
git commit -m "feat: add simulation types, api client, and useSimulation hook"
```

---

## Task 7: Frontend — SimulationPanel + Simulate tab

**Files:**
- Create: `frontend/src/components/SimulationPanel.tsx`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Create `SimulationPanel.tsx`**

```tsx
// frontend/src/components/SimulationPanel.tsx
"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import FlagIcon from "@/components/FlagIcon";
import { useSimulation } from "@/hooks/useSimulation";
import type { TeamSimResult } from "@/lib/types";

type SortKey = keyof Omit<TeamSimResult, "team" | "group">;

function ProbPill({ value }: { value: number }) {
  const pct = value * 100;
  const opacity = Math.max(0.08, value);
  return (
    <span
      className="inline-block px-2 py-0.5 rounded text-xs font-semibold text-white min-w-[48px] text-center"
      style={{ backgroundColor: `rgba(34,197,94,${opacity})` }}
    >
      {pct < 0.5 ? "<1%" : `${pct.toFixed(1)}%`}
    </span>
  );
}

const COLS: { key: SortKey; label: string }[] = [
  { key: "round_of_32",   label: "R32" },
  { key: "quarter_final", label: "QF" },
  { key: "semi_final",    label: "SF" },
  { key: "final",         label: "Final" },
  { key: "champion",      label: "🏆" },
];

export default function SimulationPanel() {
  const { data, loading, error } = useSimulation();
  const [sortKey, setSortKey] = useState<SortKey>("champion");
  const [sortAsc, setSortAsc] = useState(false);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="w-8 h-8 border-2 border-fifa-blue border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 text-sm">Running 1000 tournament simulations…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
        Simulation failed: {error}. Make sure the backend is running.
      </div>
    );
  }

  if (!data) return null;

  const sorted = [...data.teams].sort((a, b) => {
    const diff = a[sortKey] - b[sortKey];
    return sortAsc ? diff : -diff;
  });

  const podium = [...data.teams]
    .sort((a, b) => b.champion - a.champion)
    .slice(0, 5);

  function handleSort(key: SortKey) {
    if (key === sortKey) setSortAsc((v) => !v);
    else { setSortKey(key); setSortAsc(false); }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Champion podium */}
      <div className="bg-navy-800 rounded-2xl border border-navy-600 p-6">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Most Likely Champions · {data.n_simulations.toLocaleString()} Simulations
        </h2>
        <div className="flex gap-3 flex-wrap">
          {podium.map((t, i) => (
            <motion.div
              key={t.team}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="flex-1 min-w-[120px] bg-navy-700 border border-navy-600 rounded-xl p-3 flex flex-col items-center gap-2"
            >
              <FlagIcon team={t.team} className="w-12 h-9 rounded" />
              <span className="text-xs font-semibold text-white text-center leading-tight">{t.team}</span>
              <span className="text-lg font-black text-green-400">{(t.champion * 100).toFixed(1)}%</span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Full table */}
      <div className="bg-navy-800 rounded-2xl border border-navy-600 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-navy-600">
                <th className="text-left px-4 py-3 text-slate-400 font-semibold uppercase tracking-wider text-xs w-8">#</th>
                <th className="text-left px-4 py-3 text-slate-400 font-semibold uppercase tracking-wider text-xs">Team</th>
                <th className="text-center px-2 py-3 text-slate-400 font-semibold uppercase tracking-wider text-xs">Grp</th>
                {COLS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`text-center px-3 py-3 font-semibold uppercase tracking-wider text-xs cursor-pointer select-none transition-colors hover:text-white ${
                      sortKey === col.key ? "text-white" : "text-slate-400"
                    }`}
                  >
                    {col.label} {sortKey === col.key ? (sortAsc ? "↑" : "↓") : ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((team, i) => (
                <tr
                  key={team.team}
                  className="border-b border-navy-700/50 hover:bg-navy-700/30 transition-colors"
                >
                  <td className="px-4 py-2.5 text-slate-500 text-xs">{i + 1}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <FlagIcon team={team.team} className="w-7 h-5 rounded" />
                      <span className="text-white font-medium truncate max-w-[130px]">{team.team}</span>
                    </div>
                  </td>
                  <td className="px-2 py-2.5 text-center text-slate-400 font-mono text-xs">{team.group}</td>
                  {COLS.map((col) => (
                    <td key={col.key} className="px-3 py-2.5 text-center">
                      <ProbPill value={team[col.key]} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-4 py-2 border-t border-navy-700/50">
          <p className="text-xs text-slate-600">
            Based on {data.n_simulations.toLocaleString()} Monte Carlo simulations · Generated {new Date(data.generated_at).toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add "Simulate" tab to `page.tsx`**

In `frontend/src/app/page.tsx`, update the `Tab` type at the top of the component:

```ts
type Tab = "bracket" | "predictor" | "simulate";
```

Add the import for `SimulationPanel`:

```tsx
import SimulationPanel from "@/components/SimulationPanel";
```

Add the new tab button in the tab bar (after the "Predict Match" button):

```tsx
<button
  onClick={() => setTab("simulate")}
  className={`px-5 py-3.5 text-sm font-semibold border-b-[3px] transition-colors ${
    tab === "simulate"
      ? "border-fifa-blue text-white"
      : "border-transparent text-slate-500 hover:text-slate-300"
  }`}
>
  Simulate
</button>
```

Add the tab panel in the content area (after the predictor `</>` closing tag):

```tsx
{tab === "simulate" && <SimulationPanel />}
```

- [ ] **Step 3: Verify the frontend builds without errors**

```
cd frontend
npm run build
```
Expected: compiled successfully with no TypeScript errors.

- [ ] **Step 4: Start both servers and verify end-to-end**

Terminal 1:
```
cd fifa-2026-predictor
python -m uvicorn src.api.main:app --reload --port 8000
```

Terminal 2:
```
cd frontend
npm run dev
```

Open `http://localhost:3000`, click "Simulate" tab, confirm:
- Loading spinner appears while simulation runs
- Champion podium shows top 5 teams with % values
- Table shows all 48 teams sortable by QF/SF/Final/Champion columns
- Back on Predict Match tab, run a prediction — confirm ± values appear under probability bars

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SimulationPanel.tsx frontend/src/app/page.tsx
git commit -m "feat: add Simulate tab with champion podium and sortable team table (issue #22)"
```

---

## Self-Review Notes

- **Spec coverage:** CI extraction ✓, CI display ✓, simulation backend ✓, WC2026 bracket ✓, 3rd-place seeding with eligibility ✓, `/simulate` endpoint ✓, frontend tab ✓, champion podium ✓, sortable table ✓, `group_exit` probability ✓
- **Types consistency:** `TeamSimResult`, `SimulationResponse`, `ConfidenceInterval` defined in Task 6 match schemas in Task 5 and types in Task 2. `simulate_once` returns `dict[str, str]` and `run_simulation` returns plain `dict` in Task 4 — consumed correctly in Task 5.
- **Method names:** `_extract_ensemble_ci` defined in Task 1 Step 4, called in Task 1 Step 5. `simulate()` in services defined in Task 5 Step 2, called in route in Task 5 Step 3. `useSimulation` defined in Task 6 Step 3, imported in Task 7 Step 1.
- **No placeholders present.**
