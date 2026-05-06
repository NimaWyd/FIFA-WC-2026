# Draw Submodel + Ensemble Design
**Issues:** #46 (two-stage draw prediction), #43 (XGBoost + LogReg + MLP ensemble)
**Date:** 2026-05-06
**Approach:** Option B — draw submodel as post-hoc probability adjuster blended into ensemble

---

## Architecture Overview

Two new artifacts saved in `src/models/artifacts/`:
- `draw_submodel.joblib` — binary classifier for P(Draw)
- `ensemble.joblib` — `EnsembleModel` wrapping XGB + LogReg + MLP + draw blend weights

**Training flow:**
1. `python -m src.models.train_xgb` — existing, unchanged
2. `python -m src.models.train_logreg` — existing, unchanged (after #54 fix)
3. `python -m src.models.train_draw_submodel` — new, trains binary draw classifier
4. `python -m src.models.train_ensemble` — new, loads base models, optimizes blend weights, saves `ensemble.joblib`

**Inference flow:**
`services.py` preference order: `ensemble.joblib` → `xgb.joblib` → `logreg.joblib`
`EnsembleModel.predict_proba()` runs all 3 base models + draw blend in one call, returning a (1, 3) array in the same format as the existing pipeline.

---

## Draw Submodel (#46)

**File:** `src/models/train_draw_submodel.py`

**Training details:**
- Same chronological split as XGBoost: `min_train_year` from config, same `val_size`/`test_size`
- Binary target: `y = 1 if outcome == "D" else 0`
- Uses existing `build_preprocessor()` — no new feature columns; draw_rate and H2H features already in `common.py` provide the signal
- Classifier: `LogisticRegression(class_weight="balanced")` — better calibrated than XGBoost for binary tasks; balanced weights handle ~25% draw frequency
- No `IsotonicCalibrationWrapper` needed — LogReg probabilities are natively well-calibrated
- Saved as plain sklearn `Pipeline([("preprocessor", preprocessor), ("classifier", clf)])`

**Blending formula (applied inside `EnsembleModel.predict_proba`):**
```
p_draw_final  = w * p_draw_submodel + (1 - w) * p_draw_ensemble
remaining     = 1 - p_draw_final
p_H_final     = (p_H_ensemble / (p_H_ensemble + p_A_ensemble)) * remaining
p_A_final     = (p_A_ensemble / (p_H_ensemble + p_A_ensemble)) * remaining
```
Where `w ∈ [0, 1]` is learned on the val set and stored in `ensemble.joblib`.
Edge case: if `p_H_ensemble + p_A_ensemble ≈ 0`, split remaining 50/50.

---

## Ensemble Model (#43)

**New files:**
- `src/models/ensemble_model.py` — `EnsembleModel` class
- `src/models/train_ensemble.py` — training script

**`EnsembleModel` class (in `ensemble_model.py`):**
```python
class EnsembleModel:
    # Holds: xgb_pipeline, logreg_pipeline, mlp_pipeline, draw_submodel
    #        per_class_weights (3x3 array), draw_blend_weight (float)

    def predict_proba(self, feature_row: pd.DataFrame) -> np.ndarray
        # Returns (n, 3) ordered [A=0, D=1, H=2] — same contract as existing pipelines

    def save(self, path: Path) -> None
    @classmethod
    def load(cls, path: Path) -> "EnsembleModel"
```
The class is intentionally minimal — no `fit()` method; training logic lives in `train_ensemble.py`.

**Training script (`train_ensemble.py`):**
1. Load `features.csv`, apply `min_train_year` filter, make chronological split (same config as XGBoost)
2. Load `xgb.joblib` and `logreg.joblib` from artifacts dir; train fresh `MLPModel` on train split
3. Get val-set `predict_proba()` from all 3 base models → shape (n_val, 3) each
4. Optimize per-class blend weights by minimizing log-loss on val set via `scipy.optimize.minimize(method="SLSQP")` with constraints: weights ≥ 0, sum to 1 per class
5. Train `draw_submodel` on train split; get val-set `p_draw` predictions; optimize `w_draw` (scalar) by minimizing log-loss on draw binary labels
6. Package everything into `EnsembleModel`, save to `ensemble.joblib`

**`services.py` change (single line):**
```python
for name in ("ensemble.joblib", "xgb.joblib", "logreg.joblib"):
```

---

## Testing

**New file:** `tests/test_ensemble.py`

| Test | What it checks |
|------|----------------|
| `test_draw_submodel_trains` | Fits on small fixture df, outputs `p_draw ∈ [0, 1]` |
| `test_draw_submodel_proba_sum` | Final blended probabilities sum to 1.0 |
| `test_ensemble_predict_proba_shape` | Returns (n, 3) array |
| `test_ensemble_proba_sums_to_one` | Row sums == 1.0 for all inputs |
| `test_ensemble_blend_weight_bounds` | Learned `w_draw ∈ [0, 1]` |
| `test_ensemble_save_load_roundtrip` | Save/load produces identical probabilities |
| `test_services_loads_ensemble_first` | `_get_model()` prefers `ensemble.joblib` when present |

All 327 existing tests remain unchanged.

---

## File Summary

| File | Status |
|------|--------|
| `src/models/ensemble_model.py` | New |
| `src/models/train_draw_submodel.py` | New |
| `src/models/train_ensemble.py` | New |
| `src/api/services.py` | 1-line change (preference order) |
| `tests/test_ensemble.py` | New |
| `src/models/artifacts/draw_submodel.joblib` | New artifact (generated) |
| `src/models/artifacts/ensemble.joblib` | New artifact (generated) |
