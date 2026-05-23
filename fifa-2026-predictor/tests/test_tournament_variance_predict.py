"""Tests for tournament variance factor applied to WC group-stage predictions (#162).

The Monte Carlo simulation blends probabilities 12% toward uniform before sampling.
Individual /predict calls for neutral WC group-stage matches must apply the same
blend so displayed odds match what the simulation is actually using internally.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


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


def _pred(home: str, away: str, neutral: bool, stage: str, competition: str = "FIFA World Cup"):
    from src.api.services import predict
    return predict(
        home_team=home, away_team=away,
        match_date="2026-06-20",
        competition=competition,
        neutral=neutral,
        home_confederation=None, away_confederation=None,
        home_fifa_rank=None, away_fifa_rank=None,
        tournament_stage=stage,
    )


# ---------------------------------------------------------------------------
# Issue #162 — Variance factor applied to WC group-stage neutral predictions
# ---------------------------------------------------------------------------

@_integration_skip
class TestTournamentVarianceFactor:
    """predict() must blend probabilities toward uniform for neutral WC group-stage matches."""

    def test_group_stage_probs_compressed_toward_uniform(self):
        """WC group-stage probs must be closer to [0.33,0.33,0.33] than raw probs."""
        result = _pred("France", "Morocco", neutral=True, stage="Group Stage")
        probs = result["probabilities"]
        raw = result["metadata"]["raw_probabilities"]

        uniform = 1.0 / 3.0
        for key in ("home_win", "draw", "away_win"):
            dist_blended = abs(probs[key] - uniform)
            dist_raw = abs(raw[key] - uniform)
            assert dist_blended <= dist_raw + 1e-6, (
                f"{key}: blended distance from uniform ({dist_blended:.4f}) "
                f"should be <= raw distance ({dist_raw:.4f})"
            )

    def test_group_stage_probs_match_simulation_formula(self):
        """Verify: group_prob = (1 - vf) * raw_prob + vf * (1/3) for each outcome."""
        from src.utils import load_config
        cfg = load_config()
        vf = cfg["simulation"]["tournament_variance_factor"]

        result = _pred("Spain", "Germany", neutral=True, stage="Group Stage")
        raw = result["metadata"]["raw_probabilities"]

        uniform = 1.0 / 3.0
        for key in ("home_win", "draw", "away_win"):
            expected = (1 - vf) * raw[key] + vf * uniform
            actual = result["probabilities"][key]
            assert abs(actual - expected) < 1e-6, (
                f"{key}: expected blended prob {expected:.6f} but got {actual:.6f}"
            )

    def test_variance_flag_in_metadata_for_group_stage(self):
        """Metadata must carry tournament_variance_applied=True for WC group stage."""
        result = _pred("England", "Brazil", neutral=True, stage="Group Stage")
        assert result["metadata"].get("tournament_variance_applied") is True

    def test_variance_not_applied_to_non_group_stage(self):
        """Knockout-round neutral predictions must NOT have variance compression."""
        result = _pred("France", "England", neutral=True, stage="Quarter-Final")
        assert result["metadata"].get("tournament_variance_applied") is False

    def test_variance_not_applied_to_non_neutral(self):
        """Non-neutral predictions (qualifiers) must NOT have variance compression."""
        result = _pred("Brazil", "Argentina", neutral=False, stage="Group Stage",
                       competition="FIFA World Cup Qualification")
        assert result["metadata"].get("tournament_variance_applied") is False

    def test_probabilities_still_sum_to_one_after_blending(self):
        """Blended probabilities must still sum to exactly 1.0."""
        result = _pred("Argentina", "Netherlands", neutral=True, stage="Group Stage")
        total = sum(result["probabilities"].values())
        assert abs(total - 1.0) < 1e-6, f"Probabilities sum to {total} after blending"

    def test_raw_probabilities_exposed_in_metadata(self):
        """Raw (pre-blend) probabilities must be available in metadata for comparison."""
        result = _pred("Portugal", "Uruguay", neutral=True, stage="Group Stage")
        raw = result["metadata"].get("raw_probabilities")
        assert raw is not None, "raw_probabilities missing from metadata"
        assert set(raw.keys()) == {"home_win", "draw", "away_win"}
        assert abs(sum(raw.values()) - 1.0) < 1e-6
