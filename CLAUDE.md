
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Two top-level packages share a single git repo:

- `fifa-2026-predictor/` — Python ML backend (FastAPI + scikit-learn/XGBoost)
- `frontend/` — Next.js 14 app (TypeScript, Tailwind CSS, Framer Motion)

---

## Backend (`fifa-2026-predictor/`)

### Setup

```bash
cd fifa-2026-predictor
python -m venv .venv
.venv/Scripts/activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # set FOOTBALL_DATA_API_KEY if needed
```

### Common commands

| Task | Command |
|------|---------|
| Run API server | `python -m uvicorn src.api.main:app --reload --port 8000` |
| Full pipeline (one shot) | `python -m src.pipeline.run_all --source local --input-csv data/raw/demo_international_matches.csv --model-name xgb` |
| Run all tests | `pytest tests/` |
| Run a single test file | `pytest tests/test_phase4.py` |
| Run a single test | `pytest tests/test_phase4.py::test_name` |
| Phase 2 evaluation | `python -m src.evaluation.run_phase2` |
| Phase 7 accuracy report | `python -m src.evaluation.run_accuracy_improvements` |

### API endpoints (prefix `/api/v1`)

- `POST /predict` — core prediction; only `home_team`, `away_team`, `match_date` are required; confederation/rank auto-filled from team registry
- `GET /teams` — list canonical teams, filter by `?confederation=UEFA`
- `GET /teams/{name}` — single team metadata (accepts aliases)
- `GET /model-info` — model metadata
- `GET /health` — service health

### Architecture

**Data flow (training):**
1. `src/data/load_matches.py` — ingest → `data/processed/matches_clean.csv`
2. `src/data/load_teams.py` — team reference table → `data/processed/teams.csv`
3. `src/features/build_features.py` — feature table → `data/processed/features.csv`
4. `src/models/train_xgb.py` or `train_logreg.py` → `src/models/artifacts/`
5. `src/evaluation/evaluate.py` — chronological backtest

**Data flow (inference):**
`src/api/services.py` → `src/app/predict_match.py` → replays history through `TeamStateTracker` → calls trained model + `TeamDependentScoreModel`

**Key shared modules:**

- `src/features/state_tracker.py` — `TeamStateTracker` is the central state machine used by both training and inference. It accumulates Elo ratings, rolling form, attack/defense ratings, head-to-head records, and draw rates for every team as matches are processed chronologically. Always snapshot features *before* calling `tracker.update()`.

- `src/features/match_row_builder.py` — converts a `TeamStateTracker` snapshot into a flat feature dict for one match. Called identically in training and inference to prevent train/serve skew.

- `src/data/team_identity.py` — canonical team names (FIFA convention), confederation lookup, 2025 FIFA rank, and alias resolution. All pipeline entry points should route team names through `resolve_team()`.

- `src/features/registry.py` — `FeatureRegistry` singleton (`get_registry()`). Feature blocks are named, toggleable units. The `player_aggregate` block is registered but disabled by default until real player data is available.

- `src/data/schema.py` — defines the canonical column names and dtypes for `matches_clean.csv` and `features.csv`.

**Models saved under** `src/models/artifacts/`:
- `xgb.joblib` / `logreg.joblib` — outcome classifier (H/D/A probabilities)
- `poisson_params.json` — legacy global Poisson params
- `scoreline_params.json` — team-dependent Poisson params (used at inference)

**Leakage rule:** every feature must be knowable before kickoff. Rolling features use only matches with `date < match_date`. Elo is taken pre-match and updated post-match. Train/val/test splits are strictly chronological (no random shuffle).

**Config** (`configs/config.yaml`) controls Elo K-factor, form window, recency half-life, H2H window, XGBoost hyperparameters, and backtest settings. Load via `src/utils.py`.

**Rest-days features (issue #48):** raw linear `rest_days` is kept in `TeamStateTracker` internal state but is NOT emitted as a feature. `match_row_builder.py` emits `home/away_rest_days_log = log(1 + rest_days)` and `home/away_long_break = int(rest_days > 21)` instead. Do not add `home_rest_days` / `away_rest_days` back to the feature dict.

**Probability calibration (issue #44):** `xgb.joblib` contains a `sklearn.pipeline.Pipeline` whose `"classifier"` step is an `IsotonicCalibrationWrapper` (defined in `src/models/common.py`), not a raw `XGBClassifier`. The wrapper holds the fitted XGBoost model plus per-class OvR isotonic calibrators. `sklearn.calibration.CalibratedClassifierCV(cv='prefit')` was removed in sklearn 1.6+ — use `IsotonicCalibrationWrapper` instead. After any retraining, the model artifact must be regenerated via `python -m src.models.train_xgb`.

**Val split size (issue #51):** `configs/config.yaml` `model.val_size` is 0.20 (was 0.15). `train_xgb.py` asserts `train_df["date"].max() <= val_df["date"].min()` after the split.

---

## Frontend (`frontend/`)

### Setup & commands

```bash
cd frontend
npm install
npm run dev      # dev server at http://localhost:3000
npm run build
npm run lint
```

The frontend calls the backend at `http://localhost:8000/api/v1` (configured via `NEXT_PUBLIC_API_URL` in `.env.local`).

### Stack

Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion, Headless UI, flag-icons.
