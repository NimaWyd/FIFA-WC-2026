# Draw Class-Weight Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-compute inverse-frequency class weights from training data and multiply them into the existing sample weights so draws are no longer systematically underpredicted by XGBoost.

**Architecture:** `sklearn.utils.class_weight.compute_sample_weight('balanced', y_train)` produces per-sample weights inversely proportional to class frequency. These are element-wise multiplied with the existing time-decay `match_weight` array (or used alone if no time-decay weights exist), then passed as `sample_weight` to `classifier.fit()`. No changes to the Pipeline, inference path, or config are needed.

**Tech Stack:** Python, XGBoost, scikit-learn (`compute_sample_weight`), pytest

---

## File Map

| Action | File | What changes |
|--------|------|--------------|
| Modify | `fifa-2026-predictor/src/models/train_xgb.py` | Weight assembly block (lines 66–82): compute and multiply in class weights |
| Modify | `fifa-2026-predictor/tests/test_accuracy_improvements.py` | Add `TestClassWeightTuning` class with draw-recall assertion |

---

### Task 1: Write the failing test

**Files:**
- Modify: `fifa-2026-predictor/tests/test_accuracy_improvements.py`

- [ ] **Step 1: Add the failing test class at the bottom of the file**

Open `fifa-2026-predictor/tests/test_accuracy_improvements.py` and append the following class. It builds a heavily imbalanced synthetic dataset (H=60%, D=10%, A=30%), trains XGBoost using the *current* code path (which has no class weighting), and asserts that the mean predicted draw probability exceeds the naive draw frequency by at least 20% relative. This test should **fail** before the fix is applied.

```python
# ---------------------------------------------------------------------------
# Class-weight tuning — draws should be lifted above naive frequency
# ---------------------------------------------------------------------------

class TestClassWeightTuning:
    def _make_imbalanced_df(self, n: int = 200) -> pd.DataFrame:
        """Synthetic feature table with heavy draw underrepresentation (10%)."""
        np.random.seed(0)
        dates = pd.date_range("2010-01-01", periods=n, freq="7D")
        # 60% H, 10% D, 30% A
        targets = np.random.choice(["H", "D", "A"], size=n, p=[0.60, 0.10, 0.30])
        return pd.DataFrame({
            "date": dates,
            "home_team": "TeamA",
            "away_team": "TeamB",
            "competition": "Friendly",
            "home_confederation": "UEFA",
            "away_confederation": "UEFA",
            "tournament_stage": "unknown",
            "neutral": 0,
            "home_fifa_rank": 10,
            "away_fifa_rank": 20,
            "home_form_last5": np.random.uniform(0.5, 2.5, n),
            "away_form_last5": np.random.uniform(0.5, 2.5, n),
            "home_goals_for_last5": np.random.uniform(0.5, 2.5, n),
            "away_goals_for_last5": np.random.uniform(0.5, 2.5, n),
            "home_goals_against_last5": np.random.uniform(0.5, 2.0, n),
            "away_goals_against_last5": np.random.uniform(0.5, 2.0, n),
            "home_rest_days": 7,
            "away_rest_days": 7,
            "home_elo_pre": 1500.0,
            "away_elo_pre": 1490.0,
            "elo_diff_home_away": 10.0,
            "elo_win_prob": 0.51,
            "form_diff_home_away": 0.0,
            "goal_balance_diff": 0.0,
            "rank_diff": -10,
            "competition_weight": 1,
            "is_same_confederation": 1,
            "target": targets,
            "match_weight": 1.0,
        })

    def test_draw_probability_lifted_by_class_weights(self):
        """After class-weight tuning, mean draw prob must exceed naive draw freq."""
        from src.models.common import (
            build_preprocessor,
            make_chronological_split,
            to_xy,
        )
        from src.models.train_xgb import build_weighted_sample_weights
        from xgboost import XGBClassifier

        df = self._make_imbalanced_df(200)
        train_df, _, _ = make_chronological_split(df, val_size=0.15, test_size=0.15)
        preprocessor, feature_cols = build_preprocessor(df)
        x_train, y_train = to_xy(train_df, feature_cols)

        weights = build_weighted_sample_weights(y_train, train_df)

        preprocessor.fit(x_train, y_train)
        x_train_t = preprocessor.transform(x_train)

        clf = XGBClassifier(
            n_estimators=100,
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            random_state=42,
        )
        clf.fit(x_train_t, y_train, sample_weight=weights, verbose=False)

        probs = clf.predict_proba(x_train_t)
        draw_idx = 1  # TARGET_MAP: D=1
        mean_draw_prob = probs[:, draw_idx].mean()
        naive_draw_freq = (y_train == draw_idx).mean()

        # Class weighting must lift draw predictions at least 20% above naive freq
        assert mean_draw_prob > naive_draw_freq * 1.2, (
            f"mean_draw_prob={mean_draw_prob:.4f} not > "
            f"naive_draw_freq * 1.2 = {naive_draw_freq * 1.2:.4f}"
        )
```

