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


def _make_stub_tracker():
    return MagicMock()


def _make_stub_prob_cache():
    """Return a fixed prob_cache for all 48×47 pairs (60% home win)."""
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    all_teams = [t for g in WC2026_GROUPS for t in g["teams"]]
    cache = {}
    for home in all_teams:
        for away in all_teams:
            if home != away:
                cache[(home, away)] = {"home_win": 0.60, "draw": 0.20, "away_win": 0.20}
    return cache


def test_simulate_once_returns_all_48_teams():
    from src.simulation.tournament import simulate_once
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    all_teams = {t for g in WC2026_GROUPS for t in g["teams"]}
    rng = np.random.default_rng(42)
    stage_results, _ = simulate_once(
        _make_stub_tracker(), None, {}, rng, prob_cache=_make_stub_prob_cache()
    )
    assert set(stage_results.keys()) == all_teams


def test_simulate_once_returns_valid_stages():
    from src.simulation.tournament import simulate_once
    valid_stages = {"group_exit", "round_of_32", "round_of_16", "quarter_final", "semi_final", "third_place", "final", "champion"}
    rng = np.random.default_rng(42)
    stage_results, _ = simulate_once(
        _make_stub_tracker(), None, {}, rng, prob_cache=_make_stub_prob_cache()
    )
    for team, stage in stage_results.items():
        assert stage in valid_stages, f"{team} has invalid stage: {stage}"


def test_simulate_once_exactly_one_champion():
    from src.simulation.tournament import simulate_once
    rng = np.random.default_rng(42)
    stage_results, _ = simulate_once(
        _make_stub_tracker(), None, {}, rng, prob_cache=_make_stub_prob_cache()
    )
    champions = [t for t, s in stage_results.items() if s == "champion"]
    assert len(champions) == 1


def test_simulate_once_returns_match_winners():
    from src.simulation.tournament import simulate_once
    rng = np.random.default_rng(42)
    stage_results, match_winners = simulate_once(
        _make_stub_tracker(), None, {}, rng, prob_cache=_make_stub_prob_cache()
    )
    assert isinstance(stage_results, dict)
    assert isinstance(match_winners, dict)
    assert 103 in match_winners, "Final winner (slot 103) must be tracked"
    assert 104 in match_winners, "3rd-place winner (slot 104) must be tracked"
    assert all(isinstance(v, str) for v in match_winners.values())


def test_run_simulation_probabilities_sum_to_one_per_team():
    from src.simulation.tournament import run_simulation
    with patch("src.simulation.tournament.precompute_all_probabilities", return_value=_make_stub_prob_cache()):
        results = run_simulation(_make_stub_tracker(), None, {}, n=50)
    for team_result in results["teams"]:
        total = (
            team_result["group_exit"] + team_result["round_of_32"] +
            team_result["round_of_16"] + team_result["quarter_final"] +
            team_result["semi_final"] + team_result["third_place"] +
            team_result["final"] + team_result["champion"]
        )
        assert abs(total - 1.0) < 0.01, f"{team_result['team']} probs sum to {total}"


def test_run_simulation_includes_modal_match_winners():
    from src.simulation.tournament import run_simulation
    with patch("src.simulation.tournament.precompute_all_probabilities",
               return_value=_make_stub_prob_cache()):
        result = run_simulation(_make_stub_tracker(), None, {}, n=50)
    assert "modal_match_winners" in result, "modal_match_winners key missing from simulation output"
    modal = result["modal_match_winners"]
    assert 103 in modal, "Final winner slot (103) must be in modal_match_winners"
    for slot, winner in modal.items():
        assert isinstance(winner, str), f"Slot {slot} winner must be a string"


def test_predict_bracket_modal_returns_correct_structure():
    from src.simulation.tournament import predict_bracket_modal
    from src.simulation.wc2026_bracket import WC2026_GROUPS
    all_teams = {t for g in WC2026_GROUPS for t in g["teams"]}
    prob_cache = _make_stub_prob_cache()
    result = predict_bracket_modal({}, prob_cache)
    assert "rounds" in result
    assert "champion" in result
    assert "group_standings" in result
    assert result["champion"] in all_teams
    round_names = [r["round"] for r in result["rounds"]]
    assert "Round of 32" in round_names
    assert "Round of 16" in round_names
    assert "Quarter-Final" in round_names
    assert "Semi-Final" in round_names
    assert "Final" in round_names


def test_predict_bracket_modal_uses_modal_champion():
    from src.simulation.tournament import predict_bracket_modal, run_simulation
    prob_cache = _make_stub_prob_cache()
    with patch("src.simulation.tournament.precompute_all_probabilities",
               return_value=prob_cache):
        sim = run_simulation(_make_stub_tracker(), None, {}, n=200)
    modal = sim["modal_match_winners"]
    result = predict_bracket_modal(modal, prob_cache)
    # When modal slot 103 is provided AND that team is one of the two finalists
    # produced by the modal bracket path, the bracket champion must match it.
    if 103 in modal:
        final_match = result["rounds"][-1]["matches"][0]
        finalist1, finalist2 = final_match["team1"], final_match["team2"]
        if modal[103] in (finalist1, finalist2):
            assert result["champion"] == modal[103], (
                f"Bracket champion {result['champion']!r} != modal final winner {modal[103]!r}"
            )
        else:
            # modal[103] is an impossible finalist given earlier modal picks — fallback used
            assert result["champion"] in (finalist1, finalist2)
