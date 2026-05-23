"""Tests for stale-while-revalidate background cache refresh (#164).

When the simulation/bracket cache is near expiry (>80% of TTL), a background
thread must rebuild it. The current request must get the stale-but-valid result
immediately — never block waiting for the refresh.
"""
from __future__ import annotations

import sys
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestBackgroundCacheRefresh:
    """Stale-while-revalidate: return cached value, refresh in background."""

    def setup_method(self):
        """Reset refresh state before each test."""
        import src.api.services as svc
        svc._refresh_in_progress = False

    def test_fresh_cache_does_not_trigger_refresh(self):
        """A cache that is brand new must not spawn a refresh thread."""
        import src.api.services as svc
        with patch("threading.Thread") as mock_thread:
            svc._maybe_trigger_background_refresh(cache_ts=time.time())
        mock_thread.assert_not_called()

    def test_old_cache_triggers_background_refresh(self):
        """A cache older than the refresh threshold must spawn a background thread."""
        import src.api.services as svc
        # Fake timestamp old enough to exceed the 80% threshold
        old_ts = time.time() - svc._CACHE_TTL_SECONDS * 0.85
        thread_started = []

        original_thread = threading.Thread
        def capturing_thread(*args, **kwargs):
            t = original_thread(*args, **kwargs)
            thread_started.append(t)
            return t

        with patch("threading.Thread", side_effect=capturing_thread):
            svc._maybe_trigger_background_refresh(cache_ts=old_ts)

        assert len(thread_started) == 1, "Expected exactly one background thread"

    def test_no_double_refresh_when_already_in_progress(self):
        """If a refresh is already running, a second call must not spawn another thread."""
        import src.api.services as svc
        svc._refresh_in_progress = True
        old_ts = time.time() - svc._CACHE_TTL_SECONDS * 0.85
        with patch("threading.Thread") as mock_thread:
            svc._maybe_trigger_background_refresh(cache_ts=old_ts)
        mock_thread.assert_not_called()

    def test_simulate_returns_stale_cache_while_refresh_runs(self):
        """simulate() must return the cached value immediately even when near-expired."""
        import src.api.services as svc
        stale_result = {"teams": [{"team": "Test"}], "modal_match_winners": {}}
        svc._simulation_cache = stale_result
        # Set timestamp to 85% of TTL — old but not expired
        svc._simulation_cache_ts = time.time() - svc._CACHE_TTL_SECONDS * 0.85

        with patch.object(svc, "_maybe_trigger_background_refresh") as mock_refresh:
            result = svc.simulate(n=100)

        assert result is stale_result, "simulate() should return stale cache without blocking"
        mock_refresh.assert_called_once()

    def test_do_background_refresh_updates_simulation_cache(self):
        """_do_background_refresh() must rebuild and update _simulation_cache."""
        import src.api.services as svc
        fresh_sim = {"teams": [{"team": "Fresh"}], "modal_match_winners": {}}
        fresh_bracket = {"rounds": [], "group_standings": {}, "champion": "Fresh"}

        with patch.object(svc, "_build_simulation", return_value=fresh_sim) as mock_sim, \
             patch.object(svc, "_build_bracket", return_value=fresh_bracket) as mock_bracket:
            svc._do_background_refresh()

        mock_sim.assert_called_once()
        mock_bracket.assert_called_once()

    def test_do_background_refresh_clears_in_progress_flag_on_error(self):
        """_refresh_in_progress must be reset to False even if the refresh crashes."""
        import src.api.services as svc
        svc._refresh_in_progress = True

        with patch.object(svc, "_build_simulation", side_effect=RuntimeError("boom")):
            svc._do_background_refresh()

        assert svc._refresh_in_progress is False, \
            "_refresh_in_progress must be False after an error"

    def test_predict_bracket_returns_stale_cache_while_refresh_runs(self):
        """predict_bracket() must return cached value immediately when near-expired."""
        import src.api.services as svc
        stale_bracket = {"rounds": [], "group_standings": {}, "champion": "Stale"}
        svc._bracket_cache = stale_bracket
        svc._bracket_cache_ts = time.time() - svc._CACHE_TTL_SECONDS * 0.85

        with patch.object(svc, "_maybe_trigger_background_refresh") as mock_refresh:
            result = svc.predict_bracket()

        assert result is stale_bracket, "predict_bracket() should return stale cache without blocking"
        mock_refresh.assert_called_once()
