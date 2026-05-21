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

---

## 6. Deployment Issues — Vercel + Railway

Target: **Vercel (frontend) + Railway (backend)**

Issues below are tracked on GitHub. Fix them in priority order before going live.

---

### 🔴 Critical — app will not work without these

#### Issue: Set production API URL for frontend ([#144](https://github.com/NimaWyd/FIFA-WC-2026/issues/144))
`frontend/.env.local` hardcodes `http://127.0.0.1:8000/api/v1`. The deployed frontend will call localhost, which does not exist on Vercel.

**Fix:** In the Vercel dashboard add an environment variable:
```
NEXT_PUBLIC_API_BASE_URL=https://<your-railway-backend>.up.railway.app/api/v1
```

---

#### Issue: Pin all Python dependency versions ([#145](https://github.com/NimaWyd/FIFA-WC-2026/issues/145))
`requirements.txt` has no version pins. Railway may install newer sklearn/xgboost versions incompatible with the committed `.joblib` artifacts — this silently corrupts predictions or crashes on load.

**Fix:** Capture exact versions locally and commit:
```bash
pip freeze > fifa-2026-predictor/requirements.txt
```
Regenerate model artifacts if versions change.

---

#### Issue: Add production start command for Railway ([#146](https://github.com/NimaWyd/FIFA-WC-2026/issues/146))
No `Procfile` or Railway config exists. `uvicorn --reload` is dev-only; Railway also injects `$PORT` dynamically which the current command ignores.

**Fix:** Create `fifa-2026-predictor/Procfile`:
```
web: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT --workers 2
```

---

### 🟠 High — security problems for a public deployment

#### Issue: Lock CORS to the Vercel domain ([#147](https://github.com/NimaWyd/FIFA-WC-2026/issues/147))
`main.py` sets `allow_origins=["*"]`, allowing any website to call the API.

**Fix:** Replace with the actual Vercel URL and an env var:
```python
import os
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGIN", "http://localhost:3000").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, ...)
```
Set `ALLOWED_ORIGIN=https://<your-app>.vercel.app` in Railway.

---

#### Issue: Protect the `/refresh` endpoint ([#148](https://github.com/NimaWyd/FIFA-WC-2026/issues/148))
`POST /api/v1/refresh` is unauthenticated. Anyone can call it to burn through the `FOOTBALL_DATA_API_KEY` quota and flush all simulation caches.

**Fix:** Check a secret token header in `routes.py`:
```python
import os
from fastapi import Header, HTTPException

@router.post("/refresh")
def refresh_live_data(x_refresh_token: str = Header(...)):
    if x_refresh_token != os.getenv("REFRESH_SECRET"):
        raise HTTPException(status_code=403, detail="Forbidden")
    ...
```
Set `REFRESH_SECRET` in Railway env vars.

---

#### Issue: Disable API docs in production ([#149](https://github.com/NimaWyd/FIFA-WC-2026/issues/149))
`/docs` and `/redoc` are enabled with no auth, exposing the full API surface publicly.

**Fix:** Conditionally disable in `main.py`:
```python
import os
ENV = os.getenv("ENV", "development")
app = FastAPI(
    docs_url="/docs" if ENV != "production" else None,
    redoc_url="/redoc" if ENV != "production" else None,
)
```
Set `ENV=production` in Railway.

---

### 🟡 Medium — performance and reliability

#### Issue: Run simulation off the async event loop ([#150](https://github.com/NimaWyd/FIFA-WC-2026/issues/150))
`GET /simulate` runs 1000 Monte Carlo iterations synchronously in a FastAPI async handler, blocking the event loop for all other requests.

**Fix:** Offload to a thread pool in `routes.py`:
```python
from starlette.concurrency import run_in_threadpool

@router.get("/simulate")
async def simulate_tournament():
    result = await run_in_threadpool(services.simulate, n=1000)
    ...
```

---

#### Issue: Move `load_dotenv()` to startup ([#151](https://github.com/NimaWyd/FIFA-WC-2026/issues/151))
`services._fetch_wc_matches()` calls `load_dotenv()` on every live-match request (a file read on every poll cycle).

**Fix:** Call it once at the top of `main.py` before the app is created:
```python
from dotenv import load_dotenv
load_dotenv()
```
Remove the `load_dotenv()` call from `_fetch_wc_matches`.

---

#### Issue: Validate required artifacts at startup ([#152](https://github.com/NimaWyd/FIFA-WC-2026/issues/152))
If `ensemble.joblib` or `matches_clean.csv` is missing on Railway, the server starts fine but returns 503 on the first real request — hard to debug.

**Fix:** Add a startup event in `main.py`:
```python
@app.on_event("startup")
def validate_artifacts():
    from src.api.services import _get_model, _get_history
    if _get_model() is None:
        raise RuntimeError("No trained model artifact found — aborting startup.")
    if _get_history() is None:
        raise RuntimeError("No match history CSV found — aborting startup.")
```

---

### 🟢 Low — housekeeping

#### Issue: Add `frontend/.env.local` to `.gitignore` ([#153](https://github.com/NimaWyd/FIFA-WC-2026/issues/153))
The root `.gitignore` does not exclude `frontend/.env.local`. If a secret is ever added it could be accidentally committed.

**Fix:** Add to `.gitignore`:
```
frontend/.env.local
```

---

#### Issue: Add rate limiting to `/predict` and `/simulate` ([#154](https://github.com/NimaWyd/FIFA-WC-2026/issues/154))
No rate limiting exists. A single client can spam `/simulate` (CPU-heavy) without restriction.

**Fix:** Add `slowapi` to requirements and apply limits:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@router.get("/simulate")
@limiter.limit("5/minute")
async def simulate_tournament(request: Request): ...

@router.post("/predict")
@limiter.limit("30/minute")
def predict(request: Request, body: schemas.PredictRequest): ...
```

---

### Pre-launch checklist

- [ ] Railway: `requirements.txt` is fully pinned
- [ ] Railway: `Procfile` or start command configured
- [ ] Railway: `FOOTBALL_DATA_API_KEY` env var set
- [ ] Railway: `REFRESH_SECRET` env var set
- [ ] Railway: `ENV=production` env var set
- [ ] Railway: `ALLOWED_ORIGIN` env var set to Vercel URL
- [ ] Vercel: `NEXT_PUBLIC_API_BASE_URL` env var set to Railway backend URL
- [ ] CORS locked to Vercel domain
- [ ] `/refresh` endpoint protected with token
- [ ] API docs disabled in production
- [ ] Simulation endpoint runs off the event loop
- [ ] `load_dotenv()` moved to startup
- [ ] Startup artifact validation added
- [ ] `frontend/.env.local` added to `.gitignore`
- [ ] Rate limiting added to `/predict` and `/simulate`
