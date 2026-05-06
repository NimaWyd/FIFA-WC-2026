"""Train binary draw/not-draw classifier for P(Draw)."""
from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight

from src.models.common import (
    build_preprocessor,
    ensure_artifact_dir,
    load_feature_data,
    make_chronological_split,
    to_xy,
)
from src.utils import load_config


def train_draw_submodel(df: pd.DataFrame, cfg: dict) -> Pipeline:
    """Fit a binary draw/not-draw LogReg pipeline on the training split of df."""
    train_df, val_df, test_df = make_chronological_split(
        df,
        val_size=float(cfg["model"]["val_size"]),
        test_size=float(cfg["model"]["test_size"]),
    )
    preprocessor, feature_cols = build_preprocessor(df)
    X_train, _ = to_xy(train_df, feature_cols)
    y_train = (train_df["target"] == "D").astype(int).values

    weights = compute_sample_weight("balanced", y_train)
    preprocessor.fit(X_train)
    X_train_t = preprocessor.transform(X_train)

    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_train_t, y_train, sample_weight=weights)

    model = Pipeline([("preprocessor", preprocessor), ("classifier", clf)])
    print(f"Draw submodel — train: {len(train_df)} | val: {len(val_df)} | test: {len(test_df)}")
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train binary draw submodel.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    args = parser.parse_args()

    cfg = load_config()
    df = load_feature_data(args.features_csv)

    min_train_year = int(cfg["model"].get("min_train_year", 0))
    if min_train_year > 0:
        n_before = len(df)
        df = df[pd.to_datetime(df["date"]).dt.year >= min_train_year].reset_index(drop=True)
        print(f"Filtered to {min_train_year}+: {n_before} -> {len(df)} rows")

    model = train_draw_submodel(df, cfg)

    artifact_dir = ensure_artifact_dir(cfg["paths"]["trained_model_dir"])
    path = artifact_dir / "draw_submodel.joblib"
    joblib.dump(model, path)
    print(f"Saved draw submodel to {path}")


if __name__ == "__main__":
    main()
