"""Train XGBoost multiclass model for outcome probabilities."""

from __future__ import annotations

import argparse
import json

import joblib
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from src.models.common import (
    build_preprocessor,
    ensure_artifact_dir,
    load_feature_data,
    make_chronological_split,
    to_xy,
)
from src.utils import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train XGBoost model.")
    parser.add_argument("--features-csv", default="data/processed/features.csv")
    parser.add_argument("--model-name", default="xgb")
    return parser.parse_args()


def build_weighted_sample_weights(
    y: "np.ndarray",
    df: "pd.DataFrame",
) -> "np.ndarray":
    """Return sample weights combining class balance and time-decay.

    Multiplies inverse-frequency class weights by the per-row ``match_weight``
    column when present, so recent draws are weighted highest.
    """
    class_weights = compute_sample_weight("balanced", y)
    if "match_weight" in df.columns:
        return df["match_weight"].values * class_weights
    return class_weights


def main() -> None:
    cfg = load_config()
    args = parse_args()

    df = load_feature_data(args.features_csv)
    train_df, val_df, test_df = make_chronological_split(
        df,
        val_size=float(cfg["model"]["val_size"]),
        test_size=float(cfg["model"]["test_size"]),
    )
    preprocessor, feature_cols = build_preprocessor(df)
    x_train, y_train = to_xy(train_df, feature_cols)
    x_val, y_val = to_xy(val_df, feature_cols)

    xgb_cfg = cfg["model"]["xgb"]
    esr = xgb_cfg.get("early_stopping_rounds")
    early_stopping_rounds = int(esr) if esr is not None else None
    if early_stopping_rounds is not None and early_stopping_rounds <= 0:
        early_stopping_rounds = None

    classifier = XGBClassifier(
        n_estimators=int(xgb_cfg["n_estimators"]),
        learning_rate=float(xgb_cfg["learning_rate"]),
        max_depth=int(xgb_cfg["max_depth"]),
        subsample=float(xgb_cfg["subsample"]),
        colsample_bytree=float(xgb_cfg["colsample_bytree"]),
        min_child_weight=int(xgb_cfg.get("min_child_weight", 1)),
        gamma=float(xgb_cfg.get("gamma", 0.0)),
        reg_alpha=float(xgb_cfg.get("reg_alpha", 0.0)),
        reg_lambda=float(xgb_cfg.get("reg_lambda", 1.0)),
        objective=str(xgb_cfg["objective"]),
        num_class=3,
        eval_metric="mlogloss",
        random_state=int(cfg["project"]["random_state"]),
        early_stopping_rounds=early_stopping_rounds,
    )

    weights_train = build_weighted_sample_weights(y_train, train_df)
    print(
        f"Using combined class+time-decay sample weights "
        f"(min={weights_train.min():.3f}, max={weights_train.max():.3f})"
    )

    preprocessor.fit(x_train, y_train)
    x_train_t = preprocessor.transform(x_train)
    x_val_t = preprocessor.transform(x_val)
    fit_kwargs: dict = {"verbose": False}
    if early_stopping_rounds is not None and early_stopping_rounds > 0:
        fit_kwargs["eval_set"] = [(x_val_t, y_val)]
    fit_kwargs["sample_weight"] = weights_train
    classifier.fit(x_train_t, y_train, **fit_kwargs)

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )

    artifact_dir = ensure_artifact_dir(cfg["paths"]["trained_model_dir"])
    model_path = artifact_dir / f"{args.model_name}.joblib"
    meta_path = artifact_dir / f"{args.model_name}_meta.json"
    joblib.dump(model, model_path)
    metadata = {
        "model_type": "xgboost",
        "features_csv": args.features_csv,
        "split_sizes": {
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df),
        },
        "feature_columns": feature_cols,
        "early_stopping_rounds": early_stopping_rounds,
    }
    if early_stopping_rounds is not None and early_stopping_rounds > 0:
        try:
            metadata["best_iteration"] = int(classifier.best_iteration)
        except AttributeError:
            pass
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved model to {model_path}")
    print(f"Train: {len(train_df)} | Val: {len(val_df)} | Test: {len(test_df)}")


if __name__ == "__main__":
    main()
