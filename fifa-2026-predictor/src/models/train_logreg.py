"""Train logistic regression baseline for 3-way outcome prediction."""

from __future__ import annotations

import argparse
import json

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.models.common import (
    build_preprocessor,
    ensure_artifact_dir,
    load_feature_data,
    make_chronological_split,
    to_xy,
)
from src.utils import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train logistic baseline.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    parser.add_argument("--model-name", default="logreg")
    return parser.parse_args()


def main() -> None:
    cfg = load_config()
    args = parse_args()

    df = load_feature_data(args.features_csv)
    min_train_year = int(cfg["model"].get("min_train_year", 0))
    if min_train_year > 0:
        n_before = len(df)
        df = df[pd.to_datetime(df["date"]).dt.year >= min_train_year].reset_index(drop=True)
        print(f"Filtered to {min_train_year}+: {n_before} -> {len(df)} rows")

    train_df, val_df, test_df = make_chronological_split(
        df,
        val_size=float(cfg["model"]["val_size"]),
        test_size=float(cfg["model"]["test_size"]),
    )

    preprocessor, feature_cols = build_preprocessor(df)
    x_train, y_train = to_xy(train_df, feature_cols)

    weights_train = (
        train_df["match_weight"].values if "match_weight" in train_df.columns else None
    )
    if weights_train is not None:
        print(f"Using time-decay sample weights "
              f"(min={weights_train.min():.3f}, max={weights_train.max():.3f})")

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "classifier",
                LogisticRegression(
                    max_iter=int(cfg["model"]["logistic_max_iter"]),
                    class_weight="balanced",
                ),
            ),
        ]
    )
    fit_kwargs: dict = {}
    if weights_train is not None:
        fit_kwargs["classifier__sample_weight"] = weights_train
    model.fit(x_train, y_train, **fit_kwargs)

    artifact_dir = ensure_artifact_dir(cfg["paths"]["trained_model_dir"])
    model_path = artifact_dir / f"{args.model_name}.joblib"
    meta_path = artifact_dir / f"{args.model_name}_meta.json"
    joblib.dump(model, model_path)

    metadata = {
        "model_type": "logistic_regression",
        "features_csv": args.features_csv,
        "split_sizes": {
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df),
        },
        "feature_columns": feature_cols,
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved model to {model_path}")


if __name__ == "__main__":
    main()