- [ ] **Step 2: Run the test to confirm it fails**

```
cd fifa-2026-predictor
pytest tests/test_accuracy_improvements.py::TestClassWeightTuning::test_draw_probability_lifted_by_class_weights -v
```

Expected output: `FAILED` — `ImportError: cannot import name 'build_weighted_sample_weights' from 'src.models.train_xgb'`

---

### Task 2: Implement `build_weighted_sample_weights` and wire it in

**Files:**
- Modify: `fifa-2026-predictor/src/models/train_xgb.py`

- [ ] **Step 1: Add the import at the top of the file**

In `fifa-2026-predictor/src/models/train_xgb.py`, add this import after the existing imports (after line 18, before `from src.utils import load_config`):

```python
from sklearn.utils.class_weight import compute_sample_weight
```

- [ ] **Step 2: Add the `build_weighted_sample_weights` function**

Add this function immediately after the `parse_args` function (after line 26, before `def main()`):

```python
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
```

- [ ] **Step 3: Replace the weight-assembly block in `main()`**

Find and replace the existing weight-assembly block in `main()`. The current code (lines 66–82) looks like:

```python
    # Extract time-decay sample weights if the feature table provides them
    weights_train = (
        train_df["match_weight"].values if "match_weight" in train_df.columns else None
    )
    if weights_train is not None:
        print(f"Using time-decay sample weights "
              f"(min={weights_train.min():.3f}, max={weights_train.max():.3f})")
```

Replace it with:

```python
    weights_train = build_weighted_sample_weights(y_train, train_df)
    print(
        f"Using combined class+time-decay sample weights "
        f"(min={weights_train.min():.3f}, max={weights_train.max():.3f})"
    )
```

Also remove the now-redundant guard around `fit_kwargs["sample_weight"]`. Find this block (around line 80):

```python
    if weights_train is not None:
        fit_kwargs["sample_weight"] = weights_train
```

Replace it with:

```python
    fit_kwargs["sample_weight"] = weights_train
```

- [ ] **Step 4: Run the test to confirm it passes**

```
cd fifa-2026-predictor
pytest tests/test_accuracy_improvements.py::TestClassWeightTuning::test_draw_probability_lifted_by_class_weights -v
```

Expected output: `PASSED`

- [ ] **Step 5: Run the full test suite to check for regressions**

```
cd fifa-2026-predictor
pytest tests/ -v
```

Expected output: all tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add fifa-2026-predictor/src/models/train_xgb.py fifa-2026-predictor/tests/test_accuracy_improvements.py
git commit -m "feat: add auto class-weight tuning to XGBoost training (issue #42)

Draws were severely underpredicted because the model had no per-class
weighting. compute_sample_weight('balanced') now multiplies into the
existing time-decay weights so draws are penalised proportionally.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```
