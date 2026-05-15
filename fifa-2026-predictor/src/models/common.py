"""Shared helpers for model training and inference."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.utils import PROJECT_ROOT, ensure_parent_dir

TARGET_MAP = {"A": 0, "D": 1, "H": 2}
INV_TARGET_MAP = {v: k for k, v in TARGET_MAP.items()}


def load_feature_data(csv_path: str) -> pd.DataFrame:
    path = PROJECT_ROOT / csv_path
    if not path.exists():
        raise FileNotFoundError(f"Features file not found: {path}")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def make_chronological_split(
    df: pd.DataFrame,
    val_size: float,
    test_size: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if val_size <= 0 or test_size <= 0 or val_size + test_size >= 1:
        raise ValueError("Use valid split fractions where val+test < 1.")

    n = len(df)
    train_end = int(n * (1.0 - val_size - test_size))
    val_end = int(n * (1.0 - test_size))

    if train_end < 1 or val_end <= train_end:
        raise ValueError("Dataset too small for requested chronological split.")

    return (
        df.iloc[:train_end].copy(),
        df.iloc[train_end:val_end].copy(),
        df.iloc[val_end:].copy(),
    )


def build_preprocessor(df: pd.DataFrame) -> tuple[ColumnTransformer, list[str]]:
    # Team names are dropped — Elo ratings already capture team strength and
    # one-hot encoding sparse team indicators on limited data causes overfitting.
    categorical_features = [
        "competition",
        "home_confederation",
        "away_confederation",
        "tournament_stage",
    ]
    # Phase 1–3 core numeric features
    _base_numeric = [
        "neutral",
        "home_fifa_rank",
        "away_fifa_rank",
        "home_form_last5",
        "away_form_last5",
        "home_goals_for_last5",
        "away_goals_for_last5",
        "home_goals_against_last5",
        "away_goals_against_last5",
        "home_rest_days_log",
        "away_rest_days_log",
        "home_long_break",
        "away_long_break",
        "home_elo_pre",
        "away_elo_pre",
        "elo_diff_home_away",
        "elo_win_prob",
        "form_diff_home_away",
        "goal_balance_diff",
        "rank_diff",
        "competition_weight",
        "is_same_confederation",
        "match_weight",
    ]
    # Phase 4 extended features (included when present)
    _phase4_numeric = [
        "stage_importance",
        "home_form_w3",
        "away_form_w3",
        "home_form_w10",
        "away_form_w10",
        "home_form_rw5",
        "away_form_rw5",
        "home_attack_w5",
        "away_attack_w5",
        "home_defense_w5",
        "away_defense_w5",
        "home_attack_rw5",
        "away_attack_rw5",
        "home_defense_rw5",
        "away_defense_rw5",
        "home_adj_form_w5",
        "away_adj_form_w5",
        "home_adj_attack_w5",
        "away_adj_attack_w5",
        "home_adj_defense_w5",
        "away_adj_defense_w5",
        "attack_diff_w5",
        "defense_diff_w5",
        "adj_form_diff_w5",
        "form_diff_w3",
        "form_diff_w10",
    ]
    # Issue #50: inactivity-decayed Elo (included when present)
    _phase8_numeric = [
        "home_elo_effective",
        "away_elo_effective",
        "elo_diff_effective",
    ]
    # Phase 7: draw-rate and head-to-head features (included when present)
    _phase7_numeric = [
        "home_draw_rate_w5",
        "away_draw_rate_w5",
        "draw_rate_diff",
        "h2h_home_win_rate",
        "h2h_draw_rate",
        "h2h_goal_diff",
        "h2h_n_matches",
    ]
    # Issue #57: neutral-venue interaction features (included when present)
    _issue57_numeric = [
        "neutral_x_elo_diff",
        "neutral_x_rank_diff",
    ]
    # Issue #58: consecutive-result streak features (included when present)
    _issue58_numeric = [
        "home_win_streak",
        "away_win_streak",
        "home_unbeaten_streak",
        "away_unbeaten_streak",
        "home_loss_streak",
        "away_loss_streak",
    ]
    # Issue #88: clean sheet rate (included when present)
    _issue88_numeric = [
        "home_clean_sheet_rate_w5",
        "away_clean_sheet_rate_w5",
    ]
    # Issue #84: goal-difference form (included when present)
    _issue84_numeric = [
        "home_gd_form_w5",
        "away_gd_form_w5",
        "gd_form_diff",
    ]
    # Issue #85: venue-split form (included when present)
    _issue85_numeric = [
        "home_home_form_w5",
        "home_away_form_w5",
        "away_home_form_w5",
        "away_away_form_w5",
        "home_venue_form_diff",
        "away_venue_form_diff",
    ]
    # Issue #59: competition-tier base rates (included when present)
    _issue59_numeric = [
        "tier_home_rate",
        "tier_draw_rate",
        "tier_away_rate",
    ]
    # Issue #78: squad strength features (included when present)
    _issue78_numeric = [
        "home_squad_avg_rating",
        "away_squad_avg_rating",
        "squad_rating_diff",
        "home_top_player_rating",
        "away_top_player_rating",
    ]
    # Issue #87: WC penalty shootout win rate (included when present)
    _issue87_numeric = [
        "home_penalty_win_rate",
        "away_penalty_win_rate",
        "penalty_win_rate_diff",
    ]
    # Issue #119: confederation strength difference (included when present)
    _issue119_numeric = [
        "confederation_strength_diff",
    ]
    # Only include Phase 4 / Phase 7 / Phase 8 columns that actually exist in this DataFrame
    present_phase4 = [c for c in _phase4_numeric if c in df.columns]
    present_phase7 = [c for c in _phase7_numeric if c in df.columns]
    present_phase8 = [c for c in _phase8_numeric if c in df.columns]
    present_issue57 = [c for c in _issue57_numeric if c in df.columns]
    present_issue58 = [c for c in _issue58_numeric if c in df.columns]
    present_issue59 = [c for c in _issue59_numeric if c in df.columns]
    present_issue78 = [c for c in _issue78_numeric if c in df.columns]
    present_issue87 = [c for c in _issue87_numeric if c in df.columns]
    present_issue88 = [c for c in _issue88_numeric if c in df.columns]
    present_issue84 = [c for c in _issue84_numeric if c in df.columns]
    present_issue85 = [c for c in _issue85_numeric if c in df.columns]
    present_issue119 = [c for c in _issue119_numeric if c in df.columns]
    numeric_features = (_base_numeric + present_phase4 + present_phase7 + present_phase8
                        + present_issue57 + present_issue58 + present_issue59
                        + present_issue78 + present_issue87
                        + present_issue88 + present_issue84 + present_issue85
                        + present_issue119)
    used_features = categorical_features + numeric_features

    missing = sorted(set(used_features) - set(df.columns))
    if missing:
        raise ValueError(f"Missing expected feature columns: {missing}")

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("num", StandardScaler(), numeric_features),
        ],
        sparse_threshold=0.3,
    )
    return preprocessor, used_features


def to_xy(df: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    x = df[feature_cols].copy()
    y_series = df["target"].map(TARGET_MAP)
    if y_series.isna().any():
        bad = df.loc[y_series.isna(), "target"].unique().tolist()
        raise ValueError(f"Unknown target label(s) in data: {bad}")
    y = y_series.astype(int).values
    return x, y


class IsotonicCalibrationWrapper(BaseEstimator):
    """Wraps a fitted classifier with per-class OvR isotonic calibration.

    Replaces sklearn's CalibratedClassifierCV(cv='prefit') which was removed
    in sklearn 1.6+. Fits one IsotonicRegression per class on the validation
    set probabilities, then renormalizes to a valid probability simplex.
    """

    def __init__(self, classifier: Any) -> None:
        self.classifier = classifier
        self._calibrators: list[Any] | None = None
        self.classes_: np.ndarray | None = None

    def fit(self, X: Any, y: np.ndarray) -> "IsotonicCalibrationWrapper":
        from sklearn.isotonic import IsotonicRegression

        probs = self.classifier.predict_proba(X)
        self.classes_ = self.classifier.classes_
        self._calibrators = []
        for i, cls in enumerate(self.classes_):
            ir = IsotonicRegression(out_of_bounds="clip")
            ir.fit(probs[:, i], (y == cls).astype(int))
            self._calibrators.append(ir)
        return self

    def predict_proba(self, X: Any) -> np.ndarray:
        probs = self.classifier.predict_proba(X)
        cal = np.column_stack(
            [c.predict(probs[:, i]) for i, c in enumerate(self._calibrators)]
        )
        row_sums = cal.sum(axis=1, keepdims=True)
        return cal / np.maximum(row_sums, 1e-9)

    def predict(self, X: Any) -> np.ndarray:
        return self.classes_[self.predict_proba(X).argmax(axis=1)]


def ensure_artifact_dir(path_str: str) -> Path:
    path = PROJECT_ROOT / path_str
    ensure_parent_dir(path / "keep.txt")
    path.mkdir(parents=True, exist_ok=True)
    return path
