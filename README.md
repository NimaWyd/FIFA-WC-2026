# FIFA World Cup 2026 Predictor

A full-stack machine learning platform that predicts match outcomes, simulates the entire 2026 World Cup bracket via Monte Carlo methods, and visualises team rosters for all 48 competing nations.

<p align="center">
  <img src="assets/hero.png" alt="Hero" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/XGBoost-Ensemble-orange" alt="XGBoost" />
  <img src="https://img.shields.io/badge/tests-533%20passing-brightgreen" alt="Tests" />
</p>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [How It Works](#how-it-works)
  - [Data Pipeline](#data-pipeline)
  - [Feature Engineering](#feature-engineering)
  - [Model Architecture](#model-architecture)
  - [Scoreline Prediction](#scoreline-prediction)
  - [Tournament Simulation](#tournament-simulation)
- [API Reference](#api-reference)
- [Model Performance](#model-performance)
- [Configuration](#configuration)
- [Retraining the Model](#retraining-the-model)
- [Running Tests](#running-tests)

---

## Overview

The FIFA World Cup 2026 Predictor combines 50+ years of international football data with modern machine learning to produce calibrated outcome probabilities for any international match. It goes beyond a simple win/loss predictor — it outputs full scoreline distributions, expected goals (xG), and can simulate the entire 104-match WC2026 tournament 10,000 times in seconds to estimate each team's championship odds.

The system is built around a strict **no-data-leakage** design: all features are computed from information available *before* kickoff, and all train/validation/test splits are strictly chronological.

---

## Features

### Match Predictor
- Select any two national teams and a match date
- Get calibrated win / draw / loss probabilities
- See the top 10 most likely scorelines with their individual probabilities
- View expected goals (xG) for home and away teams
- Inspect which features drove the prediction (Elo rating, recent form, head-to-head record, etc.)

### Tournament Bracket
- Deterministic bracket showing the model's single most-likely path to the trophy
- Covers all stages: Group Stage → Round of 32 → Round of 16 → Quarter-Finals → Semi-Finals → Final
- 3rd-place playoff correctly modelled between the two semi-final losers

### Monte Carlo Simulation
- Simulate the full 48-team, 104-match tournament N times (default 10,000)
- Per-team probability of reaching each stage: group exit, R32, R16, QF, SF, Final, Champion
- Home/away assignment randomised each run to cancel model home-advantage bias on neutral venues

### Group Stage Viewer
- All 12 groups (A–L) with real 2026 draw assignments
- Click any group to see individual match-by-match predictions and projected standings

### Team Rosters
- Browse all 48 World Cup squads
- Player cards with photos (SofaScore CDN → ESPN CDN → initials fallback)
- Confederation filtering and team search

### Live Matches
- Track in-progress matches with live scores alongside model predictions

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend framework** | Next.js 14 (App Router), React 18, TypeScript |
| **Styling** | Tailwind CSS 3.4, Framer Motion 12 |
| **UI components** | Headless UI, Heroicons, flag-icons |
| **3D visuals** | Three.js, @react-three/fiber, @react-three/drei |
| **Backend framework** | FastAPI, Uvicorn |
| **ML models** | XGBoost, scikit-learn (LogReg, MLP, Isotonic Calibration) |
| **Data manipulation** | pandas, NumPy, SciPy |
| **Feature importance** | SHAP |
| **Configuration** | YAML (PyYAML), python-dotenv |
| **Testing (Python)** | pytest (533 tests) |
| **Testing (JS)** | Vitest, @testing-library/react |

---

## Project Structure

```
FIFA-WC-2026/
├── frontend/                        # Next.js app
│   ├── src/
│   │   ├── app/                     # App Router pages
│   │   │   ├── page.tsx             # Landing page
│   │   │   ├── predict/page.tsx     # Match predictor
│   │   │   ├── groups/page.tsx      # Group stage browser
│   │   │   ├── simulate/page.tsx    # Monte Carlo simulator
│   │   │   ├── teams/               # Team index + profiles
│   │   │   ├── live/page.tsx        # Live match tracker
│   │   │   └── about/page.tsx       # Project info
│   │   ├── components/              # Reusable UI components
│   │   ├── hooks/                   # Data-fetching hooks (usePredict, useSimulation, …)
│   │   └── lib/
│   │       └── rosters.json         # Static squad data for all 48 teams
│   └── package.json
│
└── fifa-2026-predictor/             # Python ML backend
    ├── configs/
    │   └── config.yaml              # All tuneable hyperparameters
    ├── data/
    │   ├── raw/
    │   │   └── results.csv          # 50k+ international match results (1872–2026)
    │   └── processed/
    │       ├── matches_clean.csv    # Cleaned & deduplicated match history
    │       ├── features.csv         # Full feature table (60+ columns, 61k rows)
    │       ├── squad_ratings.csv    # Squad average & top-player ratings
    │       └── fifa_rankings.csv    # Historical FIFA rankings
    ├── src/
    │   ├── api/                     # FastAPI application
    │   │   ├── main.py              # App factory, CORS, routers
    │   │   ├── routes.py            # Endpoint handlers
    │   │   └── services.py          # Prediction & simulation services
    │   ├── data/
    │   │   ├── load_matches.py      # Ingest & clean raw CSV
    │   │   ├── load_teams.py        # Build teams reference table
    │   │   ├── team_identity.py     # Canonical names, confederation, FIFA rank, aliases
    │   │   └── schema.py            # Column name / dtype contracts
    │   ├── features/
    │   │   ├── build_features.py    # Orchestrates full feature build
    │   │   ├── state_tracker.py     # TeamStateTracker — chronological Elo + form engine
    │   │   ├── match_row_builder.py # Snapshot tracker state → flat feature dict
    │   │   ├── elo.py               # Elo update formula (competition-weighted)
    │   │   ├── competition_weights.py # K-factor multipliers & tier base rates
    │   │   └── registry.py          # FeatureRegistry — toggleable feature blocks
    │   ├── models/
    │   │   ├── common.py            # build_preprocessor(), IsotonicCalibrationWrapper
    │   │   ├── train_xgb.py         # XGBoost training script
    │   │   ├── train_logreg.py      # Logistic regression training script
    │   │   ├── train_draw_submodel.py  # Binary draw classifier
    │   │   ├── train_ensemble.py    # Blend XGB + LogReg + MLP; optimize weights
    │   │   ├── ensemble_model.py    # EnsembleModel class
    │   │   ├── scoreline_model.py   # Team-dependent Poisson xG model
    │   │   └── artifacts/           # Trained model files (.joblib, .json)
    │   ├── simulation/
    │   │   ├── tournament.py        # Monte Carlo simulation engine
    │   │   └── wc2026_bracket.py    # Static bracket & group definitions
    │   ├── evaluation/
    │   │   ├── evaluate.py          # Single-model accuracy metrics
    │   │   ├── run_phase2.py        # Rolling-origin backtest (5 windows)
    │   │   └── run_accuracy_improvements.py  # Full model comparison report
    │   └── pipeline/
    │       └── run_all.py           # End-to-end training pipeline
    ├── tests/                       # 533 pytest tests
    ├── scripts/                     # Data enrichment & tuning utilities
    └── requirements.txt
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend Setup

```bash
cd fifa-2026-predictor

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Copy environment file (add FOOTBALL_DATA_API_KEY if you have one)
cp .env.example .env

# Start the API server
python -m uvicorn src.api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Visit `http://localhost:8000/docs` for the interactive Swagger UI.

> **Note:** Pre-trained model artifacts are included in `src/models/artifacts/`. You don't need to retrain to run the API.

### Frontend Setup

```bash
cd frontend
npm install

# Create local environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local

npm run dev
```

The app will be available at `http://localhost:3000`.

---

## How It Works

### Data Pipeline

The system is built on ~50,000 cleaned international football results spanning 1872–2026, sourced from public datasets. Only matches from 1993 onwards are used for model training — pre-modern football is structurally different and near-zero time-decay weights on ancient matches destabilise XGBoost training.

```
data/raw/results.csv  (50k+ rows)
        │
        ▼
load_matches.py  ──►  matches_clean.csv
  • Deduplicates on (date, home_team, away_team)
  • Filters pre-dissolution Yugoslavia / Czechoslovakia
  • Normalises team names via team_identity.py
        │
        ▼
build_features.py  ──►  features.csv  (61k rows, 60+ columns)
  • Replays history through TeamStateTracker (chronologically)
  • Snapshots features BEFORE each match (no leakage)
  • Calls build_match_row() to produce flat feature dict
        │
        ▼
train_xgb / train_logreg / train_draw_submodel / train_ensemble
        │
        ▼
src/models/artifacts/ensemble.joblib  (served by API)
```

### Feature Engineering

All features are computed by `TeamStateTracker`, which replays the full match history chronologically and maintains rolling state per team. The same tracker and `build_match_row()` function is used in both training and inference — eliminating train/serve skew.

**Key feature groups:**

| Group | Features |
|-------|---------|
| **Elo ratings** | `home_elo_pre`, `away_elo_pre`, `elo_diff_home_away`, `elo_win_prob` |
| **Recent form** | `home_form_rw5`, `away_form_rw5`, `form_diff_w3`, `form_diff_w10` (recency-weighted) |
| **Attack / Defense** | `home_attack_rw5`, `away_defense_rw5`, `attack_diff_w5`, `defense_diff_w5` |
| **Opponent-adjusted** | `home_adj_form_w5`, `away_adj_attack_w5`, `away_adj_defense_w5` |
| **Head-to-head** | `h2h_home_win_rate`, `h2h_draw_rate`, `h2h_goal_diff` (last 10 matches) |
| **Rest & fatigue** | `home_rest_days_log`, `away_long_break` |
| **Draw propensity** | `home_draw_rate_w5`, `away_draw_rate_w5`, `draw_rate_diff` |
| **Venue / Context** | `neutral`, `competition_weight`, `tier_home_rate`, `tier_draw_rate`, `tier_away_rate` |
| **Squad strength** | `home_squad_avg_rating`, `squad_rating_diff`, `home_top_player_rating` |
| **Penalty history** | `home_penalty_win_rate`, `penalty_win_rate_diff` |

**Elo model details:**
- Base K-factor: **25** (tuned via grid search — minimises log-loss on held-out test set)
- K scales by competition importance: ×2.0 for World Cup finals, ×0.5 for friendlies
- Home advantage: confederation-specific (e.g., UEFA 80 pts, CONMEBOL 110 pts)
- Goal-margin multiplier applied: a 3-0 win moves ratings more than a 1-0 win

**Features intentionally excluded from the model** (emitted but not trained on — near-zero SHAP contribution): consecutive-result streaks, confederation strength difference.

### Model Architecture

The primary served model is an `EnsembleModel` that blends three base classifiers:

```
Input features (60+ columns)
        │
        ├──► XGBoost classifier    (300 trees, depth 3, isotonic calibration)
        ├──► Logistic Regression   (C=1.0, isotonic calibration)
        └──► MLP                   (hidden layers: [256, 128, 64], isotonic calibration)
                │
                ▼
        Per-class SLSQP blending (3 models × 3 outcomes = 9 weights)
        Optimised on validation set to minimise log-loss
                │
                ▼
        Draw post-hoc adjustment
        (dedicated binary LogReg predicts P(Draw);
         blended with ensemble draw probability)
                │
                ▼
        [P(Away win), P(Draw), P(Home win)]
```

**Why an ensemble?** Each model captures different signal: XGBoost handles non-linear interactions between Elo and form; Logistic Regression provides well-calibrated linear baselines; MLP captures subtle higher-order patterns. The SLSQP weight optimisation lets the blender upweight whichever model is best per outcome class.

**Probability calibration:** Raw XGBoost output is recalibrated using a custom `IsotonicCalibrationWrapper` (one isotonic regressor per class, fitted on the validation set). This replaces `sklearn.calibration.CalibratedClassifierCV(cv='prefit')` which was removed in scikit-learn 1.6.

**Training data split (strictly chronological):**
```
1993 ──────────── 60% train ──────────── 20% val ── 20% test ──► 2026
```

No random shuffling. The val set is used for calibration and ensemble weight optimisation only. The test set is touched once for final evaluation.

### Scoreline Prediction

The API returns the top 10 most-likely scorelines alongside their probabilities. This is powered by a **team-dependent Poisson model**:

1. Each team has an `attack_rating` and `defense_rating` tracked by `TeamStateTracker`
2. `TeamDependentScoreModel` converts these into natural Poisson rates (λ_home, λ_away)
3. The lambdas are then **calibrated to match the ensemble's outcome probabilities** — finding (λ_h, λ_a) whose Poisson CDF agrees with P(H/D/A)
4. Lambdas are clamped to **[0.5, 2.5]** to prevent unrealistic scorelines
5. `scipy.stats.poisson.pmf()` generates the full scoreline probability matrix

This ensures xG always points in the same direction as the win probability — the stronger team always shows higher expected goals.

### Tournament Simulation

The Monte Carlo engine in `src/simulation/tournament.py` runs the full 48-team tournament from group stage to the final:

```
1. Precompute all 48×47 match probabilities in a single batched model call
   → cached as {(home, away): {home_win, draw, away_win}}

2. For each of N simulations:
   ├── Group stage: simulate all 48 group matches
   │   ├── Assign points, apply 3rd-place tiebreaker
   │   │   (points → goal difference → goals scored → FIFA rank)
   │   ├── Top 2 from each group advance to R32
   │   └── Best 16 third-placed teams via backtracking CSP
   │
   └── Knockout rounds (R32 → R16 → QF → SF → Final):
       ├── Draws split 50/50 (no penalty shootout modelled yet)
       └── Home/away coin-flipped each run (cancels home-advantage
           artifact on neutral World Cup venues)

3. Aggregate: reach_prob[team][stage] = n_times_reached / N
```

**Outputs per team:**

| Field | Meaning |
|-------|---------|
| `group_exit` | Eliminated in group stage |
| `round_of_32` | Eliminated in R32 |
| `round_of_16` | Eliminated in R16 |
| `quarter_final` | Eliminated in QF |
| `semi_final` | Eliminated in SF |
| `third_place` | Lost SF, won 3rd-place playoff |
| `final` | Lost the final |
| `champion` | Won the tournament |

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs: `http://localhost:8000/docs`

### `POST /predict`

Predict the outcome of an international match.

**Request body:**
```json
{
  "home_team": "Brazil",
  "away_team": "Argentina",
  "match_date": "2026-06-15",
  "neutral": true,
  "competition": "FIFA World Cup",
  "tournament_stage": "group_stage"
}
```

Only `home_team`, `away_team`, and `match_date` are required. Confederation, FIFA rank, and competition defaults are auto-filled from the team registry.

**Response:**
```json
{
  "home_win": 0.38,
  "draw": 0.26,
  "away_win": 0.36,
  "home_goals": 1.42,
  "away_goals": 1.38,
  "top_scorelines": [
    {"home": 1, "away": 1, "probability": 0.112},
    {"home": 1, "away": 0, "probability": 0.098}
  ],
  "explanation": {
    "elo_win_prob": 0.51,
    "home_form_rw5": 2.1,
    "away_form_rw5": 2.3
  },
  "home_team_meta": {"confederation": "CONMEBOL", "fifa_rank": 3},
  "away_team_meta": {"confederation": "CONMEBOL", "fifa_rank": 1}
}
```

### `GET /teams`

List all registered national teams. Filter by `?confederation=UEFA`.

### `GET /teams/{name}`

Get metadata for a specific team. Accepts official names and common aliases (e.g., `USA` → `United States`).

### `GET /simulate?n=1000`

Run a full Monte Carlo tournament simulation. Returns per-team probabilities of reaching each knockout stage plus the modal bracket path.

### `GET /model-info`

Returns model metadata: model type, feature set, and accuracy on test set.

### `GET /health`

Returns `{"status": "ok"}`.

---

## Model Performance

Evaluated on the chronological test set (last 20% of 1993+ matches, ~5,900 matches from 2019 onward):

| Model | Test Accuracy | Notes |
|-------|--------------|-------|
| Most-frequent baseline | 44.6% | Always predicts home win |
| Elo-only | 58.8% | Elo expected score as a standalone predictor |
| Logistic Regression | 54.9% | Linear model with calibration |
| MLP | 57.96% | Neural net |
| **XGBoost** | **59.87%** | Best single model |
| **Ensemble** | **60.0%** | XGBoost + LogReg + MLP + draw submodel |

**Rolling-origin backtest** (5 windows, each retrains from scratch on expanding data):

- XGBoost mean accuracy: **58.34% ± 1.50%**

**Feature importance (SHAP):**
- `elo_win_prob` is the single most important feature, contributing ~8× more than the second-best
- `home_defense_rw5` and `away_adj_defense_w5` are the next meaningful signals
- Streak features, `rank_diff`, and `is_same_confederation` are near-zero contributors (excluded from training)

> Predicting football is inherently uncertain. Even the best published models rarely exceed 60% accuracy on 3-class match outcome prediction.

---

## Configuration

All model hyperparameters live in `fifa-2026-predictor/configs/config.yaml`:

```yaml
features:
  elo_k_factor: 25.0              # Elo update speed (tuned via grid search)
  elo_home_advantage: 100.0       # Base home advantage in Elo points
  elo_home_advantage_by_confederation:
    UEFA: 80.0
    CONMEBOL: 110.0
    CONCACAF: 70.0
    CAF: 90.0
    AFC: 80.0
  form_window: 5                  # Rolling form window (matches)
  recency_halflife_days: 180      # Half-life for recency weighting
  h2h_window: 10                  # Head-to-head history window

model:
  min_train_year: 1993            # Exclude pre-modern matches from training
  val_size: 0.20
  test_size: 0.15
  xgb:
    n_estimators: 300
    max_depth: 3
    learning_rate: 0.05
    early_stopping_rounds: 25
```

---

## Retraining the Model

If you update the match data or tune hyperparameters, retrain in this order:

```bash
cd fifa-2026-predictor

# 1. Rebuild cleaned matches + feature table
python -m src.data.load_matches --source local --input-csv data/raw/results.csv --output-csv data/processed/matches_clean.csv
python -m src.features.build_features --input-csv data/processed/matches_clean.csv --output-csv data/processed/features.csv

# 2. Train base models
python -m src.models.train_xgb
python -m src.models.train_logreg
python -m src.models.train_draw_submodel

# 3. Train ensemble (must come after the three above)
python -m src.models.train_ensemble

# 4. Rebuild scoreline model
python -m src.models.scoreline_model --features-csv data/processed/features.csv --output-json src/models/artifacts/scoreline_params.json

# 5. Evaluate
python -m src.evaluation.run_accuracy_improvements
```

**Tune Elo K-factor** (run before retraining if you change the data):
```bash
python scripts/tune_elo_k.py
```

---

## Running Tests

```bash
# Python (from fifa-2026-predictor/)
pytest tests/                            # all 533 tests
pytest tests/test_phase4.py              # single file
pytest tests/test_phase4.py::test_name  # single test

# JavaScript (from frontend/)
npm test
```



run backend : cd fifa-2026-predictor python -m uvicorn src.api.main:app --reload --port 8000 run frontend : npm run dev