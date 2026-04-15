param(
    [ValidateSet("local", "football-data", "statsbomb")]
    [string]$Source = "local",
    [ValidateSet("xgb", "logreg")]
    [string]$Model = "xgb",
    [string]$InputCsv = "data/raw/demo_international_matches.csv"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Installing dependencies..."
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "Running end-to-end pipeline..."
.\.venv\Scripts\python.exe -m src.pipeline.run_all --source $Source --model-name $Model --input-csv $InputCsv

Write-Host ""
Write-Host "Done. You can now run a prediction, for example:"
Write-Host ".\.venv\Scripts\python.exe -m src.app.predict_match --model-path src/models/artifacts/$Model.joblib --history-csv data/processed/matches_clean.csv --home-team Argentina --away-team France --match-date 2026-06-15 --competition `"FIFA World Cup`" --neutral --home-confederation CONMEBOL --away-confederation UEFA --home-fifa-rank 2 --away-fifa-rank 3 --tournament-stage Group --with-scorelines"
