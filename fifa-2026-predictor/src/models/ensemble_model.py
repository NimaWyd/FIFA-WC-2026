"""EnsembleModel: blends XGBoost + LogReg + MLP with a draw submodel adjustment."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


class EnsembleModel:
    """Blends 3 base classifiers with per-class weights + post-hoc draw submodel adjustment.

    Exposes the same predict_proba interface and named_steps property as a
    sklearn Pipeline so services.py requires no changes beyond preference order.
    """

    def __init__(
        self,
        xgb_pipeline: Any,
        logreg_pipeline: Any,
        mlp_pipeline: Any,
        draw_submodel: Any,
        per_class_weights: np.ndarray,
        draw_blend_weight: float,
        feature_cols: list[str],
    ) -> None:
        self.xgb_pipeline = xgb_pipeline
        self.logreg_pipeline = logreg_pipeline
        self.mlp_pipeline = mlp_pipeline
        self.draw_submodel = draw_submodel
        self.per_class_weights = np.asarray(per_class_weights)  # shape (3, 3): [model, class]
        self.draw_blend_weight = float(draw_blend_weight)
        self.feature_cols = feature_cols
        self.classes_ = np.array([0, 1, 2])

    @property
    def named_steps(self) -> dict[str, Any]:
        """Compatibility shim: services.py does model.named_steps['classifier'].classes_."""
        return {"classifier": self}

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return (n, 3) probability array ordered [A=0, D=1, H=2]."""
        p_xgb = self._get_base_proba(self.xgb_pipeline, X)
        p_logreg = self._get_base_proba(self.logreg_pipeline, X)
        p_mlp = self._get_base_proba(self.mlp_pipeline, X)

        # Weighted blend per class; per_class_weights[model_idx, class_idx]
        blended = np.zeros((len(X), 3))
        for m_idx, p in enumerate([p_xgb, p_logreg, p_mlp]):
            for c_idx in range(3):
                blended[:, c_idx] += self.per_class_weights[m_idx, c_idx] * p[:, c_idx]

        # Draw submodel post-hoc adjustment (D = class index 1)
        p_draw_sub = self.draw_submodel.predict_proba(X)[:, 1]
        w = self.draw_blend_weight
        p_draw_final = w * p_draw_sub + (1.0 - w) * blended[:, 1]

        # Redistribute remaining probability between A and H in their original ratio
        ha_sum = blended[:, 0] + blended[:, 2]
        safe_ha = np.where(ha_sum < 1e-9, 1.0, ha_sum)
        remaining = 1.0 - p_draw_final
        p_A = (blended[:, 0] / safe_ha) * remaining
        p_H = (blended[:, 2] / safe_ha) * remaining

        result = np.column_stack([p_A, p_draw_final, p_H])
        row_sums = result.sum(axis=1, keepdims=True)
        return result / np.maximum(row_sums, 1e-9)

    def _get_base_proba(self, model: Any, X: pd.DataFrame) -> np.ndarray:
        """Get (n, 3) probabilities ordered [A=0, D=1, H=2] from any model type."""
        from src.evaluation.baselines import MLPModel
        if isinstance(model, MLPModel):
            # MLPModel.predict_proba calls to_xy which requires a 'target' column.
            # Add a dummy column when absent (inference path); to_xy discards it anyway.
            X_in = X.copy() if "target" not in X.columns else X
            if "target" not in X_in.columns:
                X_in["target"] = "H"
            return model.predict_proba(X_in)
        # sklearn Pipeline: reorder by classes_ to guarantee [A=0, D=1, H=2]
        raw = model.predict_proba(X)
        classes = np.asarray(model.named_steps["classifier"].classes_).astype(int).ravel()
        order = np.argsort(classes)
        if np.array_equal(order, np.arange(len(classes))):
            return raw
        return raw[:, order]

    def save(self, path: Path) -> None:
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> "EnsembleModel":
        return joblib.load(path)
