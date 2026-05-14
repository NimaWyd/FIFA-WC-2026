"""Tests for live match updates (#79) and squad strength features (#78)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# Issue #79 — Live match updates
# ---------------------------------------------------------------------------

class TestGetLastUpdateDate:
    def test_returns_max_date_from_csv(self, tmp_path):
        from src.data.update_live_matches import get_last_update_date
        csv = tmp_path / "matches.csv"
        csv.write_text("date,home_team,away_team\n2024-03-01,Brazil,Argentina\n2024-05-15,France,Germany\n")
        assert get_last_update_date(csv) == "2024-05-15"

    def test_returns_fallback_when_file_missing(self, tmp_path):
        from src.data.update_live_matches import get_last_update_date
        assert get_last_update_date(tmp_path / "nonexistent.csv") == "2020-01-01"

    def test_returns_fallback_when_csv_empty(self, tmp_path):
        from src.data.update_live_matches import get_last_update_date
        csv = tmp_path / "matches.csv"
        csv.write_text("date,home_team,away_team\n")
        assert get_last_update_date(csv) == "2020-01-01"


class TestFetchAndAppendNewResults:
    def _make_api_response(self) -> pd.DataFrame:
        return pd.DataFrame({
            "date": ["2024-06-01", "2024-06-02"],
            "home_team": ["Brazil", "France"],
            "away_team": ["Argentina", "Germany"],
            "home_score": [2.0, 1.0],
            "away_score": [1.0, 1.0],
            "competition": ["Friendly", "Friendly"],
            "neutral": [False, False],
        })

    def test_appends_new_rows_to_existing_csv(self, tmp_path):
        from src.data.update_live_matches import fetch_and_append_new_results
        existing = tmp_path / "matches.csv"
        existing.write_text(
            "date,home_team,away_team,home_score,away_score,competition,neutral\n"
            "2024-05-01,Spain,Portugal,1,0,Friendly,False\n"
        )
        api_df = self._make_api_response()
        with patch("src.data.update_live_matches.fetch_international_matches_from_api", return_value=api_df):
            n = fetch_and_append_new_results(existing, date_from="2024-05-01")
        result = pd.read_csv(existing)
        assert n == 2
        assert len(result) == 3

    def test_deduplicates_existing_matches(self, tmp_path):
        from src.data.update_live_matches import fetch_and_append_new_results
        existing = tmp_path / "matches.csv"
        existing.write_text(
            "date,home_team,away_team,home_score,away_score,competition,neutral\n"
            "2024-06-01,Brazil,Argentina,2,1,Friendly,False\n"
        )
        api_df = self._make_api_response()
        with patch("src.data.update_live_matches.fetch_international_matches_from_api", return_value=api_df):
            n = fetch_and_append_new_results(existing, date_from="2024-05-01")
        result = pd.read_csv(existing)
        assert n == 1          # Only France vs Germany (Brazil vs Argentina already present)
        assert len(result) == 2

    def test_returns_zero_when_no_new_matches(self, tmp_path):
        from src.data.update_live_matches import fetch_and_append_new_results
        existing = tmp_path / "matches.csv"
        existing.write_text(
            "date,home_team,away_team,home_score,away_score,competition,neutral\n"
            "2024-06-01,Brazil,Argentina,2,1,Friendly,False\n"
            "2024-06-02,France,Germany,1,1,Friendly,False\n"
        )
        api_df = self._make_api_response()
        with patch("src.data.update_live_matches.fetch_international_matches_from_api", return_value=api_df):
            n = fetch_and_append_new_results(existing, date_from="2024-05-01")
        assert n == 0

    def test_skips_matches_without_scores(self, tmp_path):
        from src.data.update_live_matches import fetch_and_append_new_results
        existing = tmp_path / "matches.csv"
        existing.write_text("date,home_team,away_team,home_score,away_score,competition,neutral\n")
        api_df = pd.DataFrame({
            "date": ["2024-06-01", "2024-06-02"],
            "home_team": ["Brazil", "France"],
            "away_team": ["Argentina", "Germany"],
            "home_score": [2.0, None],
            "away_score": [1.0, None],
            "competition": ["Friendly", "Friendly"],
            "neutral": [False, False],
        })
        with patch("src.data.update_live_matches.fetch_international_matches_from_api", return_value=api_df):
            n = fetch_and_append_new_results(existing, date_from="2020-01-01")
        assert n == 1
