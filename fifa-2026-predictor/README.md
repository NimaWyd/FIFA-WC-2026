# fifa-2026-predictor

An API-first, legal, leakage-safe MVP for predicting international football matches one game at a time before kickoff.

Primary output per match:
- Home win probability
- Draw probability
- Away win probability

Optional output:
- Top likely scorelines from a lightweight Poisson model

## Why this MVP is honest and legal

- Uses legal data pipelines only:
  - Local CSV ingestion
  - `football-data.org` API adapter (requires your own key and API plan)
  - StatsBomb Open Data adapter
- No scraping from Sofascore, FotMob, or other restricted sources.
- Features are strictly pre-kickoff (no post-match leakage).
- Train/validation/test are chronological, not random.
- Evaluation emphasizes calibrated probabilities (log loss, Brier, calibration curve), not only accuracy.

## Project structure

```text
fifa-2026-predictor/
├── configs/
│   └── config.yaml
├── data/
│   ├── processed/
│   │   └── .gitkeep
│   └── raw/
│       └── demo_international_matches.csv
├── notebooks/
│   ├── .gitkeep
│   └── 01_data_exploration.ipynb
├── src/
│   ├── __init__.py
│   ├── utils.py
│   ├── app/
│   │   ├── __init__.py
│   │   └── predict_match.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── load_football_data_api.py
│   │   ├── load_matches.py
│   │   ├── load_statsbomb.py
│   │   └── load_teams.py
│   ├── evaluation/
│   │   ├── __init__.py
│   │   └── evaluate.py
│   ├── features/
│   │   ├── __init__.py
│   │   ├── build_features.py
│   │   └── elo.py
│   └── models/
│       ├── __init__.py
│       ├── common.py
│       ├── poisson_model.py
│       ├── train_logreg.py
│       └── train_xgb.py
├── .env.example
├── requirements.txt
└── README.md
```

## Data flow

1. Ingest matches to `data/processed/matches_clean.csv` (`src/data/load_matches.py`)
2. Build team table (optional) to `data/processed/teams.csv` (`src/data/load_teams.py`)
3. Build leakage-safe feature table to `data/processed/features.csv` (`src/features/build_features.py`)
4. Train model(s) to `src/models/artifacts/`
5. Evaluate chronologically to `data/processed/evaluation/`
6. Predict one future match with `src/app/predict_match.py`

## Environment setup

### 1) Create virtual environment and install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Add API key (optional for API ingestion)

```bash
copy .env.example .env
```

Set:
- `FOOTBALL_DATA_API_KEY=...`

If no API key is added, the MVP still runs with local CSV.

## Run the MVP locally (exact commands)

### A) Ingest and clean data

Local CSV (default demo):
```bash
python -m src.data.load_matches --source local --input-csv data/raw/demo_international_matches.csv --output-csv data/processed/matches_clean.csv
```

Football-data.org API:
```bash
python -m src.data.load_matches --source football-data --date-from 2022-01-01 --date-to 2026-12-31 --output-csv data/processed/matches_clean.csv
```

StatsBomb Open Data:
```bash
python -m src.data.load_matches --source statsbomb --competition-id 43 --season-id 106 --output-csv data/processed/matches_clean.csv
```

### B) Build team reference table

```bash
python -m src.data.load_teams --matches-csv data/processed/matches_clean.csv --output-csv data/processed/teams.csv
```

### C) Build feature table

```bash
python -m src.features.build_features --input-csv data/processed/matches_clean.csv --output-csv data/processed/features.csv
```

### D) Train models

Logistic baseline:
```bash
python -m src.models.train_logreg --features-csv data/processed/features.csv --model-name logreg
```

XGBoost model:
```bash
python -m src.models.train_xgb --features-csv data/processed/features.csv --model-name xgb
```

Optional Poisson params:
```bash
python -m src.models.poisson_model --features-csv data/processed/features.csv --output-json src/models/artifacts/poisson_params.json
```

### E) Evaluate (chronological test block)

```bash
python -m src.evaluation.evaluate --features-csv data/processed/features.csv --model-path src/models/artifacts/xgb.joblib --output-json data/processed/evaluation/metrics.json --calibration-plot data/processed/evaluation/calibration.png
```

### F) Predict one match before kickoff

```bash
python -m src.app.predict_match --model-path src/models/artifacts/xgb.joblib --history-csv data/processed/matches_clean.csv --home-team Argentina --away-team France --match-date 2026-06-15 --competition "FIFA World Cup" --neutral --home-confederation CONMEBOL --away-confederation UEFA --home-fifa-rank 2 --away-fifa-rank 3 --tournament-stage Group --with-scorelines
```

## Feature design (leakage-safe)

Each training row is one match with features known before kickoff:
- teams
- date
- competition
- neutral flag
- confederations
- FIFA ranking placeholders
- tournament stage placeholder
- recent form (last 5 matches)
- rolling goals scored/conceded
- rest days
- pre-match Elo ratings and Elo difference
- opponent-relative form/goal-balance deltas

Targets:
- `H` = home win
- `D` = draw
- `A` = away win

## Why chronological evaluation matters

Football is time-dependent. Team strength, managers, and squads evolve.
- Random split lets future patterns leak into training and overstates performance.
- Chronological split simulates real deployment: train on past, predict future.
- This repository uses train (oldest), validation (middle), and test (most recent).

## Leakage guardrails

- No post-match stats in pre-match features.
- Rolling features are computed only from prior matches.
- Elo is taken pre-match, then updated after result.
- Future fixtures are predicted using only history up to that date.

## Extension points for later versions

- injuries/lineups
- betting odds
- player-level metrics
- travel distance and climate
- richer scoreline models and Bayesian calibration

