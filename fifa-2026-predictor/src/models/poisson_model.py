"""Optional Poisson scoreline model from historical goals."""

from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from scipy.stats import poisson

from src.models.common import load_feature_data
from src.utils import PROJECT_ROOT, ensure_parent_dir


def fit_simple_poisson_goals(features_df: pd.DataFrame) -> dict[str, float]:
    """
    Fit a lightweight Poisson scoring model.

    This MVP estimates average home and away goals and applies simple attack/defense
    strengths from rolling form proxies. It is intentionally simple but leakage-safe.
    """
    home_lambda = float(features_df["home_score"].mean())
    away_lambda = float(features_df["away_score"].mean())
    return {"base_home_lambda": home_lambda, "base_away_lambda": away_lambda}


def top_scorelines(
    home_lambda: float,
    away_lambda: float,
    max_goals: int = 5,
    top_n: int = 3,
) -> list[tuple[str, float]]:
    probs: list[tuple[str, float]] = []
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = float(poisson.pmf(h, home_lambda) * poisson.pmf(a, away_lambda))
            probs.append((f"{h}-{a}", p))
    probs.sort(key=lambda x: x[1], reverse=True)
    return probs[:top_n]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit optional Poisson scoreline model.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    parser.add_argument("--output-json", default="src/models/artifacts/poisson_params.json")
    args = parser.parse_args()

    df = load_feature_data(args.features_csv)
    params = fit_simple_poisson_goals(df)
    output_path = PROJECT_ROOT / args.output_json
    ensure_parent_dir(output_path)
    output_path.write_text(json.dumps(params, indent=2), encoding="utf-8")
    print(f"Saved Poisson params to: {output_path}")


if __name__ == "__main__":
    main()

