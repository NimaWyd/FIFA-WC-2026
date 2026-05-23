# Squad Quality Adjustment via EA FC 25 Ratings

**Date:** 2026-05-23
**Status:** Approved, pending implementation

## Problem

The model ranks teams primarily by FIFA rank and Elo history. For some squads, current player quality is significantly mis-estimated by these signals alone:

- **Egypt (rank 29)** has Mohamed Salah at peak form — a top-5 player in the world — but ranks below **IR Iran (rank 21)**, causing the model to predict Iran 2nd and Egypt 3rd in their WC 2026 group (Belgium, Egypt, IR Iran, New Zealand).
- **Norway** is similarly undervalued: Erling Haaland's presence makes them a credible dark horse the model doesn't reflect.

The root cause is that the `player_aggregate` feature block is disabled (`registry.py:290`) because no player rating data is loaded. The aggregation infrastructure already exists; it just needs data.

## Decision

Add a **post-prediction squad quality adjustment** using EA FC 25 player ratings sourced from the public Kaggle dataset. This is an inference-only change — no model retraining, no train/serve skew.

## Approach

Rather than feeding player features into the ML model (which would require historical ratings for all training rows going back to 1993), a lightweight adjustment is applied *after* the model returns `P(home_win / draw / away_win)`. The adjustment shifts probabilities based on the squad rating differential between the two teams.

This flows automatically into:
- The `/api/v1/predict` endpoint
- The simulation's `precompute_all_probabilities()` (which calls `predict_match()` internally)
- The bracket prediction

## Architecture

### Four new components

```
scripts/build_player_ratings.py                      ← one-time data pipeline script
fifa-2026-predictor/src/data/load_squad_ratings.py   ← rating loader (singleton)
fifa-2026-predictor/src/models/squad_quality_adjuster.py  ← pure adjustment function
fifa-2026-predictor/src/api/services.py              ← 3-line integration point
```

---

### 1. Data pipeline — `scripts/build_player_ratings.py`

**Inputs:**
- `data/raw/fc25_players.csv` — EA FC 25 Kaggle dataset (user downloads; ~20k rows, columns include `short_name`, `long_name`, `overall`, `nationality_name`, `club_name`)
- `frontend/src/lib/rosters.json` — already exists; all 48 WC 2026 squads with player names

**Process:**
1. Load all players from `rosters.json` (approx. 700 players across 48 teams).
2. For each player, fuzzy-match their name against FC 25 `long_name` / `short_name` using `rapidfuzz.process.extractOne` with `scorer=fuzz.token_sort_ratio`.
3. Accept matches with score ≥ 80. Flag anything below as unmatched.
4. For each team, compute:
   - `top15_avg` — mean `overall` of the top 15 rated matched players (proxy for typical starting XI + bench depth)
   - `squad_avg` — mean `overall` of all matched players
   - `matched` — count of successfully matched players
   - `unmatched` — list of player names that fell below the threshold

**Output:** `data/processed/wc2026_squad_ratings.json`

```json
{
  "Egypt": {
    "top15_avg": 80.4,
    "squad_avg": 77.1,
    "matched": 23,
    "unmatched": ["Omar Marmoush"]
  },
  "IR Iran": {
    "top15_avg": 74.2,
    "squad_avg": 72.8,
    "matched": 21,
    "unmatched": []
  }
}
```

The script also prints a summary table so mismatches can be reviewed and corrected manually if needed.

**Dependency:** `rapidfuzz` (add to `requirements.txt`)

---

### 2. Rating loader — `src/data/load_squad_ratings.py`

Loads `wc2026_squad_ratings.json` once at import time. Exposes:

```python
def get_squad_rating(team: str) -> float:
    """Return top15_avg for team, or 75.0 if not found."""

def is_ratings_available() -> bool:
    """False when the JSON file doesn't exist yet."""
```

- Falls back to `75.0` (approximate global average) for any unknown team.
- When the JSON file is absent entirely, `get_squad_rating` returns `75.0` for every team → adjustment is a no-op → fully backward compatible.
- Uses `team_identity.resolve_team()` before lookup so aliases work.

---

### 3. Adjustment function — `src/models/squad_quality_adjuster.py`

Pure, stateless function — no I/O, no side effects.

```python
MAX_SHIFT = 0.06       # maximum probability shift (6 percentage points)
SCALE = 0.3            # controls how steeply quality_diff maps to adjustment

def adjust_probabilities(
    probs: dict,           # {"home_win": float, "draw": float, "away_win": float}
    home_rating: float,    # top15_avg for home team
    away_rating: float,    # top15_avg for away team
) -> dict:
```

**Formula:**

```
quality_diff = (home_rating - away_rating) / 10
delta = tanh(quality_diff * SCALE) * MAX_SHIFT
new_home = clamp(probs["home_win"] + delta, 0.05, 0.90)
new_away = clamp(probs["away_win"] - delta, 0.05, 0.90)
new_draw = 1.0 - new_home - new_away
# renormalize so all three sum to 1.0
```

**Example — Egypt vs Iran:**
- Egypt top15_avg = 80.4, Iran top15_avg = 74.2 → diff = 6.2 → delta ≈ +0.035
- Egypt's win probability increases by ~3.5%, Iran's decreases by ~3.5%
- Draw is recalculated from remainder and renormalized

**Tuneable constants:** `MAX_SHIFT` and `SCALE` are module-level so they can be adjusted without touching logic. A 20-point gap (e.g., France vs San Marino) produces a ~5.7% shift — meaningful but never overriding a large Elo gap.

**Edge cases:**
- Equal ratings → `delta = 0.0`, probabilities unchanged
- `probs` missing a key → returns input unchanged (safe default)
- Result always sums to 1.0

---

### 4. Integration — `src/api/services.py`

In `predict_match()`, immediately after the model returns probabilities, add:

```python
from src.data.load_squad_ratings import get_squad_rating
from src.models.squad_quality_adjuster import adjust_probabilities

home_rating = get_squad_rating(home_team)
away_rating = get_squad_rating(away_team)
result["probabilities"] = adjust_probabilities(result["probabilities"], home_rating, away_rating)
```

No other files change. The simulation picks up the fix automatically.

---

## File change summary

| File | Action |
|------|--------|
| `scripts/build_player_ratings.py` | Create |
| `fifa-2026-predictor/src/data/load_squad_ratings.py` | Create |
| `fifa-2026-predictor/src/models/squad_quality_adjuster.py` | Create |
| `fifa-2026-predictor/src/api/services.py` | Modify (3 lines) |
| `fifa-2026-predictor/requirements.txt` | Add `rapidfuzz` |
| `data/processed/wc2026_squad_ratings.json` | Generated (not committed) |

---

## What the user must do first

1. Download the EA FC 25 dataset from Kaggle: search **"EA FC 25 Players"**, download `male_players.csv`
2. Place it at `data/raw/fc25_players.csv`
3. Run `python scripts/build_player_ratings.py`
4. Review the unmatched players report and fix any important mismatches manually in the JSON

---

## Out of scope

- Retraining the ML model on player features (future work; requires multi-year EA FC historical data)
- Enabling the `player_aggregate` block in the feature registry (separate effort; requires lineup/injury data at training time)
- Injury data integration (no real-time injury feed connected)
- Per-position weighting in the adjustment (squad-level top-15 average is sufficient for now)
