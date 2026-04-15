"""Run end-to-end MVP pipeline with one command."""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Sequence

from src.utils import PROJECT_ROOT


def run_step(args: Sequence[str]) -> None:
    """Execute one Python module command and fail fast on errors."""
    cmd = [sys.executable, "-m", *args]
    print(f"\n>>> Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full FIFA 2026 predictor MVP pipeline.")
    parser.add_argument("--source", choices=["local", "football-data", "statsbomb"], default="local")
    parser.add_argument("--input-csv", default="data/raw/demo_international_matches.csv")
    parser.add_argument("--output-matches-csv", default="data/processed/matches_clean.csv")
    parser.add_argument("--output-features-csv", default="data/processed/features.csv")
    parser.add_argument("--model-name", choices=["xgb", "logreg"], default="xgb")
    parser.add_argument("--skip-poisson", action="store_true")
    parser.add_argument("--skip-evaluation", action="store_true")
    parser.add_argument("--date-from", default="2022-01-01")
    parser.add_argument("--date-to", default="2026-12-31")
    parser.add_argument("--competition-id", default="43")
    parser.add_argument("--season-id", default="106")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    load_matches_cmd = [
        "src.data.load_matches",
        "--source",
        args.source,
        "--output-csv",
        args.output_matches_csv,
    ]
    if args.source == "local":
        load_matches_cmd.extend(["--input-csv", args.input_csv])
    elif args.source == "football-data":
        load_matches_cmd.extend(["--date-from", args.date_from, "--date-to", args.date_to])
    else:
        load_matches_cmd.extend(["--competition-id", args.competition_id, "--season-id", args.season_id])

    run_step(load_matches_cmd)
    run_step(
        [
            "src.data.load_teams",
            "--matches-csv",
            args.output_matches_csv,
            "--output-csv",
            "data/processed/teams.csv",
        ]
    )
    run_step(
        [
            "src.features.build_features",
            "--input-csv",
            args.output_matches_csv,
            "--output-csv",
            args.output_features_csv,
        ]
    )

    if args.model_name == "xgb":
        run_step(["src.models.train_xgb", "--features-csv", args.output_features_csv, "--model-name", "xgb"])
        model_path = "src/models/artifacts/xgb.joblib"
    else:
        run_step(
            [
                "src.models.train_logreg",
                "--features-csv",
                args.output_features_csv,
                "--model-name",
                "logreg",
            ]
        )
        model_path = "src/models/artifacts/logreg.joblib"

    if not args.skip_poisson:
        run_step(
            [
                "src.models.poisson_model",
                "--features-csv",
                args.output_features_csv,
                "--output-json",
                "src/models/artifacts/poisson_params.json",
            ]
        )

    if not args.skip_evaluation:
        run_step(
            [
                "src.evaluation.evaluate",
                "--features-csv",
                args.output_features_csv,
                "--model-path",
                model_path,
                "--output-json",
                "data/processed/evaluation/metrics.json",
                "--calibration-plot",
                "data/processed/evaluation/calibration.png",
            ]
        )

    print("\nPipeline completed successfully.")
    print(f"Model artifact: {model_path}")
    print("Features table: data/processed/features.csv")


if __name__ == "__main__":
    main()

