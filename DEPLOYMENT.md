# Deployment Guide

Self-hosted setup for the FIFA WC 2026 Predictor (Python backend + Next.js frontend).

For local development, see the main [README](README.md).

---

## Prerequisites

| Requirement | Minimum version |
|-------------|-----------------|
| Python      | 3.10            |
| pip         | bundled with Python |
| Node.js     | 18              |
| npm         | bundled with Node.js |

---

## 1. Backend Setup

### 1.1 Install Python dependencies

```bash
cd fifa-2026-predictor
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 1.2 Environment variables

```bash
cp .env.example .env
```

Open `.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `FOOTBALL_DATA_API_KEY` | No | API key for live match data ingestion. Not needed when running from local CSVs. |

### 1.3 Required data files

These three files must exist before starting the backend:

```
fifa-2026-predictor/data/processed/
  matches_clean.csv
  features.csv
  teams.csv
```

If they are missing, generate them from the bundled demo CSV:

```bash
cd fifa-2026-predictor
python -m src.pipeline.run_all \
  --source local \
  --input-csv data/raw/demo_international_matches.csv \
  --model-name xgb
```

### 1.4 Required model artifacts

These files must exist under `fifa-2026-predictor/src/models/artifacts/`:

| File | Purpose |
|------|---------|
| `xgb.joblib` | XGBoost outcome classifier |
| `logreg.joblib` | Logistic regression outcome classifier |
| `draw_submodel.joblib` | Binary draw probability classifier |
| `ensemble.joblib` | **Default model served by the API** |

If any are missing, retrain in this exact order:

```bash
cd fifa-2026-predictor
python -m src.models.train_xgb
python -m src.models.train_logreg
python -m src.models.train_draw_submodel
python -m src.models.train_ensemble
```

---

## 2. Frontend Setup

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Replace `http://localhost:8000` with your backend's public hostname/IP if the backend is running on a different machine.

Build the production bundle:

```bash
npm run build
```

---

## 3. Startup Order

Start the **backend first**. The frontend fetches team data on load and will show an error if the backend is unreachable.

**Terminal 1 — Backend:**

```bash
cd fifa-2026-predictor

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm start      # serves the production build on http://localhost:3000
```

---

## 4. Verifying the Deployment

**Backend health check:**

```bash
curl http://localhost:8000/api/v1/health
```

Expected:
```json
{"status": "ok"}
```

**End-to-end prediction test:**

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"home_team": "Brazil", "away_team": "Argentina", "match_date": "2026-06-15"}'
```

Expected: JSON response containing `probabilities`, `top_scorelines`, and `expected_goals` fields.

**UI check:** Open `http://localhost:3000`, select two teams, pick a date, and click **Predict Match**. Results should appear within a few seconds.

---

## 5. Secrets Management

- Never commit `.env` or `.env.local` — both are already in `.gitignore`
- In production, inject secrets via your platform's environment variable mechanism (not committed files)
- `FOOTBALL_DATA_API_KEY` is only needed for live data ingestion, not for running predictions against existing artifacts
