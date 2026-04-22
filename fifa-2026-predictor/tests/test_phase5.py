"""Phase 5 tests: player layer, feature registry, aggregation, fallbacks.

Run with:
    python -m pytest tests/test_phase5.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.player_schema import (
    DEFAULTS,
    PLAYER_COLUMNS,
    ROSTER_COLUMNS,
    INJURY_COLUMNS,
    PLAYER_RATING_COLUMNS,
    EXPECTED_LINEUP_COLUMNS,
    PlayerRecord,
    RosterEntry,
    InjuryRecord,
    PlayerRating,
    ensure_player_schema,
    ensure_roster_schema,
    ensure_injury_schema,
    ensure_rating_schema,
    ensure_lineup_schema,
    VALID_POSITIONS,
)
from src.data.player_identity import (
    CANONICAL_PLAYERS,
    resolve_player,
    get_player,
    list_players_for_team,
)
from src.data.load_players import (
    load_players,
    load_injuries,
    load_player_ratings,
    load_expected_lineups,
    load_player_match_stats,
)
from src.data.load_rosters import load_rosters, get_team_roster
from src.features.player_aggregator import (
    PLAYER_FEATURE_NAMES,
    PLAYER_MATCH_FEATURE_NAMES,
    aggregate_team_player_features,
    build_player_match_features,
)
from src.features.registry import FeatureBlock, FeatureRegistry, get_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg() -> dict:
    return {
        "features": {
            "form_window": 5,
            "elo_k_factor": 40.0,
            "elo_home_advantage": 100.0,
            "default_fifa_rank": 75,
            "recency_halflife_days": 180.0,
        }
    }


def _make_ratings_df(player_ratings: Dict[str, float], date: str = "2025-01-01") -> pd.DataFrame:
    """Build a minimal ratings DataFrame for testing."""
    rows = [
        {
            "player_id": pid,
            "rating_date": date,
            "overall_rating": rating,
            "attack_rating": None,
            "defense_rating": None,
            "source": "test",
        }
        for pid, rating in player_ratings.items()
    ]
    return pd.DataFrame(rows)


def _make_lineups_df(team: str, player_ids, date: str, match_id: str = "m1") -> pd.DataFrame:
    rows = [
        {
            "match_id": match_id,
            "team": team,
            "player_id": pid,
            "date": date,
            "formation_position": None,
            "is_starter": True,
        }
        for pid in player_ids
    ]
    return pd.DataFrame(rows)


def _make_injuries_df(team: str, player_id: str, from_date: str, to_date=None) -> pd.DataFrame:
    return pd.DataFrame([{
        "player_id": player_id,
        "team": team,
        "from_date": from_date,
        "to_date": to_date,
        "injury_type": "test",
        "severity": "minor",
    }])


def _make_rosters_df(team: str, player_ids, season: str = "2025-2026") -> pd.DataFrame:
    rows = [
        {
            "team": team,
            "player_id": pid,
            "season": season,
            "squad_number": None,
            "joined_date": None,
            "left_date": None,
        }
        for pid in player_ids
    ]
    return pd.DataFrame(rows)


def _minimal_matches() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "date": "2024-01-01", "home_team": "Brazil", "away_team": "Argentina",
            "home_score": 2, "away_score": 1, "competition": "International Friendly",
            "neutral": False, "home_confederation": "CONMEBOL",
            "away_confederation": "CONMEBOL", "home_fifa_rank": 5,
            "away_fifa_rank": 3, "tournament_stage": "Unknown",
        },
        {
            "date": "2024-02-01", "home_team": "France", "away_team": "Germany",
            "home_score": 1, "away_score": 0, "competition": "International Friendly",
            "neutral": False, "home_confederation": "UEFA",
            "away_confederation": "UEFA", "home_fifa_rank": 2,
            "away_fifa_rank": 10, "tournament_stage": "Unknown",
        },
    ])


# ===========================================================================
# 1. Player schema tests
# ===========================================================================

class TestPlayerSchema(unittest.TestCase):

    def test_player_columns_defined(self):
        self.assertIn("player_id", PLAYER_COLUMNS)
        self.assertIn("position", PLAYER_COLUMNS)

    def test_valid_positions(self):
        self.assertIn("GK", VALID_POSITIONS)
        self.assertIn("FWD", VALID_POSITIONS)

    def test_player_record_valid(self):
        p = PlayerRecord("p1", "Test Player", "Brazil", "FWD")
        self.assertEqual(p.position, "FWD")

    def test_player_record_invalid_position(self):
        with self.assertRaises(ValueError):
            PlayerRecord("p1", "Test Player", "Brazil", "INVALID")

    def test_ensure_player_schema_ok(self):
        df = pd.DataFrame([{
            "player_id": "p1", "name": "Test", "nationality": "Brazil", "position": "fwd",
        }])
        result = ensure_player_schema(df)
        self.assertEqual(result["position"].iloc[0], "FWD")

    def test_ensure_player_schema_missing_col(self):
        df = pd.DataFrame([{"player_id": "p1", "name": "Test"}])
        with self.assertRaises(ValueError):
            ensure_player_schema(df)

    def test_ensure_roster_schema_ok(self):
        df = pd.DataFrame([{"team": "Brazil", "player_id": "p1", "season": "2025-2026"}])
        result = ensure_roster_schema(df)
        self.assertIn("left_date", result.columns)

    def test_ensure_injury_schema_ok(self):
        df = pd.DataFrame([{
            "player_id": "p1", "team": "Brazil", "from_date": "2025-01-01",
        }])
        result = ensure_injury_schema(df)
        self.assertIn("to_date", result.columns)

    def test_ensure_rating_schema_ok(self):
        df = pd.DataFrame([{
            "player_id": "p1", "rating_date": "2025-01-01", "overall_rating": 85.0,
        }])
        result = ensure_rating_schema(df)
        self.assertIn("attack_rating", result.columns)

    def test_ensure_lineup_schema_ok(self):
        df = pd.DataFrame([{
            "match_id": "m1", "team": "Brazil", "player_id": "p1", "date": "2025-06-15",
        }])
        result = ensure_lineup_schema(df)
        self.assertIn("is_starter", result.columns)
        self.assertTrue(result["is_starter"].iloc[0])

    def test_defaults_dict_complete(self):
        for key in ["overall_rating", "attack_rating", "defense_rating",
                    "gk_rating", "squad_rating", "missing_top3_count", "squad_continuity"]:
            self.assertIn(key, DEFAULTS)


# ===========================================================================
# 2. Player identity tests
# ===========================================================================

class TestPlayerIdentity(unittest.TestCase):

    def test_canonical_players_populated(self):
        self.assertGreater(len(CANONICAL_PLAYERS), 0)

    def test_resolve_known_player(self):
        pid = resolve_player("Messi")
        self.assertEqual(pid, "messi_lionel")

    def test_resolve_canonical_name(self):
        pid = resolve_player("Lionel Messi")
        self.assertEqual(pid, "messi_lionel")

    def test_resolve_unknown_player(self):
        pid = resolve_player("Unknown Player XYZ")
        self.assertIsNone(pid)

    def test_resolve_with_matching_nationality(self):
        pid = resolve_player("Messi", nationality="Argentina")
        self.assertEqual(pid, "messi_lionel")

    def test_resolve_with_wrong_nationality(self):
        pid = resolve_player("Messi", nationality="Brazil")
        self.assertIsNone(pid)

    def test_get_player_returns_record(self):
        record = get_player("messi_lionel")
        self.assertIsNotNone(record)
        self.assertEqual(record["position"], "FWD")

    def test_get_player_unknown(self):
        self.assertIsNone(get_player("nonexistent_player"))

    def test_list_players_for_team(self):
        argentina_players = list_players_for_team("Argentina")
        self.assertIn("messi_lionel", argentina_players)

    def test_list_players_for_team_empty(self):
        result = list_players_for_team("Andorra")
        self.assertEqual(result, [])


# ===========================================================================
# 3. Loader tests (graceful degradation)
# ===========================================================================

class TestLoaders(unittest.TestCase):

    def test_load_players_no_path(self):
        df = load_players(None)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 0)
        for col in PLAYER_COLUMNS:
            self.assertIn(col, df.columns)

    def test_load_players_missing_file(self):
        df = load_players("/nonexistent/players.csv")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 0)

    def test_load_injuries_no_path(self):
        df = load_injuries(None)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 0)

    def test_load_player_ratings_no_path(self):
        df = load_player_ratings(None)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 0)

    def test_load_expected_lineups_no_path(self):
        df = load_expected_lineups(None)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 0)

    def test_load_player_match_stats_no_path(self):
        df = load_player_match_stats(None)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 0)

    def test_load_rosters_no_path(self):
        df = load_rosters(None)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 0)

    def test_load_rosters_missing_file(self):
        df = load_rosters("/nonexistent/rosters.csv")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 0)


# ===========================================================================
# 4. Roster loader: get_team_roster
# ===========================================================================

class TestGetTeamRoster(unittest.TestCase):

    def test_empty_rosters(self):
        df = get_team_roster(pd.DataFrame(columns=ROSTER_COLUMNS), "Brazil", "2025-06-01")
        self.assertEqual(len(df), 0)

    def test_active_player_returned(self):
        rosters = _make_rosters_df("Brazil", ["p1", "p2"])
        result = get_team_roster(rosters, "Brazil", "2025-06-01")
        self.assertEqual(len(result), 2)

    def test_team_case_insensitive(self):
        rosters = _make_rosters_df("Brazil", ["p1"])
        result = get_team_roster(rosters, "brazil", "2025-06-01")
        self.assertEqual(len(result), 1)

    def test_departed_player_excluded(self):
        rosters = pd.DataFrame([{
            "team": "Brazil", "player_id": "p1", "season": "2025-2026",
            "squad_number": None, "joined_date": None, "left_date": "2025-01-01",
        }])
        result = get_team_roster(rosters, "Brazil", "2025-06-01")
        self.assertEqual(len(result), 0)

    def test_not_yet_joined_excluded(self):
        rosters = pd.DataFrame([{
            "team": "Brazil", "player_id": "p1", "season": "2025-2026",
            "squad_number": None, "joined_date": "2026-01-01", "left_date": None,
        }])
        result = get_team_roster(rosters, "Brazil", "2025-06-01")
        self.assertEqual(len(result), 0)

    def test_other_team_excluded(self):
        rosters = _make_rosters_df("Argentina", ["p1"])
        result = get_team_roster(rosters, "Brazil", "2025-06-01")
        self.assertEqual(len(result), 0)


# ===========================================================================
# 5. Player aggregator: fallback behaviour
# ===========================================================================

class TestPlayerAggregatorFallbacks(unittest.TestCase):

    def test_all_none_returns_defaults(self):
        feats = aggregate_team_player_features("Brazil", "2025-06-15")
        self.assertEqual(feats["has_lineup_data"], 0.0)
        self.assertEqual(feats["has_injury_data"], 0.0)
        self.assertEqual(feats["has_rating_data"], 0.0)
        self.assertAlmostEqual(feats["squad_overall_rating"], DEFAULTS["squad_rating"])
        self.assertAlmostEqual(feats["squad_continuity"], DEFAULTS["squad_continuity"])
        self.assertEqual(feats["missing_top3_count"], 0.0)

    def test_empty_dataframes_return_defaults(self):
        feats = aggregate_team_player_features(
            "Brazil", "2025-06-15",
            rosters_df=pd.DataFrame(columns=ROSTER_COLUMNS),
            ratings_df=pd.DataFrame(columns=PLAYER_RATING_COLUMNS),
            injuries_df=pd.DataFrame(columns=INJURY_COLUMNS),
            lineups_df=pd.DataFrame(columns=EXPECTED_LINEUP_COLUMNS),
        )
        self.assertEqual(feats["has_lineup_data"], 0.0)

    def test_no_injuries_full_continuity(self):
        rosters = _make_rosters_df("Brazil", ["p1", "p2", "p3"])
        feats = aggregate_team_player_features(
            "Brazil", "2025-06-15",
            rosters_df=rosters,
        )
        self.assertAlmostEqual(feats["squad_continuity"], 1.0)

    def test_feature_names_complete(self):
        feats = aggregate_team_player_features("Brazil", "2025-06-15")
        for name in PLAYER_FEATURE_NAMES:
            self.assertIn(name, feats, f"Missing feature: {name}")


# ===========================================================================
# 6. Player aggregator: with data
# ===========================================================================

class TestPlayerAggregatorWithData(unittest.TestCase):

    def test_ratings_reflected(self):
        ratings = _make_ratings_df({"p1": 90.0, "p2": 80.0}, date="2025-01-01")
        lineups = _make_lineups_df("Brazil", ["p1", "p2"], date="2025-06-15")
        feats = aggregate_team_player_features(
            "Brazil", "2025-06-15",
            ratings_df=ratings,
            lineups_df=lineups,
        )
        self.assertEqual(feats["has_lineup_data"], 1.0)
        self.assertEqual(feats["has_rating_data"], 1.0)
        self.assertAlmostEqual(feats["squad_overall_rating"], 85.0)

    def test_injury_reduces_continuity(self):
        rosters = _make_rosters_df("Brazil", ["p1", "p2", "p3", "p4"])
        injuries = _make_injuries_df("Brazil", "p1", "2025-01-01")
        feats = aggregate_team_player_features(
            "Brazil", "2025-06-15",
            rosters_df=rosters,
            injuries_df=injuries,
        )
        self.assertEqual(feats["has_injury_data"], 1.0)
        self.assertAlmostEqual(feats["squad_continuity"], 0.75)

    def test_missing_top3_counts_injured_top_players(self):
        ratings = _make_ratings_df({"p1": 95.0, "p2": 90.0, "p3": 85.0, "p4": 70.0},
                                   date="2025-01-01")
        lineups = _make_lineups_df("Brazil", ["p1", "p2", "p3", "p4"], date="2025-06-15")
        injuries = _make_injuries_df("Brazil", "p1", "2025-01-01")
        feats = aggregate_team_player_features(
            "Brazil", "2025-06-15",
            ratings_df=ratings,
            lineups_df=lineups,
            injuries_df=injuries,
        )
        self.assertEqual(feats["missing_top3_count"], 1.0)

    def test_no_missing_top3_when_no_injuries(self):
        ratings = _make_ratings_df({"p1": 95.0, "p2": 90.0, "p3": 85.0},
                                   date="2025-01-01")
        lineups = _make_lineups_df("Brazil", ["p1", "p2", "p3"], date="2025-06-15")
        feats = aggregate_team_player_features(
            "Brazil", "2025-06-15",
            ratings_df=ratings,
            lineups_df=lineups,
        )
        self.assertEqual(feats["missing_top3_count"], 0.0)

    def test_future_ratings_excluded(self):
        # Ratings dated after match_date must NOT leak into pre-match features
        ratings = _make_ratings_df({"p1": 99.0}, date="2026-01-01")
        lineups = _make_lineups_df("Brazil", ["p1"], date="2025-06-15")
        feats = aggregate_team_player_features(
            "Brazil", "2025-06-15",
            ratings_df=ratings,
            lineups_df=lineups,
        )
        # No valid ratings before match date → fallback to default
        self.assertEqual(feats["has_rating_data"], 0.0)

    def test_lineup_prioritised_over_roster(self):
        rosters = _make_rosters_df("Brazil", ["p1", "p2", "p3"])
        lineups = _make_lineups_df("Brazil", ["p4", "p5"], date="2025-06-15")
        feats = aggregate_team_player_features(
            "Brazil", "2025-06-15",
            rosters_df=rosters,
            lineups_df=lineups,
        )
        # has_lineup_data should be 1; lineup used, not roster
        self.assertEqual(feats["has_lineup_data"], 1.0)

    def test_roster_fallback_used_when_no_lineup(self):
        rosters = _make_rosters_df("Brazil", ["p1", "p2"])
        feats = aggregate_team_player_features(
            "Brazil", "2025-06-15",
            rosters_df=rosters,
        )
        self.assertEqual(feats["has_lineup_data"], 0.0)
        # Squad continuity should still be 1.0 (no injuries)
        self.assertAlmostEqual(feats["squad_continuity"], 1.0)


# ===========================================================================
# 7. build_player_match_features: prefixed output
# ===========================================================================

class TestBuildPlayerMatchFeatures(unittest.TestCase):

    def test_returns_home_and_away_prefixes(self):
        feats = build_player_match_features("Brazil", "France", "2025-06-15")
        for name in PLAYER_FEATURE_NAMES:
            self.assertIn(f"home_{name}", feats)
            self.assertIn(f"away_{name}", feats)

    def test_all_values_are_numeric(self):
        feats = build_player_match_features("Brazil", "France", "2025-06-15")
        for k, v in feats.items():
            self.assertIsInstance(v, (int, float), f"Non-numeric value for {k}: {v}")

    def test_output_matches_match_feature_names(self):
        feats = build_player_match_features("Brazil", "France", "2025-06-15")
        for name in PLAYER_MATCH_FEATURE_NAMES:
            self.assertIn(name, feats)

    def test_independent_home_away_values(self):
        ratings = _make_ratings_df({"p1": 90.0}, date="2025-01-01")
        home_lineups = _make_lineups_df("Brazil", ["p1"], date="2025-06-15")
        feats = build_player_match_features(
            "Brazil", "France", "2025-06-15",
            lineups_df=home_lineups,
            ratings_df=ratings,
        )
        # Brazil has lineup data; France does not
        self.assertEqual(feats["home_has_lineup_data"], 1.0)
        self.assertEqual(feats["away_has_lineup_data"], 0.0)


# ===========================================================================
# 8. Feature registry tests
# ===========================================================================

class TestFeatureRegistry(unittest.TestCase):

    def test_singleton_has_standard_blocks(self):
        registry = get_registry()
        for name in ["form", "elo", "tournament", "player_aggregate"]:
            self.assertIn(name, registry)

    def test_player_aggregate_disabled_by_default(self):
        registry = get_registry()
        self.assertFalse(registry.is_enabled("player_aggregate"))

    def test_core_blocks_enabled_by_default(self):
        registry = get_registry()
        for name in ["form", "elo", "tournament"]:
            self.assertTrue(registry.is_enabled(name))

    def test_list_blocks_returns_all(self):
        registry = get_registry()
        blocks = registry.list_blocks()
        self.assertGreaterEqual(len(blocks), 4)

    def test_enabled_blocks_excludes_disabled(self):
        registry = get_registry()
        enabled = registry.enabled_blocks()
        self.assertNotIn("player_aggregate", enabled)

    def test_enable_disable(self):
        # Use a fresh registry to avoid mutating the singleton
        reg = FeatureRegistry()
        reg.register(FeatureBlock("test_block", lambda ctx: {"x": 1}, enabled=False))
        self.assertFalse(reg.is_enabled("test_block"))
        reg.enable("test_block")
        self.assertTrue(reg.is_enabled("test_block"))
        reg.disable("test_block")
        self.assertFalse(reg.is_enabled("test_block"))

    def test_build_all_skips_disabled(self):
        reg = FeatureRegistry()
        reg.register(FeatureBlock("a", lambda ctx: {"feat_a": 1}, enabled=True))
        reg.register(FeatureBlock("b", lambda ctx: {"feat_b": 2}, enabled=False))
        result = reg.build_all({})
        self.assertIn("feat_a", result)
        self.assertNotIn("feat_b", result)

    def test_build_all_merges_outputs(self):
        reg = FeatureRegistry()
        reg.register(FeatureBlock("a", lambda ctx: {"x": 1, "y": 2}))
        reg.register(FeatureBlock("b", lambda ctx: {"z": 3}))
        result = reg.build_all({})
        self.assertEqual(result, {"x": 1, "y": 2, "z": 3})

    def test_build_all_survives_exception_in_block(self):
        reg = FeatureRegistry()
        reg.register(FeatureBlock("good", lambda ctx: {"ok": 1}))
        reg.register(FeatureBlock("bad", lambda ctx: (_ for _ in ()).throw(RuntimeError("boom"))))
        # Should not raise; bad block is skipped
        result = reg.build_all({})
        self.assertIn("ok", result)

    def test_require_raises_for_unknown_block(self):
        reg = FeatureRegistry()
        with self.assertRaises(KeyError):
            reg.enable("nonexistent_block")

    def test_build_block_executes_disabled_block(self):
        reg = FeatureRegistry()
        reg.register(FeatureBlock("b", lambda ctx: {"v": 99}, enabled=False))
        result = reg.build_block("b", {})
        self.assertEqual(result["v"], 99)

    def test_decorator_registers_block(self):
        reg = FeatureRegistry()

        @reg.feature_block("decorated", enabled=True, description="test block")
        def my_block(ctx):
            return {"decorated_feat": 42}

        self.assertIn("decorated", reg)
        result = reg.build_all({})
        self.assertEqual(result["decorated_feat"], 42)

    def test_len_counts_all_blocks(self):
        reg = FeatureRegistry()
        reg.register(FeatureBlock("a", lambda ctx: {}))
        reg.register(FeatureBlock("b", lambda ctx: {}))
        self.assertEqual(len(reg), 2)

    def test_player_aggregate_block_produces_prefixed_features(self):
        registry = get_registry()
        # Temporarily enable the player_aggregate block
        registry.enable("player_aggregate")
        try:
            context = {
                "home_team": "Brazil",
                "away_team": "France",
                "match_date": "2025-06-15",
            }
            result = registry.build_block("player_aggregate", context)
            self.assertIn("home_squad_overall_rating", result)
            self.assertIn("away_squad_overall_rating", result)
        finally:
            registry.disable("player_aggregate")

    def test_player_aggregate_block_missing_context_keys(self):
        registry = get_registry()
        # Context without required keys – must not crash
        result = registry.build_block("player_aggregate", {})
        self.assertEqual(result, {})


# ===========================================================================
# 9. Match pipeline stays one-row-per-match
# ===========================================================================

class TestMatchRowIntegrity(unittest.TestCase):

    def test_build_feature_table_one_row_per_match(self):
        from src.features.build_features import build_feature_table
        matches = _minimal_matches()
        features = build_feature_table(matches, _cfg())
        self.assertEqual(len(features), len(matches))

    def test_build_feature_table_with_player_data_one_row_per_match(self):
        from src.features.build_features import build_feature_table

        # Enable player_aggregate block for this test
        registry = get_registry()
        registry.enable("player_aggregate")
        try:
            matches = _minimal_matches()
            ratings = _make_ratings_df({"p1": 85.0, "p2": 80.0}, date="2023-01-01")
            features = build_feature_table(
                matches, _cfg(),
                ratings_df=ratings,
            )
            self.assertEqual(len(features), len(matches))
        finally:
            registry.disable("player_aggregate")

    def test_predict_row_is_single_row(self):
        from src.app.predict_match import build_pre_match_row

        matches = _minimal_matches()
        row = build_pre_match_row(
            history_df=matches,
            home_team="Brazil",
            away_team="Argentina",
            match_date="2025-06-15",
            competition="FIFA World Cup",
            neutral=True,
            home_confederation="CONMEBOL",
            away_confederation="CONMEBOL",
            home_fifa_rank=5,
            away_fifa_rank=3,
            tournament_stage="Group",
            cfg=_cfg(),
        )
        self.assertEqual(len(row), 1)

    def test_predict_row_with_player_data_still_single_row(self):
        from src.app.predict_match import build_pre_match_row

        registry = get_registry()
        registry.enable("player_aggregate")
        try:
            matches = _minimal_matches()
            ratings = _make_ratings_df({"p1": 85.0}, date="2023-01-01")
            row = build_pre_match_row(
                history_df=matches,
                home_team="Brazil",
                away_team="France",
                match_date="2025-06-15",
                competition="FIFA World Cup",
                neutral=True,
                home_confederation="CONMEBOL",
                away_confederation="UEFA",
                home_fifa_rank=5,
                away_fifa_rank=2,
                tournament_stage="Group",
                cfg=_cfg(),
                ratings_df=ratings,
            )
            self.assertEqual(len(row), 1)
        finally:
            registry.disable("player_aggregate")


# ===========================================================================
# 10. Training / inference feature consistency
# ===========================================================================

class TestTrainInferenceConsistency(unittest.TestCase):

    def test_shared_columns_present_in_both_paths(self):
        """Training feature table and inference row share the same core columns."""
        from src.features.build_features import build_feature_table
        from src.app.predict_match import build_pre_match_row

        matches = _minimal_matches()
        train_features = build_feature_table(matches, _cfg())

        inference_row = build_pre_match_row(
            history_df=matches,
            home_team="Brazil",
            away_team="Argentina",
            match_date="2025-06-15",
            competition="International Friendly",
            neutral=False,
            home_confederation="CONMEBOL",
            away_confederation="CONMEBOL",
            home_fifa_rank=5,
            away_fifa_rank=3,
            tournament_stage="Unknown",
            cfg=_cfg(),
        )

        core_cols = ["home_elo_pre", "away_elo_pre", "home_form_last5", "away_form_last5"]
        for col in core_cols:
            self.assertIn(col, train_features.columns, f"Missing in training: {col}")
            self.assertIn(col, inference_row.columns, f"Missing in inference: {col}")


if __name__ == "__main__":
    unittest.main()
