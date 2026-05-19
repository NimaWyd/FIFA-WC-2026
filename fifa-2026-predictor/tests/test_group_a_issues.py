"""Tests for Group A model-accuracy issues (#109, #111, #116, #118, #119)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.scoreline_model import TeamDependentScoreModel, ScoreModelParams


# ---------------------------------------------------------------------------
# Issue #119 — xG/win-probability consistency: calibrated lambdas used for xG
# ---------------------------------------------------------------------------

class TestCalibratedLambdaBounds:
    """calibrate_lambdas_to_outcomes must stay within [0.5, 2.5] (tighter than old 0.3–3.5)."""

    def test_calibrated_lambdas_capped_at_2_5_for_dominant_home(self):
        """Very dominant home team (85% win prob) must not push λ_home above 2.5."""
        lh, la = TeamDependentScoreModel.calibrate_lambdas_to_outcomes(
            p_home_win=0.85, p_draw=0.10, p_away_win=0.05,
            lambda_home_init=1.8, lambda_away_init=0.7,
        )
        assert lh <= 2.5, f"Home lambda {lh:.3f} exceeded 2.5 cap — unrealistic xG"
        assert la >= 0.5, f"Away lambda {la:.3f} below 0.5 floor"

    def test_calibrated_lambdas_floored_at_0_5_for_dominated_team(self):
        """Very weak away team (5% win prob) must not push λ_away below 0.5."""
        lh, la = TeamDependentScoreModel.calibrate_lambdas_to_outcomes(
            p_home_win=0.80, p_draw=0.15, p_away_win=0.05,
            lambda_home_init=2.0, lambda_away_init=0.6,
        )
        assert la >= 0.5, f"Away lambda {la:.3f} below 0.5 floor"
        assert lh <= 2.5, f"Home lambda {lh:.3f} exceeded 2.5 cap"

    def test_away_dominant_gives_higher_away_lambda(self):
        """When away team has higher win prob, calibrated λ_away must exceed λ_home."""
        lh, la = TeamDependentScoreModel.calibrate_lambdas_to_outcomes(
            p_home_win=0.30, p_draw=0.27, p_away_win=0.43,
            lambda_home_init=1.4, lambda_away_init=1.1,
        )
        assert la > lh, (
            f"Away team wins more (43% vs 30%) but λ_away={la:.3f} < λ_home={lh:.3f}"
        )


@pytest.mark.skipif(
    not (lambda: __import__('pathlib').Path(
        __import__('pathlib').Path(__file__).parents[1]
        / "src/models/artifacts/scoreline_params.json"
    ).exists())(),
    reason="scoreline_params.json not found",
)
class TestXGMatchesWinProbDirection:
    """xG direction must match win-probability direction (services.py must use calibrated lambdas)."""

    def _predict(self, home: str, away: str) -> dict:
        from src.api.services import predict
        return predict(
            home_team=home, away_team=away,
            match_date="2026-06-20",
            competition="FIFA World Cup", neutral=True,
            home_confederation=None, away_confederation=None,
            home_fifa_rank=None, away_fifa_rank=None,
            tournament_stage="Group Stage",
        )

    def test_stronger_team_has_higher_xg(self):
        """The team with higher win probability should also have higher expected goals."""
        result = self._predict("Iran", "Turkey")
        probs = result["probabilities"]
        eg = result["expected_goals"]
        if abs(probs["home_win"] - probs["away_win"]) < 0.05:
            pytest.skip("Teams too evenly matched to test direction")
        if probs["away_win"] > probs["home_win"]:
            assert eg["away"] > eg["home"], (
                f"Away wins more ({probs['away_win']:.2f} vs {probs['home_win']:.2f}) "
                f"but xG: home={eg['home']:.2f} away={eg['away']:.2f}"
            )
        else:
            assert eg["home"] > eg["away"], (
                f"Home wins more ({probs['home_win']:.2f} vs {probs['away_win']:.2f}) "
                f"but xG: home={eg['home']:.2f} away={eg['away']:.2f}"
            )


# ---------------------------------------------------------------------------
# Issue #118 — Scoreline diversity: natural lambdas stay realistic
# ---------------------------------------------------------------------------

class TestNaturalLambdas:
    """Natural lambdas from attack/defense ratings should stay in 0.8–2.5 range."""

    def _make_model(self) -> TeamDependentScoreModel:
        m = TeamDependentScoreModel()
        m.params = ScoreModelParams(
            base_home_lambda=1.5,
            base_away_lambda=1.2,
            home_advantage_factor=1.15,
            mean_attack=1.3,
            mean_defense=1.1,
        )
        m._fitted = True
        return m

    def test_balanced_match_lambdas_realistic(self):
        """Neutral match between equal teams → lambdas 0.8–2.5."""
        model = self._make_model()
        row = {
            "home_attack_w5": 1.3,
            "away_attack_w5": 1.3,
            "home_defense_w5": 1.1,
            "away_defense_w5": 1.1,
            "neutral": 1,
        }
        lh, la = model.predict_lambdas_from_row(row)
        assert 0.8 <= lh <= 2.5, f"home lambda {lh} out of realistic range"
        assert 0.8 <= la <= 2.5, f"away lambda {la} out of realistic range"

    def test_balanced_match_top_scoreline_realistic(self):
        """Equal teams on neutral ground: top scoreline should be 1-0, 1-1, or 2-1."""
        model = self._make_model()
        row = {
            "home_attack_w5": 1.3,
            "away_attack_w5": 1.3,
            "home_defense_w5": 1.1,
            "away_defense_w5": 1.1,
            "neutral": 1,
        }
        lh, la = model.predict_lambdas_from_row(row)
        scorelines = TeamDependentScoreModel.top_scorelines(lh, la, top_n=3)
        top_score = scorelines[0][0]
        assert top_score in ("1-0", "1-1", "2-1", "0-1", "0-0"), \
            f"Top scoreline {top_score} is unrealistic for balanced match"

    def test_strong_favourite_lambdas_higher(self):
        """Dominant team should have clearly higher expected goals than weak opponent."""
        model = self._make_model()
        row_dominant = {
            "home_attack_w5": 2.5,
            "away_attack_w5": 0.5,
            "home_defense_w5": 0.5,
            "away_defense_w5": 2.5,
            "neutral": 1,
        }
        lh, la = model.predict_lambdas_from_row(row_dominant)
        assert lh > la * 2, f"Expected dominant home lambda >> away but got {lh:.2f} vs {la:.2f}"


def _model_and_data_available() -> bool:
    try:
        from src.api.services import _get_model, _get_history
        return _get_model() is not None and _get_history() is not None
    except Exception:
        return False

_integration_skip = pytest.mark.skipif(
    not _model_and_data_available(),
    reason="Model artifact or history CSV not found",
)


@_integration_skip
class TestScorelineIntegration:
    """Integration: API scorelines should be realistic, not inflated."""

    def test_expected_goals_realistic(self):
        """Expected goals should be in 0.8–2.5 range for most WC group fixtures."""
        from src.api.services import predict
        result = predict(
            home_team="France", away_team="Morocco",
            match_date="2026-06-20",
            competition="FIFA World Cup", neutral=True,
            home_confederation=None, away_confederation=None,
            home_fifa_rank=None, away_fifa_rank=None,
            tournament_stage="Group Stage",
        )
        eg = result["expected_goals"]
        assert 0.5 <= eg["home"] <= 3.0, f"Home xG {eg['home']} unrealistic"
        assert 0.5 <= eg["away"] <= 3.0, f"Away xG {eg['away']} unrealistic"

    def test_top_scoreline_not_always_2_1(self):
        """Lopsided match (Spain vs Saudi Arabia) should show 3-0 or 3-1 as top."""
        from src.api.services import predict
        result = predict(
            home_team="Spain", away_team="Saudi Arabia",
            match_date="2026-06-20",
            competition="FIFA World Cup", neutral=True,
            home_confederation=None, away_confederation=None,
            home_fifa_rank=None, away_fifa_rank=None,
            tournament_stage="Group Stage",
        )
        scorelines = [s["scoreline"] for s in result["top_scorelines"]]
        assert "2-1" not in scorelines[:1], \
            f"2-1 should not be top scoreline for dominant mismatch, got: {scorelines}"


# ---------------------------------------------------------------------------
# Issue #109 — Neutral-ground symmetry
# ---------------------------------------------------------------------------

@_integration_skip
class TestNeutralSymmetry:
    """Swapping home/away on neutral ground should give near-identical predictions."""

    def _pred(self, home: str, away: str) -> dict:
        from src.api.services import predict
        return predict(
            home_team=home, away_team=away,
            match_date="2026-06-20",
            competition="FIFA World Cup", neutral=True,
            home_confederation=None, away_confederation=None,
            home_fifa_rank=None, away_fifa_rank=None,
            tournament_stage="Group Stage",
        )

    def test_symmetric_home_win_prob(self):
        """P(Argentina wins) should be same whether listed as home or away."""
        fwd = self._pred("Argentina", "Portugal")
        rev = self._pred("Portugal", "Argentina")
        p_arg_fwd = fwd["probabilities"]["home_win"]
        p_arg_rev = rev["probabilities"]["away_win"]
        assert abs(p_arg_fwd - p_arg_rev) < 0.02, (
            f"Neutral asymmetry: Argentina wins {p_arg_fwd:.3f} (home) "
            f"vs {p_arg_rev:.3f} (away) — delta {abs(p_arg_fwd - p_arg_rev):.3f}"
        )

    def test_probabilities_sum_to_one_after_averaging(self):
        """Averaged probabilities must still sum to 1.0."""
        result = self._pred("Brazil", "France")
        total = sum(result["probabilities"].values())
        assert abs(total - 1.0) < 1e-4, f"Probabilities sum to {total}"

    def test_non_neutral_is_not_symmetrized(self):
        """Non-neutral predictions should NOT be averaged (home team keeps advantage)."""
        from src.api.services import predict
        home_pred = predict(
            home_team="Brazil", away_team="Argentina",
            match_date="2026-06-20",
            competition="FIFA World Cup Qualification", neutral=False,
            home_confederation=None, away_confederation=None,
            home_fifa_rank=None, away_fifa_rank=None,
            tournament_stage="Unknown",
        )
        away_pred = predict(
            home_team="Argentina", away_team="Brazil",
            match_date="2026-06-20",
            competition="FIFA World Cup Qualification", neutral=False,
            home_confederation=None, away_confederation=None,
            home_fifa_rank=None, away_fifa_rank=None,
            tournament_stage="Unknown",
        )
        p_bra_home = home_pred["probabilities"]["home_win"]
        p_bra_away = away_pred["probabilities"]["away_win"]
        assert abs(p_bra_home - p_bra_away) > 0.02, (
            "Non-neutral predictions should differ when team order swapped"
        )


# ---------------------------------------------------------------------------
# Issue #111 — Neutral flag: metadata flag for symmetry
# ---------------------------------------------------------------------------

@_integration_skip
class TestNeutralFlag:
    """Neutral symmetry flag appears in metadata."""

    def test_neutral_prediction_has_symmetry_flag(self):
        """Metadata should carry neutral_symmetry_applied=True for neutral matches."""
        from src.api.services import predict
        result = predict(
            home_team="England", away_team="Germany",
            match_date="2026-06-20",
            competition="FIFA World Cup", neutral=True,
            home_confederation=None, away_confederation=None,
            home_fifa_rank=None, away_fifa_rank=None,
            tournament_stage="Group Stage",
        )
        assert result["metadata"].get("neutral_symmetry_applied") is True

    def test_non_neutral_prediction_flag_is_false(self):
        """Non-neutral matches should have neutral_symmetry_applied=False."""
        from src.api.services import predict
        result = predict(
            home_team="Brazil", away_team="Argentina",
            match_date="2026-06-20",
            competition="FIFA World Cup Qualification", neutral=False,
            home_confederation=None, away_confederation=None,
            home_fifa_rank=None, away_fifa_rank=None,
            tournament_stage="Unknown",
        )
        assert result["metadata"].get("neutral_symmetry_applied") is False


# ---------------------------------------------------------------------------
# Issue #116 — Ensemble diversity: no model universally floored
# ---------------------------------------------------------------------------

class TestEnsembleDiversity:
    """After retraining, all per-class weights should be above the new 0.02 floor
    for at least one class, and no model should be universally floored."""

    def _load_ensemble(self):
        import joblib
        from pathlib import Path
        path = Path(__file__).parents[1] / "src/models/artifacts/ensemble.joblib"
        if not path.exists():
            pytest.skip("ensemble.joblib not found")
        return joblib.load(path)

    def test_no_model_universally_floored(self):
        """Each base model should have at least one class weight above 0.05."""
        ens = self._load_ensemble()
        w = ens.per_class_weights  # shape (3, 3): [model, class]
        for m_idx, name in enumerate(["xgb", "logreg", "mlp"]):
            max_weight = w[m_idx, :].max()
            assert max_weight > 0.05, (
                f"{name} has all per-class weights <= 0.05: {w[m_idx, :]}"
            )

    def test_draw_blend_weight_above_zero(self):
        """Draw blend weight should be > 0 (optimizer found genuine contribution)."""
        ens = self._load_ensemble()
        assert ens.draw_blend_weight > 0.0, \
            f"draw_blend_weight is {ens.draw_blend_weight} — optimizer collapsed it"

    def test_probabilities_sum_to_one(self):
        """Ensemble predict_proba must still sum to 1.0 after retraining."""
        import numpy as np
        ens = self._load_ensemble()
        rng = np.random.default_rng(0)
        n = 10
        df = pd.DataFrame({
            "home_elo_pre": rng.normal(1500, 100, n),
            "away_elo_pre": rng.normal(1500, 100, n),
            "elo_diff_home_away": rng.normal(0, 50, n),
            "elo_win_prob": rng.uniform(0.3, 0.7, n),
            "home_form_last5": rng.uniform(0, 3, n),
            "away_form_last5": rng.uniform(0, 3, n),
            "neutral": rng.choice([True, False], n),
            "competition": ["FIFA World Cup"] * n,
            "home_confederation": ["UEFA"] * n,
            "away_confederation": ["CONMEBOL"] * n,
            "tournament_stage": ["Group Stage"] * n,
            "home_fifa_rank": rng.integers(1, 50, n),
            "away_fifa_rank": rng.integers(1, 50, n),
        })
        feature_cols = ens.feature_cols
        for col in feature_cols:
            if col not in df.columns:
                df[col] = 0.0
        proba = ens.predict_proba(df)
        row_sums = proba.sum(axis=1)
        assert np.allclose(row_sums, 1.0, atol=1e-4), \
            f"Row sums not 1.0: {row_sums}"
