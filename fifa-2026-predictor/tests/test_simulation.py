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
