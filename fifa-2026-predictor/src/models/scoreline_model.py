"""Team-dependent Poisson scoreline model.

Replaces the old global-average approach (poisson_model.py) with a model
whose expected goals depend on each team's attack and defense ratings.

Expected goals formula
----------------------
λ_home = base_home × (home_attack / μ_atk) × (away_defense / μ_def) × home_factor
λ_away = base_away × (away_attack / μ_atk) × (home_defense / μ_def)

where:
  base_home / base_away  — calibrated from historical average goals
  μ_atk / μ_def          — global average attack/defense rating across all teams
  home_factor            — calibrated home-advantage multiplier (1.0 on neutral ground)
  attack / defense       — rolling recency-weighted per-team ratings from the tracker

The model reads 'home_attack_w5', 'away_attack_w5', 'home_defense_w5',
'away_defense_w5' and 'neutral' from the feature row — all pre-match columns
built by match_row_builder.build_match_row().
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import poisson

from src.models.common import load_feature_data
from src.utils import PROJECT_ROOT, ensure_parent_dir


@dataclass
class ScoreModelParams:
    base_home_lambda: float = 1.5
    base_away_lambda: float = 1.2
    home_advantage_factor: float = 1.15
    mean_attack: float = 1.0
    mean_defense: float = 1.0


class TeamDependentScoreModel:
    """Team-specific Poisson scoreline model.

    Fitted parameters are saved to / loaded from a JSON file so they can be
    persisted alongside the outcome-prediction model artifact.
    """

    DEFAULT_PARAMS_FILE = "src/models/artifacts/scoreline_params.json"

    def __init__(self) -> None:
        self.params = ScoreModelParams()
        self._fitted = False

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    def fit(self, features_df: pd.DataFrame) -> None:
        """Calibrate model parameters from a historical feature DataFrame.

        The DataFrame must have 'home_score', 'away_score', 'neutral', and
        the Phase 4 attack/defense columns when available.
        """
        home_goals = features_df["home_score"]
        away_goals = features_df["away_score"]

        self.params.base_home_lambda = float(home_goals.mean())
        self.params.base_away_lambda = float(away_goals.mean())

        # Calibrate home-advantage factor from non-neutral matches
        neutral_mask = features_df["neutral"].astype(int).astype(bool)
        home_mask = ~neutral_mask
        if home_mask.sum() >= 20:
            home_avg = float(home_goals[home_mask].mean())
            away_avg = float(away_goals[home_mask].mean())
            # sqrt keeps the multiplier symmetric: home → λ×factor, away → λ/factor
            if away_avg > 0:
                self.params.home_advantage_factor = float(
                    np.clip((home_avg / away_avg) ** 0.5, 1.0, 1.5)
                )

        # Calibrate global mean attack / defense from Phase 4 feature columns
        atk_col = "home_attack_w5" if "home_attack_w5" in features_df.columns else None
        def_col = "home_defense_w5" if "home_defense_w5" in features_df.columns else None

        if atk_col and def_col:
            all_attack = pd.concat(
                [features_df["home_attack_w5"], features_df["away_attack_w5"]]
            )
            all_defense = pd.concat(
                [features_df["home_defense_w5"], features_df["away_defense_w5"]]
            )
            self.params.mean_attack = float(all_attack.mean())
            self.params.mean_defense = float(all_defense.mean())
        else:
            # Fall back to goal averages if Phase 4 columns are absent
            all_goals = pd.concat([home_goals, away_goals])
            self.params.mean_attack = float(all_goals.mean())
            self.params.mean_defense = float(all_goals.mean())

        self._fitted = True

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_lambdas(
        self,
        home_attack: float,
        away_attack: float,
        home_defense: float,
        away_defense: float,
        neutral: bool,
    ) -> tuple[float, float]:
        """Return (lambda_home, lambda_away) as team-specific expected goals.

        Parameters
        ----------
        home_attack:   home team's recent goals-scored rate (attack_rating)
        away_attack:   away team's recent goals-scored rate
        home_defense:  home team's recent goals-conceded rate (lower = better)
        away_defense:  away team's recent goals-conceded rate (lower = better)
        neutral:       True if match is played on neutral ground
        """
        mean_atk = max(self.params.mean_attack, 0.1)
        mean_def = max(self.params.mean_defense, 0.1)
        home_def_safe = max(home_defense, 0.1)
        away_def_safe = max(away_defense, 0.1)
        home_factor = 1.0 if neutral else self.params.home_advantage_factor

        lambda_home = (
            self.params.base_home_lambda
            * (home_attack / mean_atk)
            * (away_def_safe / mean_def)
            * home_factor
        )
        lambda_away = (
            self.params.base_away_lambda
            * (away_attack / mean_atk)
            * (home_def_safe / mean_def)
        )
        lambda_home = float(np.clip(lambda_home, 0.5, 4.0))
        lambda_away = float(np.clip(lambda_away, 0.5, 4.0))
        return lambda_home, lambda_away

    def predict_lambdas_from_row(
        self, row: dict[str, Any] | pd.Series
    ) -> tuple[float, float]:
        """Extract attack/defense from a feature row and return expected goals.

        Falls back to goals_for/against columns if Phase 4 columns are absent,
        so the model degrades gracefully even on old feature tables.
        """
        home_attack = float(
            row.get("home_attack_w5", row.get("home_goals_for_last5", 1.0))
        )
        away_attack = float(
            row.get("away_attack_w5", row.get("away_goals_for_last5", 1.0))
        )
        home_defense = float(
            row.get("home_defense_w5", row.get("home_goals_against_last5", 1.0))
        )
        away_defense = float(
            row.get("away_defense_w5", row.get("away_goals_against_last5", 1.0))
        )
        neutral = bool(int(row.get("neutral", 0)))
        return self.predict_lambdas(
            home_attack, away_attack, home_defense, away_defense, neutral
        )

    # ------------------------------------------------------------------
    # Scoreline utilities
    # ------------------------------------------------------------------

    @staticmethod
    def top_scorelines(
        lambda_home: float,
        lambda_away: float,
        max_goals: int = 5,
        top_n: int = 3,
    ) -> list[tuple[str, float]]:
        """Return top-N most probable scorelines as (scoreline_str, probability)."""
        probs: list[tuple[str, float]] = []
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                p = float(poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away))
                probs.append((f"{h}-{a}", p))
        probs.sort(key=lambda x: x[1], reverse=True)
        return probs[:top_n]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, output_path: Path) -> None:
        ensure_parent_dir(output_path)
        output_path.write_text(
            json.dumps(asdict(self.params), indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, params_path: Path) -> "TeamDependentScoreModel":
        if not params_path.exists():
            raise FileNotFoundError(f"Scoreline model params not found: {params_path}")
        data = json.loads(params_path.read_text(encoding="utf-8"))
        model = cls()
        model.params = ScoreModelParams(**data)
        model._fitted = True
        return model


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fit team-dependent Poisson scoreline model."
    )
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    parser.add_argument(
        "--output-json",
        default=TeamDependentScoreModel.DEFAULT_PARAMS_FILE,
    )
    args = parser.parse_args()

    df = load_feature_data(args.features_csv)
    model = TeamDependentScoreModel()
    model.fit(df)
    output_path = PROJECT_ROOT / args.output_json
    model.save(output_path)
    print(f"Saved scoreline model params to: {output_path}")
    print(f"  base_home_lambda:      {model.params.base_home_lambda:.4f}")
    print(f"  base_away_lambda:      {model.params.base_away_lambda:.4f}")
    print(f"  home_advantage_factor: {model.params.home_advantage_factor:.4f}")
    print(f"  mean_attack:           {model.params.mean_attack:.4f}")
    print(f"  mean_defense:          {model.params.mean_defense:.4f}")


if __name__ == "__main__":
    main()
