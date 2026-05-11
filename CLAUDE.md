
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
- `ensemble.joblib` — **default model served by the API**; `EnsembleModel` (defined in `src/models/ensemble_model.py`) blending XGBoost + LogReg + MLP with per-class weights + draw submodel adjustment. Retrain via `python -m src.models.train_ensemble` (requires xgb, logreg, and draw_submodel artifacts to exist first).
- `draw_submodel.joblib` — binary LogReg classifier for P(Draw); retrain via `python -m src.models.train_draw_submodel`
- `xgb.joblib` / `logreg.joblib` — individual outcome classifiers (H/D/A probabilities)
- `poisson_params.json` — legacy global Poisson params
- `scoreline_params.json` — team-dependent Poisson params (used at inference)

**Leakage rule:** every feature must be knowable before kickoff. Rolling features use only matches with `date < match_date`. Elo is taken pre-match and updated post-match. Train/val/test splits are strictly chronological (no random shuffle).

**Config** (`configs/config.yaml`) controls Elo K-factor, form window, recency half-life, H2H window, XGBoost hyperparameters, and backtest settings. Load via `src/utils.py`.

**Rest-days features (issue #48):** raw linear `rest_days` is kept in `TeamStateTracker` internal state but is NOT emitted as a feature. `match_row_builder.py` emits `home/away_rest_days_log = log(1 + rest_days)` and `home/away_long_break = int(rest_days > 21)` instead. Do not add `home_rest_days` / `away_rest_days` back to the feature dict.

**Probability calibration (issue #44):** `xgb.joblib` contains a `sklearn.pipeline.Pipeline` whose `"classifier"` step is an `IsotonicCalibrationWrapper` (defined in `src/models/common.py`), not a raw `XGBClassifier`. The wrapper holds the fitted XGBoost model plus per-class OvR isotonic calibrators. `sklearn.calibration.CalibratedClassifierCV(cv='prefit')` was removed in sklearn 1.6+ — use `IsotonicCalibrationWrapper` instead. After any retraining, the model artifact must be regenerated via `python -m src.models.train_xgb`.

**Training data filter (`model.min_train_year: 1993`):** `train_xgb.py` filters `features.csv` to 1993+ before splitting. `features.csv` still contains all history (needed for accurate Elo tracker state). Pre-1993 data is excluded from XGBoost training because (a) pre-modern football is fundamentally different and (b) near-zero time-decay weights on ancient matches collapse XGBoost gradients → `best_iteration=0`. Without this filter the model degenerates to always predicting "Home" (0.478 accuracy).

**XGBoost sample weights:** `build_weighted_sample_weights()` now uses only balanced class weights (not `match_weight * class_weight`). Time-decay multiplying class weights caused gradients to collapse when training on pre-2015 data. The recency signal is already captured by Elo/form features.

**Val split size (issue #51):** `configs/config.yaml` `model.val_size` is 0.20 (was 0.15). `train_xgb.py` asserts `train_df["date"].max() <= val_df["date"].min()` after the split.

**Time-decayed Elo (issue #50):** `build_match_row()` accepts `elo_inactivity_halflife: float = 0.0`. When >0, emits `home/away_elo_effective = 1500 + (elo - 1500) * exp(-rest_days / halflife)` and `elo_diff_effective`. Config sets `features.elo_inactivity_halflife: 180`. These features are optional in `common.py` (present_phase8 block) so test fixtures without them still work. Both `build_features.py` and `predict_match.py` pass the config value.

**Scoreline/outcome consistency (issue #69):** `services.py` and `predict_match.py` no longer use raw Poisson lambdas to generate scorelines. After the ensemble predicts P(H/D/A), `TeamDependentScoreModel.calibrate_lambdas_to_outcomes()` finds (λ_h, λ_a) whose Poisson distribution reproduces those exact probabilities (via `scipy.optimize` L-BFGS-B). Scorelines are then generated from the calibrated lambdas. This keeps win probabilities and scorelines always consistent while preserving ensemble accuracy and the draw-submodel correction.

**SHAP feature importance (issue #82):** Run `python -m src.evaluation.feature_importance` to regenerate. Results saved to `data/processed/feature_importance.json`. Key findings from the current model: `elo_win_prob` dominates all other features by ~8× (SHAP 0.196). Defense ratings (`home_defense_rw5`, `away_adj_defense_w5`) are the next meaningful signals. Streak features (`win_streak`, `loss_streak`, `unbeaten_streak`), `rank_diff`, `is_same_confederation`, and `stage_importance` are near-zero contributors. Most competition OHE categories are noise except `Friendly`. When adding new features, run this script after retraining to check whether they land above or below the 0.001 threshold.

**Ensemble model (issues #43, #46):** `EnsembleModel` in `src/models/ensemble_model.py` blends XGBoost + LogReg + MLP with per-class weights optimized on the val set via SLSQP, then applies a post-hoc draw probability adjustment using a dedicated binary draw submodel (`draw_submodel.joblib`). `services.py` loads `ensemble.joblib` first (preference order: ensemble → xgb → logreg). `EnsembleModel` exposes `named_steps["classifier"]` and `classes_` for drop-in compatibility with the existing sklearn Pipeline interface. Full retraining order: `train_xgb` → `train_logreg` → `train_draw_submodel` → `train_ensemble`. The `MLPModel` (from `baselines.py`) is trained fresh inside `train_ensemble.py` and stored in the ensemble artifact — it is not saved as a standalone `.joblib`. When calling `EnsembleModel.predict_proba` at inference time, a dummy `target` column is added internally before passing to `MLPModel` (which calls `to_xy` expecting that column).

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

---

## Simulation (`fifa-2026-predictor/src/simulation/`)

**`tournament.py`** — Monte Carlo WC2026 simulation (`run_simulation`, `simulate_once`).

- `precompute_all_probabilities` batches all 48×47 ordered team-pair feature rows into a single `model.predict_proba` call, caching `{(home, away): {home_win, draw, away_win}}` for O(1) lookups during simulation.
- **Group stage and knockout rounds both randomize home/away per simulation run** (coin-flip on `h, a = a, h`) to cancel the model's learned home-advantage artifact on neutral-ground matches (issues #109, #117). Do not remove this randomization.
- Knockout tiebreaking: draws split 50/50 between the two teams (no penalty shootout modelled yet — issue #87).
- Run via `GET /api/v1/simulate?n=1000` or directly: `python -m src.simulation.tournament`

**`wc2026_bracket.py`** — Static group definitions and R32 bracket slots. Group home/away labels are only used as starting identifiers; the simulation randomizes them each run.
