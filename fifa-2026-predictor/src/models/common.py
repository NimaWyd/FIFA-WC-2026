"""Shared helpers for model training and inference."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
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
    categorical_features = [
        "home_team",
        "away_team",
        "competition",
        "home_confederation",
        "away_confederation",
        "tournament_stage",
    ]
    numeric_features = [
        "neutral",
        "home_fifa_rank",
        "away_fifa_rank",
        "home_form_last5",
        "away_form_last5",
        "home_goals_for_last5",
        "away_goals_for_last5",
        "home_goals_against_last5",
        "away_goals_against_last5",
        "home_rest_days",
        "away_rest_days",
        "home_elo_pre",
        "away_elo_pre",
        "elo_diff_home_away",
        "form_diff_home_away",
        "goal_balance_diff",
    ]
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
    y = df["target"].map(TARGET_MAP).values
    return x, y


def ensure_artifact_dir(path_str: str) -> Path:
    path = PROJECT_ROOT / path_str
    ensure_parent_dir(path / "keep.txt")
    path.mkdir(parents=True, exist_ok=True)
    return path

