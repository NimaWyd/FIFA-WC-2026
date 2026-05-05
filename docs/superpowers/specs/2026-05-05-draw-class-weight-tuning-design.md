# Design: Draw Class-Weight Tuning (Issue #42)

## Problem

XGBoost predicts almost no draws despite draws making up ~24% of matches. The model uses `multi:softprob` with no per-class weighting, causing it to heavily favour home wins.

## Goal

Auto-compute inverse-frequency class weights from training data and apply them during XGBoost training so draws are penalised less during fitting.

## Approach

Use `sklearn.utils.class_weight.compute_sample_weight('balanced', y_train)` to produce per-sample class weights. Multiply element-wise with the existing time-decay `match_weight` array (if present), then pass the combined array as `sample_weight` to `classifier.fit()`.

## Affected Files

- `fifa-2026-predictor/src/models/train_xgb.py` — weight assembly block (lines 66–82)
- `fifa-2026-predictor/tests/test_accuracy_improvements.py` — new test for draw recall

## Design Details

### `train_xgb.py` changes

In `main()`, after computing `weights_train` from `match_weight`:

```python
from sklearn.utils.class_weight import compute_sample_weight

class_weights = compute_sample_weight('balanced', y_train)
if weights_train is not None:
    weights_train = weights_train * class_weights
else:
    weights_train = class_weights
```

`weights_train` then flows into `fit_kwargs["sample_weight"]` unchanged — no other lines are modified. The sklearn `Pipeline` and all downstream inference code are untouched.

### `config.yaml` changes

None. Auto-computation requires no config parameters.

### Testing

New test in `TestNewModelsInEvaluationFramework` (or a new class):

1. Build a synthetic feature DataFrame with a heavy class imbalance (H=60%, D=10%, A=30%).
2. Train an XGBoost model via the updated `train_xgb.main()` logic (or equivalent inline call).
3. Assert that the model's mean predicted draw probability on the training set is greater than the naive draw frequency (10%) — confirming the class weighting is lifting draw predictions.

## Non-Goals

- No manual draw-weight config param
- No changes to inference path, feature pipeline, or Poisson scoring
- No replacement of time-decay `match_weight` (class weights multiply in, not override)

## Trade-offs Considered

| Option | Decision |
|--------|----------|
| Auto-compute balanced weights (chosen) | Principled, no tuning required |
| Manual draw multiplier in config.yaml | More control but needs manual tuning — rejected |
| XGBoost DMatrix per-class weights | Breaks sklearn Pipeline — rejected |
