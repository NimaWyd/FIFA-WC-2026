"""Tests for group standings computed from individual predict() calls (#163).

Group standings in the bracket prediction must be consistent with what individual
match predictions show — using expected points from predict() rather than from the
simulation's probability cache (which uses a different feature-building code path).
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


# ---------------------------------------------------------------------------
# Unit tests for the new helper (no model needed)
# ---------------------------------------------------------------------------

class TestBuildGroupStandingsFromPredict:
    """build_group_standings_from_predict() must rank teams by expected points."""

    def _fake_predict(self, probs: dict) -> object:
        """Return a mock predict function that returns fixed probabilities."""
        def _pred(home_team, away_team, **kwargs):
            key = (home_team, away_team)
            p = probs.get(key, {"home_win": 0.333, "draw": 0.334, "away_win": 0.333})
            return {"probabilities": p}
        return _pred

    def test_stronger_team_ranks_first(self):
        """Team with higher win probability against all opponents should rank 1st."""
        from src.api.services import build_group_standings_from_predict
        # A dominates everything — always 80% win prob
        probs = {
            ("A", "B"): {"home_win": 0.80, "draw": 0.10, "away_win": 0.10},
            ("A", "C"): {"home_win": 0.80, "draw": 0.10, "away_win": 0.10},
            ("B", "A"): {"home_win": 0.10, "draw": 0.10, "away_win": 0.80},
            ("B", "C"): {"home_win": 0.50, "draw": 0.25, "away_win": 0.25},
            ("C", "A"): {"home_win": 0.10, "draw": 0.10, "away_win": 0.80},
            ("C", "B"): {"home_win": 0.25, "draw": 0.25, "away_win": 0.50},
        }
        fake_group = {
            "id": "X",
            "teams": ["A", "B", "C"],
            "matches": [
                {"home": "A", "away": "B"},
                {"home": "A", "away": "C"},
                {"home": "B", "away": "C"},
            ],
        }
        standings, _ = build_group_standings_from_predict(
            [fake_group], self._fake_predict(probs), match_date="2026-06-20"
        )
        assert standings["X"][0] == "A", f"Expected A first, got {standings['X']}"

    def test_expected_points_formula_correct(self):
        """Expected points = sum(3*P(win) + 1*P(draw)) across all matches."""
        from src.api.services import build_group_standings_from_predict
        # Equal teams, one draw specialist
        probs = {
            ("A", "B"): {"home_win": 0.40, "draw": 0.30, "away_win": 0.30},
            ("B", "A"): {"home_win": 0.30, "draw": 0.30, "away_win": 0.40},
            ("A", "C"): {"home_win": 0.40, "draw": 0.20, "away_win": 0.40},
            ("C", "A"): {"home_win": 0.40, "draw": 0.20, "away_win": 0.40},
            ("B", "C"): {"home_win": 0.40, "draw": 0.20, "away_win": 0.40},
            ("C", "B"): {"home_win": 0.40, "draw": 0.20, "away_win": 0.40},
        }
        fake_group = {
            "id": "Y",
            "teams": ["A", "B", "C"],
            "matches": [
                {"home": "A", "away": "B"},
                {"home": "A", "away": "C"},
                {"home": "B", "away": "C"},
            ],
        }
        _, exp_pts = build_group_standings_from_predict(
            [fake_group], self._fake_predict(probs), match_date="2026-06-20"
        )
        # A's expected points: vs B (3*0.40+0.30=1.50) + vs C (avg of A@home and A@away)
        # A@home vs B: 3*0.40 + 0.30 = 1.50
        # A@away vs C (from B-C match perspective, avg): (3*0.40+0.20 + 3*0.40+0.20)/2 = 1.40
        # Full A expected pts: from A vs B + from A vs C
        # vs B: neutral avg of (A,B) and (B,A): p_A_wins = avg(0.40, 0.40)=0.40, draw avg=0.30 => 3*0.40+0.30=1.50
        # vs C: neutral avg of (A,C) and (C,A): p_A_wins = avg(0.40, 0.40)=0.40, draw avg=0.20 => 3*0.40+0.20=1.40
        # Total A = 2.90
        assert abs(exp_pts["A"] - 2.90) < 0.01, f"A expected pts {exp_pts['A']:.2f} != 2.90"

    def test_returns_all_groups(self):
        """build_group_standings_from_predict returns standings for every group passed in."""
        from src.api.services import build_group_standings_from_predict
        groups = [
            {"id": "G1", "teams": ["T1", "T2"], "matches": [{"home": "T1", "away": "T2"}]},
            {"id": "G2", "teams": ["T3", "T4"], "matches": [{"home": "T3", "away": "T4"}]},
        ]
        probs = {
            ("T1", "T2"): {"home_win": 0.6, "draw": 0.2, "away_win": 0.2},
            ("T2", "T1"): {"home_win": 0.2, "draw": 0.2, "away_win": 0.6},
            ("T3", "T4"): {"home_win": 0.5, "draw": 0.3, "away_win": 0.2},
            ("T4", "T3"): {"home_win": 0.2, "draw": 0.3, "away_win": 0.5},
        }
        standings, _ = build_group_standings_from_predict(
            groups, self._fake_predict(probs), match_date="2026-06-20"
        )
        assert set(standings.keys()) == {"G1", "G2"}


# ---------------------------------------------------------------------------
# Integration tests — bracket uses predict() for group standings
# ---------------------------------------------------------------------------

@_integration_skip
class TestBracketGroupStandingsConsistency:
    """Bracket group standings must match individual predict() expected-points ranking."""

    def test_norway_ranks_above_senegal_in_group_i(self):
        """Norway (Elo 2019, slight H2H edge) must be ranked above Senegal in Group I."""
        from src.api.services import predict_bracket
        b = predict_bracket()
        gs = b["group_standings"]
        group_i = gs["I"]
        norway_pos = group_i.index("Norway")
        senegal_pos = group_i.index("Senegal")
        assert norway_pos < senegal_pos, (
            f"Norway should rank above Senegal in Group I but got: {group_i}"
        )

    def test_france_tops_group_i(self):
        """France (strongest team in Group I) must be ranked 1st."""
        from src.api.services import predict_bracket
        b = predict_bracket()
        assert b["group_standings"]["I"][0] == "France", (
            f"Expected France 1st in Group I, got: {b['group_standings']['I']}"
        )

    def test_all_groups_have_four_teams(self):
        """Every group in bracket standings must list exactly 4 teams."""
        from src.api.services import predict_bracket
        b = predict_bracket()
        for gid, teams in b["group_standings"].items():
            assert len(teams) == 4, f"Group {gid} has {len(teams)} teams, expected 4"

    def test_bracket_champion_is_top_tier_team(self):
        """Predicted champion should be a top-tier nation."""
        from src.api.services import predict_bracket
        b = predict_bracket()
        top_tier = {"Argentina", "France", "Spain", "England", "Brazil", "Portugal",
                    "Germany", "Netherlands"}
        assert b["champion"] in top_tier, (
            f"Champion {b['champion']} is not a top-tier team — check group standings"
        )
