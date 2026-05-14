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


# ---------------------------------------------------------------------------
# Issue #79 — Cache invalidation + /refresh endpoint
# ---------------------------------------------------------------------------

class TestInvalidateDataCaches:
    def test_clears_history_and_simulation_cache(self):
        """invalidate_data_caches resets both module-level singletons."""
        import src.api.services as svc
        svc._history_df = "not_none"
        svc._simulation_cache = {"some": "data"}

        from src.api.services import invalidate_data_caches
        invalidate_data_caches()

        assert svc._history_df is None
        assert svc._simulation_cache is None


class TestRefreshEndpoint:
    def test_refresh_returns_ok_status(self):
        """POST /api/v1/refresh returns {status: ok, new_matches_added: N}."""
        try:
            from fastapi.testclient import TestClient
            from src.api.main import app
        except ImportError:
            import pytest
            pytest.skip("FastAPI or httpx not installed")

        from unittest.mock import patch
        client = TestClient(app)
        with patch("src.data.update_live_matches.fetch_and_append_new_results", return_value=3):
            resp = client.post("/api/v1/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["new_matches_added"] == 3


# ---------------------------------------------------------------------------
# Issue #78 — Squad ratings seed script
# ---------------------------------------------------------------------------

class TestSeedSquadRatings:
    def test_generates_csv_with_required_columns(self):
        from src.data.seed_squad_ratings import generate_squad_ratings, SQUAD_RATING_COLUMNS
        df = generate_squad_ratings()
        for col in SQUAD_RATING_COLUMNS:
            assert col in df.columns, f"Missing column: {col}"

    def test_all_teams_have_ratings(self):
        from src.data.seed_squad_ratings import generate_squad_ratings
        df = generate_squad_ratings()
        assert len(df) > 0
        assert df["squad_avg_rating"].between(50.0, 90.0).all(), \
            "Ratings should be in realistic range"

    def test_higher_rank_means_lower_rating(self):
        from src.data.seed_squad_ratings import generate_squad_ratings
        df = generate_squad_ratings().set_index("team")
        from src.data.team_identity import CANONICAL_TEAMS
        ranked = [(t, m.get("fifa_rank_2025", 999)) for t, m in CANONICAL_TEAMS.items()
                  if m.get("fifa_rank_2025") is not None]
        ranked.sort(key=lambda x: x[1])
        top_team, top_rank = ranked[0]
        bottom_team, bottom_rank = ranked[-1]
        if top_team in df.index and bottom_team in df.index:
            assert df.loc[top_team, "squad_avg_rating"] > df.loc[bottom_team, "squad_avg_rating"], \
                f"{top_team}(rank {top_rank}) should have higher rating than {bottom_team}(rank {bottom_rank})"

    def test_top_player_rating_above_squad_avg(self):
        from src.data.seed_squad_ratings import generate_squad_ratings
        df = generate_squad_ratings()
        assert (df["top_player_rating"] >= df["squad_avg_rating"]).all(), \
            "Top player rating should be >= squad average"
