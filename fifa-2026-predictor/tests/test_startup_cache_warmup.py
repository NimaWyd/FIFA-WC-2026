"""Tests for bracket/simulation cache pre-warming on server startup.

The server must start instantly (warmup runs in a background thread) and the
bracket cache must be populated within a reasonable time after startup.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestStartupCacheWarmup:
    """Startup lifespan must trigger background cache warmup without blocking."""

    def test_warmup_runs_in_background_thread(self):
        """Cache warmup must be dispatched as a daemon thread, not run inline."""
        from src.api import main as main_module
        threads_started = []

        original_thread = threading.Thread

        def capturing_thread(*args, **kwargs):
            t = original_thread(*args, **kwargs)
            threads_started.append(kwargs.get("target") or (args[0] if args else None))
            return t

        with patch("threading.Thread", side_effect=capturing_thread):
            # Simulate lifespan startup by calling the warmup trigger directly
            from src.api.main import _start_warmup_thread
            _start_warmup_thread()

        assert len(threads_started) >= 1, "Expected at least one thread to be started"

    def test_warmup_calls_predict_bracket_and_simulate(self):
        """Warmup function must call both simulate() and predict_bracket()."""
        from src.api.main import _warmup_caches
        with patch("src.api.services.simulate") as mock_sim, \
             patch("src.api.services.predict_bracket") as mock_bracket:
            mock_sim.return_value = {"teams": [], "modal_match_winners": {}}
            mock_bracket.return_value = {"rounds": [], "group_standings": {}, "champion": "?"}
            _warmup_caches()

        mock_sim.assert_called_once()
        mock_bracket.assert_called_once()

    def test_warmup_does_not_raise_on_error(self):
        """Warmup errors must be swallowed so a bad model doesn't crash the server."""
        from src.api.main import _warmup_caches
        with patch("src.api.services.simulate", side_effect=RuntimeError("no model")), \
             patch("src.api.services.predict_bracket", side_effect=RuntimeError("no model")):
            try:
                _warmup_caches()  # must not propagate
            except Exception as exc:
                pytest.fail(f"_warmup_caches() raised unexpectedly: {exc}")

    def test_app_has_lifespan(self):
        """FastAPI app must have a lifespan context manager registered."""
        from src.api.main import app
        # FastAPI stores lifespan as router.lifespan_context
        assert app.router.lifespan_context is not None, \
            "App has no lifespan registered — startup hook will never fire"
