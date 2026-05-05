"""Phase 1 sanity checks.

Run without pytest:
    python tests/test_sanity.py

Run with pytest:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

# Ensure src is importable when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.schema import (
    ensure_match_schema,
    ensure_team_schema,
    fill_missing_defaults,
    normalize_team_name,
)
from src.features.match_row_builder import build_match_row
from src.features.state_tracker import TeamStateTracker


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
        }
    }


def _minimal_matches() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2026-05-01", "2026-05-10", "2026-05-20"],
        "home_team": ["Brazil", "France", "Argentina"],
        "away_team": ["Argentina", "Spain", "Brazil"],
        "home_score": [2, 1, 0],
        "away_score": [1, 0, 1],
        "neutral": [False, False, True],
        "competition": ["Friendly", "Friendly", "Friendly"],
        "home_confederation": ["CONMEBOL", "UEFA", "CONMEBOL"],
        "away_confederation": ["CONMEBOL", "UEFA", "CONMEBOL"],
        "home_fifa_rank": [2, 3, 1],
        "away_fifa_rank": [1, 4, 2],
        "tournament_stage": ["Unknown", "Unknown", "Unknown"],
    })


# ---------------------------------------------------------------------------
# schema.py
# ---------------------------------------------------------------------------

class TestNormalizeTeamName(unittest.TestCase):
    def test_usa_alias(self):
        self.assertEqual(normalize_team_name("USA"), "United States")

    def test_unknown_passthrough(self):
        self.assertEqual(normalize_team_name("Brazil"), "Brazil")

    def test_strips_whitespace(self):
        self.assertEqual(normalize_team_name("  France  "), "France")


class TestFillMissingDefaults(unittest.TestCase):
    def test_adds_absent_column(self):
        df = pd.DataFrame({"a": [1, 2]})
        out = fill_missing_defaults(df, {"b": 99})
        self.assertEqual(list(out["b"]), [99, 99])

    def test_fills_nan_in_existing_column(self):
        df = pd.DataFrame({"a": [1.0, float("nan")]})
        out = fill_missing_defaults(df, {"a": 0})
        self.assertEqual(out["a"].iloc[1], 0)


class TestEnsureMatchSchema(unittest.TestCase):
    def test_fills_optional_columns(self):
        df = pd.DataFrame({
            "date": ["2026-06-14"],
            "home_team": ["Brazil"],
            "away_team": ["France"],
            "home_score": [1],
            "away_score": [2],
        })
        out = ensure_match_schema(df)
        self.assertIn("home_confederation", out.columns)
        self.assertEqual(out["home_confederation"].iloc[0], "UNKNOWN")
        self.assertIn("tournament_stage", out.columns)
        self.assertEqual(out["tournament_stage"].iloc[0], "Unknown")

    def test_normalises_team_aliases(self):
        df = pd.DataFrame({
            "date": ["2026-06-14"],
            "home_team": ["USA"],
            "away_team": ["Mexico"],
            "home_score": [1],
            "away_score": [0],
        })
        out = ensure_match_schema(df)
        self.assertEqual(out["home_team"].iloc[0], "United States")

    def test_normalises_neutral_string(self):
        df = pd.DataFrame({
            "date": ["2026-06-14"],
            "home_team": ["Brazil"],
            "away_team": ["France"],
            "home_score": [1],
            "away_score": [0],
            "neutral": ["True"],
        })
        out = ensure_match_schema(df)
        self.assertEqual(out["neutral"].dtype, bool)
        self.assertTrue(out["neutral"].iloc[0])

    def test_raises_on_missing_required_column(self):
        df = pd.DataFrame({"date": ["2026-06-14"], "home_team": ["Brazil"]})
        with self.assertRaises(ValueError):
            ensure_match_schema(df)


class TestEnsureTeamSchema(unittest.TestCase):
    def test_fills_defaults_when_columns_absent(self):
        df = pd.DataFrame({"team": ["Brazil", "France"]})
        out = ensure_team_schema(df)
        self.assertIn("confederation", out.columns)
        self.assertIn("fifa_rank", out.columns)
        self.assertEqual(out["confederation"].iloc[0], "UNKNOWN")
        self.assertEqual(out["fifa_rank"].iloc[0], 75)

    def test_normalises_team_names(self):
        df = pd.DataFrame({"team": ["USA", "Mexico"]})
        out = ensure_team_schema(df)
        self.assertEqual(out["team"].iloc[0], "United States")


# ---------------------------------------------------------------------------
# state_tracker.py
# ---------------------------------------------------------------------------

class TestTeamStateTracker(unittest.TestCase):
    def test_initial_elo(self):
        self.assertEqual(TeamStateTracker(_cfg()).elo("Brazil"), 1500.0)

    def test_initial_form_default(self):
        self.assertEqual(TeamStateTracker(_cfg()).form("Brazil"), 1.5)

    def test_initial_goals_default(self):
        tracker = TeamStateTracker(_cfg())
        self.assertEqual(tracker.goals_for("Brazil"), 1.0)
        self.assertEqual(tracker.goals_against("Brazil"), 1.0)

    def test_initial_rest_days_default(self):
        tracker = TeamStateTracker(_cfg())
        self.assertEqual(tracker.rest_days("Brazil", pd.Timestamp("2026-06-14")), 7)

    def test_win_raises_home_elo(self):
        tracker = TeamStateTracker(_cfg())
        tracker.update("Brazil", "Argentina", 2, 0, False, pd.Timestamp("2026-06-14"))
        self.assertGreater(tracker.elo("Brazil"), 1500.0)
        self.assertLess(tracker.elo("Argentina"), 1500.0)

    def test_form_after_win(self):
        tracker = TeamStateTracker(_cfg())
        tracker.update("Brazil", "Argentina", 1, 0, False, pd.Timestamp("2026-06-14"))
        self.assertEqual(tracker.form("Brazil"), 3.0)
        self.assertEqual(tracker.form("Argentina"), 0.0)

    def test_form_after_draw(self):
        tracker = TeamStateTracker(_cfg())
        tracker.update("Brazil", "Argentina", 1, 1, False, pd.Timestamp("2026-06-14"))
        self.assertEqual(tracker.form("Brazil"), 1.0)
        self.assertEqual(tracker.form("Argentina"), 1.0)

    def test_rest_days_after_match(self):
        tracker = TeamStateTracker(_cfg())
        tracker.update("Brazil", "Argentina", 1, 0, False, pd.Timestamp("2026-06-14"))
        self.assertEqual(tracker.rest_days("Brazil", pd.Timestamp("2026-06-21")), 7)

    def test_elo_win_prob_neutral_equal_teams(self):
        tracker = TeamStateTracker(_cfg())
        prob = tracker.elo_win_prob("Brazil", "Argentina", neutral=True)
        self.assertAlmostEqual(prob, 0.5, places=6)

    def test_elo_win_prob_home_advantage(self):
        tracker = TeamStateTracker(_cfg())
        prob = tracker.elo_win_prob("Brazil", "Argentina", neutral=False)
        self.assertGreater(prob, 0.5)

    def test_replay_history(self):
        history = _minimal_matches()
        history["date"] = pd.to_datetime(history["date"])
        tracker = TeamStateTracker(_cfg())
        tracker.replay_history(history)
        self.assertNotEqual(tracker.elo("Brazil"), 1500.0)


# ---------------------------------------------------------------------------
# match_row_builder.py
# ---------------------------------------------------------------------------

class TestBuildMatchRow(unittest.TestCase):
    def _make_row(self, **kwargs):
        tracker = TeamStateTracker(_cfg())
        defaults = dict(
            tracker=tracker,
            home_team="Brazil", away_team="France",
            match_date=pd.Timestamp("2026-06-14"),
            competition="FIFA World Cup", neutral=False,
            home_confederation="CONMEBOL", away_confederation="UEFA",
            home_fifa_rank=2, away_fifa_rank=3,
            tournament_stage="Group Stage",
        )
        defaults.update(kwargs)
        return build_match_row(**defaults)

    def test_returns_all_expected_keys(self):
        row = self._make_row()
        required = [
            "home_elo_pre", "away_elo_pre", "elo_win_prob",
            "home_form_last5", "away_form_last5",
            "home_goals_for_last5", "away_goals_for_last5",
            "home_goals_against_last5", "away_goals_against_last5",
            "home_rest_days_log", "away_rest_days_log",
            "home_long_break", "away_long_break",
            "elo_diff_home_away", "form_diff_home_away", "goal_balance_diff",
            "rank_diff", "competition_weight", "is_same_confederation",
        ]
        for k in required:
            self.assertIn(k, row, f"Missing key: {k}")

    def test_same_confederation_flag(self):
        row = self._make_row(
            home_confederation="CONMEBOL",
            away_confederation="CONMEBOL",
        )
        self.assertEqual(row["is_same_confederation"], 1)

    def test_different_confederation_flag(self):
        row = self._make_row(
            home_confederation="CONMEBOL",
            away_confederation="UEFA",
        )
        self.assertEqual(row["is_same_confederation"], 0)


# ---------------------------------------------------------------------------
# build_features.py
# ---------------------------------------------------------------------------

class TestBuildFeatureTable(unittest.TestCase):
    def test_normalizes_team_aliases_in_training(self):
        """build_feature_table must apply alias normalization so tracker keys are canonical."""
        from src.features.build_features import build_feature_table

        df = pd.DataFrame({
            "date": ["2026-05-01", "2026-05-10"],
            "home_team": ["USA", "Mexico"],
            "away_team": ["Mexico", "USA"],
            "home_score": [1, 0],
            "away_score": [0, 1],
            "neutral": [False, False],
        })
        features = build_feature_table(df, _cfg())
        # Alias USA → United States must have been applied before building rows.
        self.assertIn("United States", features["home_team"].values)
        self.assertNotIn("USA", features["home_team"].values)

    def test_missing_optional_columns_do_not_crash(self):
        """Matches with only required columns must not raise in build_feature_table."""
        from src.features.build_features import build_feature_table

        df = pd.DataFrame({
            "date": ["2026-05-01"],
            "home_team": ["Brazil"],
            "away_team": ["France"],
            "home_score": [1],
            "away_score": [0],
        })
        # Should complete without KeyError or ValueError.
        features = build_feature_table(df, _cfg())
        self.assertEqual(len(features), 1)
        self.assertIn("home_elo_pre", features.columns)

    def test_target_labels_are_correct(self):
        from src.features.build_features import build_feature_table

        df = pd.DataFrame({
            "date": ["2026-05-01", "2026-05-02", "2026-05-03"],
            "home_team": ["Brazil", "France", "Spain"],
            "away_team": ["Germany", "England", "Italy"],
            "home_score": [2, 1, 0],
            "away_score": [0, 1, 1],
            "neutral": [False, False, False],
        })
        features = build_feature_table(df, _cfg())
        self.assertEqual(features.iloc[0]["target"], "H")
        self.assertEqual(features.iloc[1]["target"], "D")
        self.assertEqual(features.iloc[2]["target"], "A")


# ---------------------------------------------------------------------------
# Training + inference consistency
# ---------------------------------------------------------------------------

class TestTrainingInferenceConsistency(unittest.TestCase):
    """Training and inference must produce identical pre-match feature rows."""

    def test_first_match_uses_base_elo(self):
        from src.features.build_features import build_feature_table
        features = build_feature_table(_minimal_matches(), _cfg())
        first = features.iloc[0]
        self.assertEqual(first["home_elo_pre"], 1500.0)
        self.assertEqual(first["away_elo_pre"], 1500.0)

    def test_third_match_elo_is_updated(self):
        from src.features.build_features import build_feature_table
        features = build_feature_table(_minimal_matches(), _cfg())
        third = features.iloc[2]
        # Both Argentina and Brazil appeared in match 1, so Elo differs from base
        self.assertNotEqual(third["home_elo_pre"], 1500.0)
        self.assertNotEqual(third["away_elo_pre"], 1500.0)

    def test_inference_equals_training_for_third_match(self):
        """Replaying history through the tracker must reproduce training features."""
        from src.features.build_features import build_feature_table

        matches = _minimal_matches()
        cfg = _cfg()
        features = build_feature_table(matches, cfg)
        train_row = features.iloc[2]

        # Inference path: replay first two matches, then snapshot state
        history = matches.iloc[:2].copy()
        history["date"] = pd.to_datetime(history["date"])
        tracker = TeamStateTracker(cfg)
        tracker.replay_history(history)
        infer_row = build_match_row(
            tracker=tracker,
            home_team="Argentina",
            away_team="Brazil",
            match_date=pd.Timestamp("2026-05-20"),
            competition="Friendly",
            neutral=True,
            home_confederation="CONMEBOL",
            away_confederation="CONMEBOL",
            home_fifa_rank=1,
            away_fifa_rank=2,
            tournament_stage="Unknown",
        )

        self.assertAlmostEqual(train_row["home_elo_pre"], infer_row["home_elo_pre"], places=6)
        self.assertAlmostEqual(train_row["away_elo_pre"], infer_row["away_elo_pre"], places=6)
        self.assertAlmostEqual(train_row["elo_win_prob"], infer_row["elo_win_prob"], places=6)
        self.assertAlmostEqual(train_row["home_form_last5"], infer_row["home_form_last5"], places=6)

    def test_alias_in_history_resolves_to_same_state_as_canonical(self):
        """History with aliased names must produce identical tracker state to canonical names.

        If history CSV has 'USA' and the caller passes 'United States', both paths
        must normalise before replay so the tracker key is always 'United States'.
        """
        from src.features.build_features import build_feature_table
        from src.app.predict_match import build_pre_match_row

        # Training data uses the alias "USA"
        training_df = pd.DataFrame({
            "date": ["2026-05-01", "2026-05-10"],
            "home_team": ["USA", "Mexico"],
            "away_team": ["Mexico", "USA"],
            "home_score": [2, 1],
            "away_score": [0, 2],
            "neutral": [False, False],
        })
        features = build_feature_table(training_df, _cfg())
        # After training normalization the second row has "United States" as away_team.
        train_row_usa = features[features["away_team"] == "United States"].iloc[0]

        # Inference: history also has "USA"; caller asks for "United States"
        history_alias = training_df.iloc[:1].copy()  # only the first match
        infer_row = build_pre_match_row(
            history_df=history_alias,
            home_team="Mexico",
            away_team="United States",
            match_date="2026-05-10",
            competition="Friendly",
            neutral=False,
            home_confederation="CONCACAF",
            away_confederation="CONCACAF",
            home_fifa_rank=20,
            away_fifa_rank=13,
            tournament_stage="Unknown",
            cfg=_cfg(),
        )

        self.assertAlmostEqual(
            float(train_row_usa["away_elo_pre"]),
            float(infer_row["away_elo_pre"].iloc[0]),
            places=6,
            msg="Elo state for 'United States' must match whether history used 'USA' or 'United States'",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
