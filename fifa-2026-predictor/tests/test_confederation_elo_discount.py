"""Tests for confederation opponent K-discount in Elo updates.

TDD: these tests are written BEFORE the implementation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.elo import EloConfig, update_ratings
from src.features.state_tracker import TeamStateTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(disc: dict | None = None) -> dict:
    base = {
        "features": {
            "form_window": 5,
            "elo_k_factor": 40.0,
            "elo_home_advantage": 100.0,
            "default_fifa_rank": 75,
            "recency_halflife_days": 180.0,
            "h2h_window": 10,
        }
    }
    if disc is not None:
        base["features"]["elo_opponent_conf_k_discount"] = disc
    return base


def _make_tracker(disc: dict | None = None) -> TeamStateTracker:
    return TeamStateTracker(_cfg(disc))


# ---------------------------------------------------------------------------
# update_ratings — confederation discount parameter
# ---------------------------------------------------------------------------

class TestUpdateRatingsConfDiscount:
    """Unit tests for the new away_confederation parameter in update_ratings."""

    def test_no_discount_when_both_confederations_absent(self):
        """Omitting both confederations gives same result as before (backward compat)."""
        cfg = EloConfig(k_factor=40.0, home_advantage=0.0)
        h1, a1 = update_ratings(1500, 1500, 1, 0, True, cfg)
        h2, a2 = update_ratings(1500, 1500, 1, 0, True, cfg,
                                 home_confederation="UEFA", away_confederation="UEFA",
                                 conf_k_discount={"UEFA": 1.0})
        assert abs(h1 - h2) < 0.001
        assert abs(a1 - a2) < 0.001

    def test_weak_away_confederation_reduces_home_elo_gain(self):
        """Winning against an AFC team (disc=0.85) earns less Elo than vs UEFA (disc=1.0)."""
        cfg = EloConfig(k_factor=40.0, home_advantage=0.0)
        disc = {"UEFA": 1.0, "AFC": 0.85}

        h_vs_afc, _ = update_ratings(1500, 1500, 1, 0, True, cfg,
                                      home_confederation="UEFA", away_confederation="AFC",
                                      conf_k_discount=disc)
        h_vs_uef, _ = update_ratings(1500, 1500, 1, 0, True, cfg,
                                      home_confederation="UEFA", away_confederation="UEFA",
                                      conf_k_discount=disc)

        # Winning against AFC earns less Elo than winning against UEFA
        assert h_vs_afc < h_vs_uef

    def test_discount_is_average_of_both_confederations(self):
        """Effective discount = (home_disc + away_disc) / 2."""
        cfg = EloConfig(k_factor=40.0, home_advantage=0.0)
        disc = {"UEFA": 1.0, "AFC": 0.80}

        h_new, _ = update_ratings(1500, 1500, 1, 0, True, cfg,
                                   home_confederation="UEFA", away_confederation="AFC",
                                   conf_k_discount=disc)
        # With equal ratings, home gain = K * avg_disc * 0.5
        expected_gain = 40.0 * ((1.0 + 0.80) / 2) * 0.5
        actual_gain = h_new - 1500
        assert abs(actual_gain - expected_gain) < 0.01

    def test_zero_sum_preserved(self):
        """Home gain + away loss must sum to zero regardless of discount."""
        cfg = EloConfig(k_factor=40.0, home_advantage=0.0)
        disc = {"UEFA": 1.0, "AFC": 0.85, "CAF": 0.90}

        for h_conf, a_conf in [("UEFA", "AFC"), ("CAF", "AFC"), ("UEFA", "UEFA")]:
            h_new, a_new = update_ratings(1600, 1500, 2, 1, True, cfg,
                                           home_confederation=h_conf,
                                           away_confederation=a_conf,
                                           conf_k_discount=disc)
            delta_h = h_new - 1600
            delta_a = a_new - 1500
            assert abs(delta_h + delta_a) < 0.001, (
                f"{h_conf} vs {a_conf}: zero-sum violated ({delta_h:.3f} + {delta_a:.3f})"
            )

    def test_draw_rate_discounted_correctly(self):
        """Draw result with confederation discount scales both sides equally."""
        cfg = EloConfig(k_factor=40.0, home_advantage=0.0)
        disc = {"UEFA": 1.0, "AFC": 0.80}

        h_new, a_new = update_ratings(1500, 1500, 0, 0, True, cfg,
                                       home_confederation="UEFA", away_confederation="AFC",
                                       conf_k_discount=disc)
        # Equal ratings + draw → no change (actual = expected = 0.5)
        assert abs(h_new - 1500) < 0.001
        assert abs(a_new - 1500) < 0.001

    def test_missing_confederation_falls_back_to_1_0(self):
        """Unknown confederation not in disc dict defaults to 1.0 (no discount)."""
        cfg = EloConfig(k_factor=40.0, home_advantage=0.0)
        disc = {"UEFA": 1.0}  # AFC not present

        # Should not raise; missing keys treated as 1.0
        h_with_missing, _ = update_ratings(1500, 1500, 1, 0, True, cfg,
                                            home_confederation="UEFA",
                                            away_confederation="AFC",
                                            conf_k_discount=disc)
        # avg = (1.0 + 1.0) / 2 = 1.0 — no discount applied
        h_no_disc, _ = update_ratings(1500, 1500, 1, 0, True, cfg,
                                       home_confederation="UEFA",
                                       away_confederation="UEFA",
                                       conf_k_discount={"UEFA": 1.0})
        assert abs(h_with_missing - h_no_disc) < 0.001


# ---------------------------------------------------------------------------
# TeamStateTracker — picks up discount from config
# ---------------------------------------------------------------------------

class TestTrackerConfDiscount:
    """Integration: tracker reads conf discount from config and applies it."""

    def test_winning_against_weak_confederation_gives_less_elo(self):
        """A team beating an OFC opponent earns less Elo than beating a UEFA opponent."""
        disc = {"UEFA": 1.0, "OFC": 0.65}

        t_vs_ofc = _make_tracker(disc)
        t_vs_uef = _make_tracker(disc)

        # Patch confederation so tracker can look it up
        # We use update() directly with home_confederation / away_confederation
        # injected via a minimal match row
        for tracker, away_conf in [(t_vs_ofc, "OFC"), (t_vs_uef, "UEFA")]:
            tracker.update(
                home_team="TeamA",
                away_team="TeamB",
                home_goals=1,
                away_goals=0,
                neutral=True,
                date=pd.Timestamp("2024-06-01"),
                competition="FIFA World Cup",
                home_confederation="UEFA",
                away_confederation=away_conf,
            )

        elo_vs_ofc = t_vs_ofc.elo("TeamA")
        elo_vs_uef = t_vs_uef.elo("TeamA")
        assert elo_vs_ofc < elo_vs_uef, (
            f"Expected beating OFC ({elo_vs_ofc:.1f}) to earn less Elo "
            f"than beating UEFA ({elo_vs_uef:.1f})"
        )

    def test_no_discount_config_behaves_as_before(self):
        """When elo_opponent_conf_k_discount is absent, behavior is unchanged."""
        t_with = _make_tracker({"UEFA": 1.0, "AFC": 1.0})  # all 1.0 = no discount
        t_without = _make_tracker(None)  # key absent

        for tracker in [t_with, t_without]:
            tracker.update(
                home_team="A", away_team="B",
                home_goals=2, away_goals=0,
                neutral=True,
                date=pd.Timestamp("2024-06-01"),
                competition="Friendly",
                home_confederation="UEFA",
                away_confederation="AFC",
            )

        assert abs(t_with.elo("A") - t_without.elo("A")) < 0.001

    def test_iran_elo_lower_than_egypt_after_typical_schedules(self):
        """After simulating typical schedules, Iran should accumulate less Elo
        than Egypt because Egypt plays harder cross-confederation opponents."""
        disc = {"UEFA": 1.0, "CONMEBOL": 1.0, "CAF": 0.90, "AFC": 0.85, "CONCACAF": 0.80, "OFC": 0.65}

        t_iran = _make_tracker(disc)
        t_egypt = _make_tracker(disc)

        # Iran: 10 wins vs AFC opponents (simulates WC qualification dominance)
        for i in range(10):
            t_iran.update(
                home_team="IR Iran", away_team=f"AFC_Opp_{i}",
                home_goals=2, away_goals=0, neutral=False,
                date=pd.Timestamp(f"2022-0{(i % 9) + 1}-01"),
                competition="FIFA World Cup Qualification",
                home_confederation="AFC",
                away_confederation="AFC",
            )

        # Egypt: 10 wins vs CAF opponents (slightly harder confederation)
        for i in range(10):
            t_egypt.update(
                home_team="Egypt", away_team=f"CAF_Opp_{i}",
                home_goals=2, away_goals=0, neutral=False,
                date=pd.Timestamp(f"2022-0{(i % 9) + 1}-01"),
                competition="Africa Cup of Nations",
                home_confederation="CAF",
                away_confederation="CAF",
            )

        # Both start from the same base; after same number of identical-scoreline
        # wins, Iran should have gained LESS Elo than Egypt because AFC discount < CAF discount
        iran_gain = t_iran.elo("IR Iran") - 1500
        egypt_gain = t_egypt.elo("Egypt") - 1500
        assert iran_gain < egypt_gain, (
            f"Iran gain ({iran_gain:.1f}) should be less than Egypt gain ({egypt_gain:.1f})"
        )
