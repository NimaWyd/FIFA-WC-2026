"""Tests for RankingLookup (#38) and XGDataLoader (#37) fallback behaviour."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data.load_rankings import RankingLookup
from src.data.load_xg import XGDataLoader, get_xg_features


# ---------------------------------------------------------------------------
# Issue #38 — RankingLookup gracefully handles a missing CSV
# ---------------------------------------------------------------------------

class TestRankingLookupMissingCSV:
    def test_has_data_false_when_file_missing(self, tmp_path):
        lookup = RankingLookup.from_csv(tmp_path / "nonexistent.csv")
        assert not lookup.has_data

    def test_falls_back_to_static_rank_when_file_missing(self, tmp_path):
        lookup = RankingLookup.from_csv(tmp_path / "nonexistent.csv")
        # Brazil's static 2025 rank is 5; the fallback must return a valid integer
        rank = lookup.get_rank("Brazil", pd.Timestamp("2026-06-15"))
        assert isinstance(rank, int)
        assert rank > 0

    def test_has_coverage_false_when_no_data(self, tmp_path):
        lookup = RankingLookup.from_csv(tmp_path / "nonexistent.csv")
        assert not lookup.has_coverage("France")

    def test_returns_static_rank_not_default_sentinel(self, tmp_path):
        lookup = RankingLookup.from_csv(tmp_path / "nonexistent.csv")
        # Default sentinel is 75; Brazil's static rank should differ (it's 5)
        rank = lookup.get_rank("Brazil", pd.Timestamp("2026-06-15"))
        assert rank != 75, "Expected static rank, not the default sentinel 75"

    def test_valid_csv_loads_correctly(self, tmp_path):
        csv = tmp_path / "rankings.csv"
        csv.write_text("date,team,rank\n2022-10-01,France,3\n2023-10-01,France,2\n")
        lookup = RankingLookup.from_csv(csv)
        assert lookup.has_data
        assert lookup.has_coverage("France")
        rank = lookup.get_rank("France", pd.Timestamp("2023-01-01"))
        assert rank == 3  # most recent rank strictly before 2023-01-01


# ---------------------------------------------------------------------------
# Issue #37 — XGDataLoader fallback behaviour
# ---------------------------------------------------------------------------

class TestXGDataLoaderMissingCSV:
    def test_has_data_false_when_file_missing(self, tmp_path):
        loader = XGDataLoader.from_csv(tmp_path / "nonexistent.csv")
        assert not loader.has_data

    def test_get_match_xg_returns_none_tuple_when_no_data(self, tmp_path):
        loader = XGDataLoader.from_csv(tmp_path / "nonexistent.csv")
        result = loader.get_match_xg("Brazil", "Argentina", pd.Timestamp("2026-06-15"))
        assert result == (None, None)

    def test_get_xg_features_uses_proxy_when_no_loader(self):
        features = get_xg_features(
            loader=None,
            home_team="Brazil",
            away_team="Argentina",
            match_date=pd.Timestamp("2026-06-15"),
            home_attack_rw5=1.8,
            away_attack_rw5=1.5,
        )
        assert features["xg_source"] == "raw_goal_proxy"
        assert features["home_xg_proxy"] == pytest.approx(1.8)
        assert features["away_xg_proxy"] == pytest.approx(1.5)
        assert features["xg_diff_proxy"] == pytest.approx(0.3)

    def test_get_xg_features_uses_proxy_when_loader_has_no_data(self, tmp_path):
        loader = XGDataLoader.from_csv(tmp_path / "nonexistent.csv")
        features = get_xg_features(
            loader=loader,
            home_team="Brazil",
            away_team="Argentina",
            match_date=pd.Timestamp("2026-06-15"),
            home_attack_rw5=2.0,
            away_attack_rw5=1.2,
        )
        assert features["xg_source"] == "raw_goal_proxy"
        assert features["home_xg_proxy"] == pytest.approx(2.0)


class TestXGDataLoaderWithData:
    @pytest.fixture()
    def loader(self, tmp_path):
        csv = tmp_path / "xg.csv"
        csv.write_text(
            "date,home_team,away_team,home_xg,away_xg\n"
            "2022-11-20,France,Australia,2.1,0.5\n"
            "2022-11-25,Brazil,Serbia,2.8,0.4\n"
        )
        return XGDataLoader.from_csv(csv)

    def test_has_data_true(self, loader):
        assert loader.has_data

    def test_get_match_xg_returns_values(self, loader):
        hxg, axg = loader.get_match_xg("France", "Australia", pd.Timestamp("2022-11-20"))
        assert hxg == pytest.approx(2.1)
        assert axg == pytest.approx(0.5)

    def test_get_match_xg_returns_none_for_unknown_match(self, loader):
        result = loader.get_match_xg("Germany", "Spain", pd.Timestamp("2022-11-20"))
        assert result == (None, None)

    def test_get_xg_features_uses_real_xg_when_available(self, loader):
        features = get_xg_features(
            loader=loader,
            home_team="France",
            away_team="Australia",
            match_date=pd.Timestamp("2022-11-20"),
            home_attack_rw5=1.0,
            away_attack_rw5=0.8,
        )
        assert features["xg_source"] == "real_xg"
        assert features["home_xg_proxy"] == pytest.approx(2.1)
        assert features["away_xg_proxy"] == pytest.approx(0.5)
        assert features["xg_diff_proxy"] == pytest.approx(1.6)

    def test_get_xg_features_falls_back_for_unindexed_match(self, loader):
        features = get_xg_features(
            loader=loader,
            home_team="Germany",
            away_team="Spain",
            match_date=pd.Timestamp("2022-11-20"),
            home_attack_rw5=1.3,
            away_attack_rw5=1.7,
        )
        assert features["xg_source"] == "raw_goal_proxy"
        assert features["home_xg_proxy"] == pytest.approx(1.3)
