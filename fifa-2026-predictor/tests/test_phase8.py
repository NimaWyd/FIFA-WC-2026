"""Tests for issues #92, #70, #86."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.competition_weights import normalize_tournament_stage, get_stage_importance


class TestStageNormalization:
    def test_quarterfinals_plural_normalizes(self):
        # Before fix: returned "quarterfinals" (not in STAGE_IMPORTANCE → 0)
        assert normalize_tournament_stage("Quarterfinals") == "quarterfinal"

    def test_quarterfinals_plural_has_nonzero_importance(self):
        assert get_stage_importance("Quarterfinals") == 5
