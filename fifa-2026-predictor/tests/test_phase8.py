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


import pandas as pd
from src.data.load_matches import _apply_stage_lookup


class TestApplyStageLookup:
    def _base_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "date": pd.to_datetime(["2018-07-15", "2022-12-18", "2024-03-01"]),
            "home_team": ["France", "Argentina", "Germany"],
            "away_team": ["Croatia", "France", "Brazil"],
            "tournament_stage": ["Unknown", "Unknown", "Unknown"],
        })

    def test_lookup_fills_unknown_wc_stages(self):
        df = self._base_df()
        result = _apply_stage_lookup(df)
        assert result.loc[result["home_team"] == "France", "tournament_stage"].iloc[0] == "Final"
        assert result.loc[result["home_team"] == "Argentina", "tournament_stage"].iloc[0] == "Final"

    def test_lookup_leaves_non_wc_rows_unchanged(self):
        df = self._base_df()
        result = _apply_stage_lookup(df)
        assert result.loc[result["home_team"] == "Germany", "tournament_stage"].iloc[0] == "Unknown"

    def test_lookup_does_not_overwrite_known_stage(self):
        df = self._base_df()
        df.loc[0, "tournament_stage"] = "Group Stage"
        result = _apply_stage_lookup(df)
        assert result.loc[0, "tournament_stage"] == "Group Stage"

    def test_lookup_works_with_noncontiguous_index(self):
        df = self._base_df()
        df = df.iloc[1:].copy()  # index starts at 1, not 0
        result = _apply_stage_lookup(df)
        assert result.loc[result["home_team"] == "Argentina", "tournament_stage"].iloc[0] == "Final"

    def test_save_processed_matches_writes_tournament_stage_column(self, tmp_path):
        from src.data.load_matches import save_processed_matches
        df = pd.DataFrame({
            "date": ["2018-07-15"],
            "home_team": ["France"],
            "away_team": ["Croatia"],
            "home_score": [4],
            "away_score": [2],
            "neutral": [True],
            "tournament_stage": ["Unknown"],
        })
        out = str(tmp_path / "matches.csv")
        save_processed_matches(df, out)
        result = pd.read_csv(out)
        assert "tournament_stage" in result.columns
        assert result["tournament_stage"].iloc[0] == "Final"


from src.utils import load_config


class TestConfigKeys:
    def test_logreg_c_present_in_config(self):
        cfg = load_config()
        assert "logreg_C" in cfg["model"], "logreg_C missing from config"
        assert cfg["model"]["logreg_C"] == 1.0

    def test_min_model_weight_present_in_config(self):
        cfg = load_config()
        assert "min_model_weight" in cfg["model"]
        assert cfg["model"]["min_model_weight"] == 0.05

    def test_mlp_hidden_layers_present_in_config(self):
        cfg = load_config()
        assert "mlp_hidden_layers" in cfg["model"]
        assert cfg["model"]["mlp_hidden_layers"] == [64, 32]

    def test_tournament_model_min_weight_present_in_config(self):
        cfg = load_config()
        assert "tournament_model_min_weight" in cfg["model"]
        assert cfg["model"]["tournament_model_min_weight"] == 3
