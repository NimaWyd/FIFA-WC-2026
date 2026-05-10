"""Tests for WC2026 tournament simulation (issue #22)."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_bracket_has_12_groups():
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    assert len(WC2026_GROUPS) == 12


def test_each_group_has_4_teams_and_6_matches():
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    for group in WC2026_GROUPS:
        assert len(group["teams"]) == 4, f"Group {group['id']} has wrong team count"
        assert len(group["matches"]) == 6, f"Group {group['id']} has wrong match count"


def test_bracket_has_48_unique_teams():
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    all_teams = [t for g in WC2026_GROUPS for t in g["teams"]]
    assert len(all_teams) == 48
    assert len(set(all_teams)) == 48, "Duplicate teams found"


def test_r32_has_16_matchups():
    from src.simulation.wc2026_bracket import WC2026_R32
    assert len(WC2026_R32) == 16


def test_r32_has_8_third_place_slots():
    from src.simulation.wc2026_bracket import WC2026_R32
    third_slots = [m for m in WC2026_R32 if m["slot1_type"] == "3rd" or m["slot2_type"] == "3rd"]
    assert len(third_slots) == 8


import numpy as np
from unittest.mock import MagicMock, patch


def _make_stub_model():
    """Stub model that always returns 60% home / 20% draw / 20% away."""
    model = MagicMock()
    model.predict_proba.return_value = np.array([[0.20, 0.20, 0.60]])
    clf = MagicMock()
    clf.classes_ = np.array([0, 1, 2])
    model.named_steps = {"classifier": clf}
    return model


def _make_stub_tracker():
    return MagicMock()


_DUMMY_FEATURE_ROW = {"elo_diff_home_away": 0.0, "home_form": 1.5, "away_form": 1.5}


def test_simulate_once_returns_all_48_teams():
    from src.simulation.tournament import simulate_once
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    all_teams = {t for g in WC2026_GROUPS for t in g["teams"]}
    rng = np.random.default_rng(42)
    with patch("src.simulation.tournament.build_match_row", return_value=_DUMMY_FEATURE_ROW):
        result = simulate_once(_make_stub_tracker(), _make_stub_model(), {}, rng)
    assert set(result.keys()) == all_teams


def test_simulate_once_returns_valid_stages():
    from src.simulation.tournament import simulate_once
    valid_stages = {"group_exit", "round_of_32", "quarter_final", "semi_final", "final", "champion"}
    rng = np.random.default_rng(42)
    with patch("src.simulation.tournament.build_match_row", return_value=_DUMMY_FEATURE_ROW):
        result = simulate_once(_make_stub_tracker(), _make_stub_model(), {}, rng)
    for team, stage in result.items():
        assert stage in valid_stages, f"{team} has invalid stage: {stage}"


def test_simulate_once_exactly_one_champion():
    from src.simulation.tournament import simulate_once
    rng = np.random.default_rng(42)
    with patch("src.simulation.tournament.build_match_row", return_value=_DUMMY_FEATURE_ROW):
        result = simulate_once(_make_stub_tracker(), _make_stub_model(), {}, rng)
    champions = [t for t, s in result.items() if s == "champion"]
    assert len(champions) == 1


def test_run_simulation_probabilities_sum_to_one_per_team():
    from src.simulation.tournament import run_simulation
    with patch("src.simulation.tournament.build_match_row", return_value=_DUMMY_FEATURE_ROW):
        results = run_simulation(_make_stub_tracker(), _make_stub_model(), {}, n=50)
    for team_result in results["teams"]:
        total = (
            team_result["group_exit"] + team_result["round_of_32"] +
            team_result["quarter_final"] + team_result["semi_final"] +
            team_result["final"] + team_result["champion"]
        )
        assert abs(total - 1.0) < 0.01, f"{team_result['team']} probs sum to {total}"
