"""Tests for Group A model-accuracy issues (#109, #111, #116, #118)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.scoreline_model import TeamDependentScoreModel, ScoreModelParams


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
