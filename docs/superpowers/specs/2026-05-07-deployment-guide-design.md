# Deployment Guide — Design Spec
*Issue #33 | Date: 2026-05-07*

## Goal

Add `DEPLOYMENT.md` at the repo root documenting how to run the full stack (backend + frontend) in a production-like local/self-hosted setup — covering environment variables, required artifacts, startup order, and verification.

## Document Location

`DEPLOYMENT.md` at the repo root (alongside `README.md`). Link to it from `README.md`.

## Sections

### 1. Prerequisites
- Python 3.10+, pip, virtualenv
- Node.js 18+, npm

### 2. Required Model Artifacts
List which `.joblib` files must exist under `fifa-2026-predictor/src/models/artifacts/`:
- `xgb.joblib`
- `logreg.joblib`
- `draw_submodel.joblib`
- `ensemble.joblib`

Include the retraining order if artifacts are missing:
```
train_xgb → train_logreg → train_draw_submodel → train_ensemble
```

### 3. Required Data Files
Files that must exist before the backend starts:
- `data/processed/matches_clean.csv`
- `data/processed/features.csv`
- `data/processed/teams.csv`

Note that `data/raw/demo_international_matches.csv` can seed all three via the pipeline command.

### 4. Environment Variables

**Backend** (`fifa-2026-predictor/.env`, copied from `.env.example`):
- `FOOTBALL_DATA_API_KEY` — optional for live data fetch; not required when running from local CSVs

**Frontend** (`frontend/.env.local`):
- `NEXT_PUBLIC_API_BASE_URL` — set to `http://localhost:8000/api/v1` for local; set to the deployed backend URL in production

### 5. Startup Order
Backend must be running before the frontend makes any API calls.

1. Start backend (uvicorn on port 8000)
2. Start frontend (Next.js on port 3000)

Exact commands provided for each.

### 6. Verifying the Deployment
- `GET /api/v1/health` — should return `{"status": "ok"}`
- Sample `curl` predict call with Brazil vs Argentina to confirm end-to-end

### 7. Secrets Management
- Never commit `.env` or `.env.local`
- Both files are already in `.gitignore`
- In production, inject secrets via platform environment variables (not files)

## Out of Scope
- Docker / containerisation
- Cloud platform specifics (Railway, Render, etc.)
- CI/CD pipeline setup
