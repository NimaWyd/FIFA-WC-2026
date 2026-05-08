"""Phase 4 tests: recency weighting, attack/defense, opponent-adjusted form,
competition-aware Elo, scoreline model, and training/inference consistency.

Run with pytest:
    python -m pytest tests/test_phase4.py -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.competition_weights import (
    get_stage_importance,
    normalize_tournament_stage,
    COMPETITION_K_MULTIPLIERS,
)
from src.features.elo import EloConfig, update_ratings
from src.features.match_row_builder import build_match_row
from src.features.state_tracker import TeamStateTracker
from src.models.scoreline_model import ScoreModelParams, TeamDependentScoreModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(recency_halflife=180.0) -> dict:
    return {
        "features": {
            "form_window": 5,
            "elo_k_factor": 40.0,
            "elo_home_advantage": 100.0,
            "default_fifa_rank": 75,
            "recency_halflife_days": recency_halflife,
        }
    }


def _make_tracker_with_history(n_matches: int = 6) -> TeamStateTracker:
    """Return a tracker that has processed N wins for Brazil vs Weaker."""
    tracker = TeamStateTracker(_cfg())
    base = pd.Timestamp("2025-01-01")
    for i in range(n_matches):
        tracker.update(
            "Brazil", "Weaker",
            home_goals=2, away_goals=0,
            neutral=False,
            date=base + pd.Timedelta(days=30 * i),
            competition="International Friendly",
        )
    return tracker


def _features_df(n: int = 30) -> pd.DataFrame:
    """Minimal features DataFrame for scoreline model fitting."""
    import numpy as np
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "home_score": rng.integers(0, 5, n),
        "away_score": rng.integers(0, 4, n),
        "neutral": rng.integers(0, 2, n),
        "home_attack_w5": rng.uniform(0.5, 3.0, n),
        "away_attack_w5": rng.uniform(0.5, 3.0, n),
        "home_defense_w5": rng.uniform(0.3, 2.5, n),
        "away_defense_w5": rng.uniform(0.3, 2.5, n),
        "home_goals_for_last5": rng.uniform(0.5, 2.5, n),
        "away_goals_for_last5": rng.uniform(0.5, 2.5, n),
        "home_goals_against_last5": rng.uniform(0.5, 2.5, n),
        "away_goals_against_last5": rng.uniform(0.5, 2.5, n),
    })


# ---------------------------------------------------------------------------
# Competition-aware Elo
# ---------------------------------------------------------------------------

class TestCompetitionAwareElo(unittest.TestCase):
    def test_world_cup_k_greater_than_friendly(self):
        """World Cup matches should produce larger rating changes than friendlies."""
        cfg = EloConfig(k_factor=40.0, home_advantage=100.0)
        wc_home, wc_away = update_ratings(1500, 1500, 2, 0, False, cfg,
                                          competition_k_multiplier=2.0)
        fr_home, fr_away = update_ratings(1500, 1500, 2, 0, False, cfg,
                                          competition_k_multiplier=0.5)
        self.assertGreater(wc_home - 1500, fr_home - 1500)

    def test_default_multiplier_unchanged(self):
        """Default multiplier=1.0 must reproduce original behaviour."""
        cfg = EloConfig(k_factor=40.0, home_advantage=100.0)
        new_home, new_away = update_ratings(1500, 1500, 1, 0, False, cfg,
                                            competition_k_multiplier=1.0)
        ref_home, ref_away = update_ratings(1500, 1500, 1, 0, False, cfg)
        self.assertAlmostEqual(new_home, ref_home, places=10)
        self.assertAlmostEqual(new_away, ref_away, places=10)

    def test_state_tracker_uses_competition_k(self):
        """Tracker Elo change for World Cup > friendly with same scoreline."""
        t_wc = TeamStateTracker(_cfg())
        t_wc.update("A", "B", 2, 0, False, pd.Timestamp("2025-06-01"),
                    competition="FIFA World Cup")

        t_fr = TeamStateTracker(_cfg())
        t_fr.update("A", "B", 2, 0, False, pd.Timestamp("2025-06-01"),
                    competition="International Friendly")

        self.assertGreater(t_wc.elo("A"), t_fr.elo("A"))
        self.assertLess(t_wc.elo("B"), t_fr.elo("B"))

    def test_k_multipliers_dict_has_required_competitions(self):
        required = ["FIFA World Cup", "International Friendly"]
        for comp in required:
            self.assertIn(comp, COMPETITION_K_MULTIPLIERS)

    def test_world_cup_k_greater_than_friendly_k(self):
        self.assertGreater(
            COMPETITION_K_MULTIPLIERS["FIFA World Cup"],
            COMPETITION_K_MULTIPLIERS["International Friendly"],
        )


# ---------------------------------------------------------------------------
# Recency-weighted form
# ---------------------------------------------------------------------------

class TestRecencyWeightedForm(unittest.TestCase):
    def test_more_recent_matches_matter_more(self):
        """After a recent win following earlier losses, recency-weighted form
        should be higher than plain average."""
        tracker = TeamStateTracker(_cfg(recency_halflife=30.0))
        base = pd.Timestamp("2025-01-01")
        # 4 early losses
        for i in range(4):
            tracker.update("Team", "Opp", 0, 1, True,
                           base + pd.Timedelta(days=i * 7))
        # 1 very recent win
        tracker.update("Team", "Opp", 3, 0, True,
                       base + pd.Timedelta(days=365))

        plain_form = tracker.form_window("Team", 5)       # plain avg
        rw_form = tracker.form_recency_weighted("Team", 5)  # recency-weighted

        # The recent win should dominate in the recency-weighted version
        self.assertGreater(rw_form, plain_form)

    def test_recency_weighted_form_is_bounded(self):
        tracker = _make_tracker_with_history(10)
        rw = tracker.form_recency_weighted("Brazil", 5)
        self.assertGreaterEqual(rw, 0.0)
        self.assertLessEqual(rw, 3.0)

    def test_recency_form_default_for_no_history(self):
        tracker = TeamStateTracker(_cfg())
        self.assertAlmostEqual(tracker.form_recency_weighted("NewTeam", 5), 1.5)


# ---------------------------------------------------------------------------
# Multi-window form
# ---------------------------------------------------------------------------

class TestMultiWindowForm(unittest.TestCase):
    def test_w3_uses_only_last_3(self):
        """After 5 matches (1 win, then 4 losses) form_w3 != form_w5."""
        tracker = TeamStateTracker(_cfg())
        base = pd.Timestamp("2025-01-01")
        tracker.update("T", "O", 2, 0, True, base)                           # win
        for i in range(1, 5):
            tracker.update("T", "O", 0, 1, True, base + pd.Timedelta(days=i))  # losses

        w3 = tracker.form_window("T", 3)
        w5 = tracker.form_window("T", 5)
        # last 3 all losses = 0; last 5 has 1 win
        self.assertAlmostEqual(w3, 0.0)
        self.assertGreater(w5, 0.0)

    def test_w10_returns_default_with_few_matches(self):
        """With only 3 matches, form_w10 should still return a valid number."""
        tracker = _make_tracker_with_history(3)
        w10 = tracker.form_window("Brazil", 10)
        self.assertGreaterEqual(w10, 0.0)
        self.assertLessEqual(w10, 3.0)

    def test_match_row_contains_w3_w10_keys(self):
        tracker = TeamStateTracker(_cfg())
        row = build_match_row(
            tracker=tracker,
            home_team="Brazil", away_team="France",
            match_date=pd.Timestamp("2026-06-14"),
            competition="FIFA World Cup", neutral=False,
            home_confederation="CONMEBOL", away_confederation="UEFA",
            home_fifa_rank=2, away_fifa_rank=3,
            tournament_stage="Group Stage",
        )
        for key in ("home_form_w3", "away_form_w3", "home_form_w10",
                    "away_form_w10", "home_form_rw5", "away_form_rw5"):
            self.assertIn(key, row, f"Missing key: {key}")


# ---------------------------------------------------------------------------
# Attack / defense decomposition
# ---------------------------------------------------------------------------

class TestAttackDefenseDecomposition(unittest.TestCase):
    def test_attack_updates_correctly(self):
        tracker = TeamStateTracker(_cfg())
        tracker.update("A", "B", 3, 1, True, pd.Timestamp("2025-01-01"))
        self.assertAlmostEqual(tracker.attack_rating("A", 5), 3.0)
        self.assertAlmostEqual(tracker.attack_rating("B", 5), 1.0)

    def test_defense_updates_correctly(self):
        tracker = TeamStateTracker(_cfg())
        tracker.update("A", "B", 3, 1, True, pd.Timestamp("2025-01-01"))
        # A conceded 1, B conceded 3
        self.assertAlmostEqual(tracker.defense_rating("A", 5), 1.0)
        self.assertAlmostEqual(tracker.defense_rating("B", 5), 3.0)

    def test_recency_weighted_attack_differs_from_plain(self):
        """After a recent high-scoring match, rw_attack > plain attack."""
        tracker = TeamStateTracker(_cfg(recency_halflife=30.0))
        base = pd.Timestamp("2025-01-01")
        for i in range(4):
            tracker.update("A", "B", 1, 0, True, base + pd.Timedelta(days=i * 7))
        # Recent big win
        tracker.update("A", "B", 5, 0, True, base + pd.Timedelta(days=365))
        plain_atk = tracker.attack_rating("A", 5, recency=False)
        rw_atk = tracker.attack_rating("A", 5, recency=True)
        self.assertGreater(rw_atk, plain_atk)

    def test_match_row_has_attack_defense_keys(self):
        tracker = TeamStateTracker(_cfg())
        row = build_match_row(
            tracker=tracker,
            home_team="Brazil", away_team="France",
            match_date=pd.Timestamp("2026-06-14"),
            competition="FIFA World Cup", neutral=False,
            home_confederation="CONMEBOL", away_confederation="UEFA",
            home_fifa_rank=2, away_fifa_rank=3,
            tournament_stage="Group Stage",
        )
        expected_keys = [
            "home_attack_w5", "away_attack_w5",
            "home_defense_w5", "away_defense_w5",
            "home_attack_rw5", "away_attack_rw5",
            "home_defense_rw5", "away_defense_rw5",
        ]
        for k in expected_keys:
            self.assertIn(k, row, f"Missing key: {k}")

    def test_defaults_when_no_history(self):
        tracker = TeamStateTracker(_cfg())
        self.assertAlmostEqual(tracker.attack_rating("NewTeam", 5), 1.0)
        self.assertAlmostEqual(tracker.defense_rating("NewTeam", 5), 1.0)


# ---------------------------------------------------------------------------
# Opponent-adjusted form
# ---------------------------------------------------------------------------

class TestOpponentAdjustedForm(unittest.TestCase):
    def test_win_vs_strong_opp_scores_higher_than_weak(self):
        """Same result against a stronger opponent should yield higher adj_form."""
        base_date = pd.Timestamp("2025-01-01")

        tracker_strong = TeamStateTracker(_cfg())
        # Give the opponent a high Elo
        tracker_strong.update("BigOpp", "Weak1", 5, 0, True, base_date)
        tracker_strong.update("BigOpp", "Weak2", 5, 0, True,
                              base_date + pd.Timedelta(days=7))
        # Now Team beats BigOpp
        tracker_strong.update("Team", "BigOpp", 1, 0, True,
                              base_date + pd.Timedelta(days=14))

        tracker_weak = TeamStateTracker(_cfg())
        # Opponent has base Elo
        tracker_weak.update("Team", "BaseOpp", 1, 0, True, base_date)

        strong_adj = tracker_strong.opp_adjusted_form("Team", 5)
        weak_adj = tracker_weak.opp_adjusted_form("Team", 5)
        self.assertGreater(strong_adj, weak_adj)

    def test_opp_adj_form_default(self):
        tracker = TeamStateTracker(_cfg())
        self.assertAlmostEqual(tracker.opp_adjusted_form("Unknown", 5), 1.5)

    def test_opp_adj_attack_default(self):
        tracker = TeamStateTracker(_cfg())
        self.assertAlmostEqual(tracker.opp_adjusted_attack("Unknown", 5), 1.0)

    def test_opp_adj_defense_default(self):
        tracker = TeamStateTracker(_cfg())
        self.assertAlmostEqual(tracker.opp_adjusted_defense("Unknown", 5), 1.0)

    def test_opp_adjusted_uses_only_prior_opponent_strength(self):
        """Opponent Elo stored is pre-match, not post-match — no leakage."""
        tracker = TeamStateTracker(_cfg())
        base = pd.Timestamp("2025-06-01")
        # Opponent starts at base Elo 1500
        tracker.update("Team", "Opp", 2, 0, True, base)
        # Opponent rating changed after the match — that change must NOT affect
        # the opp_elo_pre stored for Team's history entry.
        hist = tracker._history_slice("Team", 1)
        self.assertAlmostEqual(hist[0]["opp_elo_pre"], 1500.0, places=4)

    def test_match_row_has_adj_keys(self):
        tracker = TeamStateTracker(_cfg())
        row = build_match_row(
            tracker=tracker,
            home_team="A", away_team="B",
            match_date=pd.Timestamp("2026-06-01"),
            competition="FIFA World Cup", neutral=False,
            home_confederation="UEFA", away_confederation="UEFA",
            home_fifa_rank=5, away_fifa_rank=10,
            tournament_stage="Group Stage",
        )
        for k in ("home_adj_form_w5", "away_adj_form_w5",
                  "home_adj_attack_w5", "away_adj_attack_w5",
                  "home_adj_defense_w5", "away_adj_defense_w5"):
            self.assertIn(k, row, f"Missing key: {k}")


# ---------------------------------------------------------------------------
# Tournament stage
# ---------------------------------------------------------------------------

class TestTournamentStage(unittest.TestCase):
    def test_normalize_group_stage(self):
        self.assertEqual(normalize_tournament_stage("Group Stage"), "group_stage")
        self.assertEqual(normalize_tournament_stage("GROUP STAGE"), "group_stage")

    def test_normalize_final(self):
        self.assertEqual(normalize_tournament_stage("final"), "final")
        self.assertEqual(normalize_tournament_stage("Grand Final"), "final")

    def test_normalize_quarter_final(self):
        self.assertEqual(normalize_tournament_stage("Quarter-Final"), "quarterfinal")
        self.assertEqual(normalize_tournament_stage("Quarter-finals"), "quarterfinal")

    def test_normalize_unknown(self):
        result = normalize_tournament_stage("Unknown")
        self.assertEqual(result, "unknown")

    def test_stage_importance_ordering(self):
        self.assertLess(
            get_stage_importance("Group Stage"),
            get_stage_importance("Semi-Final"),
        )
        self.assertLess(
            get_stage_importance("Semi-Final"),
            get_stage_importance("Final"),
        )

    def test_stage_importance_numeric(self):
        self.assertIsInstance(get_stage_importance("Final"), int)
        self.assertGreater(get_stage_importance("Final"), 0)

    def test_match_row_has_stage_importance(self):
        tracker = TeamStateTracker(_cfg())
        row = build_match_row(
            tracker=tracker,
            home_team="A", away_team="B",
            match_date=pd.Timestamp("2026-07-01"),
            competition="FIFA World Cup", neutral=True,
            home_confederation="UEFA", away_confederation="CONMEBOL",
            home_fifa_rank=3, away_fifa_rank=5,
            tournament_stage="Semi-Final",
        )
        self.assertIn("stage_importance", row)
        self.assertEqual(row["tournament_stage"], "semifinal")
        self.assertGreater(row["stage_importance"], 0)

    def test_unknown_stage_safe(self):
        row = build_match_row(
            tracker=TeamStateTracker(_cfg()),
            home_team="A", away_team="B",
            match_date=pd.Timestamp("2026-01-01"),
            competition="Friendly", neutral=False,
            home_confederation="UEFA", away_confederation="UEFA",
            home_fifa_rank=10, away_fifa_rank=10,
            tournament_stage="Unknown",
        )
        self.assertIn("stage_importance", row)
        self.assertIsInstance(row["stage_importance"], int)


# ---------------------------------------------------------------------------
# Scoreline model
# ---------------------------------------------------------------------------

class TestTeamDependentScoreModel(unittest.TestCase):
    def test_fit_sets_base_lambdas(self):
        model = TeamDependentScoreModel()
        df = _features_df(50)
        model.fit(df)
        self.assertTrue(model._fitted)
        self.assertGreater(model.params.base_home_lambda, 0)
        self.assertGreater(model.params.base_away_lambda, 0)

    def test_predict_lambdas_are_team_specific(self):
        """Higher home attack (same defense) → higher home lambda."""
        model = TeamDependentScoreModel()
        model.fit(_features_df(50))

        # Keep defense constant; vary only home attack
        lh_strong, _ = model.predict_lambdas(
            home_attack=3.0, away_attack=1.5,
            home_defense=1.0, away_defense=1.0,
            neutral=True,
        )
        lh_weak, _ = model.predict_lambdas(
            home_attack=0.5, away_attack=1.5,
            home_defense=1.0, away_defense=1.0,
            neutral=True,
        )
        self.assertGreater(lh_strong, lh_weak)

        # Keep attack constant; weaker away defense (concedes more) → higher home lambda
        lh_easy, _ = model.predict_lambdas(
            home_attack=1.5, away_attack=1.0,
            home_defense=1.0, away_defense=2.5,  # weak defense: concedes a lot
            neutral=True,
        )
        lh_hard, _ = model.predict_lambdas(
            home_attack=1.5, away_attack=1.0,
            home_defense=1.0, away_defense=0.4,  # strong defense: concedes little
            neutral=True,
        )
        self.assertGreater(lh_easy, lh_hard)

    def test_home_factor_applied_on_non_neutral(self):
        """Home lambda should be higher on non-neutral ground."""
        model = TeamDependentScoreModel()
        model.fit(_features_df(50))

        lh_home, _ = model.predict_lambdas(1.5, 1.5, 1.0, 1.0, neutral=False)
        lh_neutral, _ = model.predict_lambdas(1.5, 1.5, 1.0, 1.0, neutral=True)
        self.assertGreaterEqual(lh_home, lh_neutral)

    def test_lambdas_are_positive(self):
        model = TeamDependentScoreModel()
        model.fit(_features_df(50))
        lh, la = model.predict_lambdas(1.0, 1.0, 1.0, 1.0, neutral=False)
        self.assertGreater(lh, 0)
        self.assertGreater(la, 0)

    def test_predict_lambdas_from_row(self):
        model = TeamDependentScoreModel()
        model.fit(_features_df(50))
        row = {
            "home_attack_w5": 1.8,
            "away_attack_w5": 1.2,
            "home_defense_w5": 0.8,
            "away_defense_w5": 1.1,
            "neutral": 0,
        }
        lh, la = model.predict_lambdas_from_row(row)
        self.assertGreater(lh, 0)
        self.assertGreater(la, 0)

    def test_fallback_to_goals_for_columns(self):
        """Model must fall back gracefully when Phase 4 columns are absent."""
        model = TeamDependentScoreModel()
        model.fit(_features_df(30))
        row = {
            "home_goals_for_last5": 1.5,
            "away_goals_for_last5": 1.0,
            "home_goals_against_last5": 1.2,
            "away_goals_against_last5": 0.9,
            "neutral": 0,
        }
        lh, la = model.predict_lambdas_from_row(row)
        self.assertGreater(lh, 0)
        self.assertGreater(la, 0)

    def test_top_scorelines_sum_to_reasonable_probability(self):
        model = TeamDependentScoreModel()
        scorelines = model.top_scorelines(1.5, 1.2, max_goals=5, top_n=3)
        self.assertEqual(len(scorelines), 3)
        total_prob = sum(p for _, p in scorelines)
        self.assertGreater(total_prob, 0)
        self.assertLess(total_prob, 1.0)

    def test_top_scorelines_are_sorted_descending(self):
        model = TeamDependentScoreModel()
        scorelines = model.top_scorelines(1.5, 1.2, max_goals=5, top_n=5)
        probs = [p for _, p in scorelines]
        self.assertEqual(probs, sorted(probs, reverse=True))

    def test_save_and_load(self, tmp_path=None):
        import tempfile, os
        model = TeamDependentScoreModel()
        model.fit(_features_df(50))

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "scoreline_params.json"
            model.save(path)
            loaded = TeamDependentScoreModel.load(path)

        self.assertAlmostEqual(
            model.params.base_home_lambda, loaded.params.base_home_lambda, places=6
        )
        self.assertAlmostEqual(
            model.params.home_advantage_factor,
            loaded.params.home_advantage_factor, places=6,
        )

    def test_global_lambda_not_used_for_all_teams(self):
        """Confirm that different team strengths produce different lambdas."""
        model = TeamDependentScoreModel()
        model.fit(_features_df(60))

        lh_strong, _ = model.predict_lambdas(3.0, 1.0, 0.5, 2.0, neutral=True)
        lh_weak, _ = model.predict_lambdas(0.5, 3.0, 2.5, 0.3, neutral=True)
        self.assertNotAlmostEqual(lh_strong, lh_weak, places=2)


# ---------------------------------------------------------------------------
# No leakage
# ---------------------------------------------------------------------------

class TestNoLeakage(unittest.TestCase):
    def test_opp_elo_pre_is_pre_match(self):
        """History must store opponent Elo BEFORE the match, not after."""
        tracker = TeamStateTracker(_cfg())
        date = pd.Timestamp("2025-01-01")
        # Both teams start at 1500
        tracker.update("A", "B", 3, 0, True, date)
        # After the match B's Elo dropped from 1500.
        # The stored opp_elo_pre for A's entry should be 1500 (pre-match).
        hist = tracker._history_slice("A", 1)
        self.assertAlmostEqual(hist[0]["opp_elo_pre"], 1500.0, places=4)

    def test_replay_produces_same_state_as_sequential_updates(self):
        """replay_history() must produce identical state to manual updates."""
        matches = pd.DataFrame({
            "date": ["2025-01-01", "2025-02-01"],
            "home_team": ["Brazil", "Argentina"],
            "away_team": ["Argentina", "Brazil"],
            "home_score": [2, 1],
            "away_score": [1, 1],
            "neutral": [False, True],
            "competition": ["Friendly", "Friendly"],
        })
        matches["date"] = pd.to_datetime(matches["date"])

        # Sequential
        t1 = TeamStateTracker(_cfg())
        for row in matches.itertuples(index=False):
            t1.update(row.home_team, row.away_team, row.home_score,
                      row.away_score, bool(row.neutral), pd.Timestamp(row.date),
                      competition=str(row.competition))

        # replay_history
        t2 = TeamStateTracker(_cfg())
        t2.replay_history(matches)

        self.assertAlmostEqual(t1.elo("Brazil"), t2.elo("Brazil"), places=6)
        self.assertAlmostEqual(t1.elo("Argentina"), t2.elo("Argentina"), places=6)

    def test_build_feature_table_no_future_leakage(self):
        """First match row must use base Elo — tracker cannot see future."""
        from src.features.build_features import build_feature_table
        df = pd.DataFrame({
            "date": ["2025-01-01", "2025-02-01", "2025-03-01"],
            "home_team": ["Brazil", "France", "Brazil"],
            "away_team": ["France", "Brazil", "France"],
            "home_score": [1, 0, 2],
            "away_score": [0, 1, 1],
            "neutral": [False, False, True],
        })
        features = build_feature_table(df, _cfg())
        # First match must have base Elo for both teams
        self.assertAlmostEqual(features.iloc[0]["home_elo_pre"], 1500.0, places=6)
        self.assertAlmostEqual(features.iloc[0]["away_elo_pre"], 1500.0, places=6)
        # Third match must have non-base Elo (teams appeared in matches 1 & 2)
        self.assertNotAlmostEqual(features.iloc[2]["home_elo_pre"], 1500.0, places=2)

    def test_training_inference_consistent_with_new_features(self):
        """New Phase 4 features must be identical in training and inference paths."""
        from src.features.build_features import build_feature_table

        matches = pd.DataFrame({
            "date": ["2025-01-01", "2025-02-01", "2025-03-01"],
            "home_team": ["Brazil", "France", "Argentina"],
            "away_team": ["Argentina", "Spain", "Brazil"],
            "home_score": [2, 1, 0],
            "away_score": [1, 0, 1],
            "neutral": [False, False, True],
        })
        cfg = _cfg()
        features = build_feature_table(matches, cfg)
        train_row = features.iloc[2]

        # Inference path: replay first two, then snapshot
        history = matches.iloc[:2].copy()
        history["date"] = pd.to_datetime(history["date"])
        tracker = TeamStateTracker(cfg)
        tracker.replay_history(history)
        infer_row = build_match_row(
            tracker=tracker,
            home_team="Argentina", away_team="Brazil",
            match_date=pd.Timestamp("2025-03-01"),
            competition="International Friendly", neutral=True,
            home_confederation="CONMEBOL", away_confederation="CONMEBOL",
            home_fifa_rank=1, away_fifa_rank=2,
            tournament_stage="Unknown",
        )

        for key in ("home_form_rw5", "home_attack_w5", "home_defense_w5",
                    "home_adj_form_w5", "home_form_w3", "home_form_w10"):
            self.assertAlmostEqual(
                float(train_row[key]),
                float(infer_row[key]),
                places=6,
                msg=f"Training/inference mismatch for {key}",
            )


# ---------------------------------------------------------------------------
# Schema stability
# ---------------------------------------------------------------------------

class TestSchemaStability(unittest.TestCase):
    def test_match_row_has_all_phase4_keys(self):
        tracker = TeamStateTracker(_cfg())
        row = build_match_row(
            tracker=tracker,
            home_team="X", away_team="Y",
            match_date=pd.Timestamp("2026-06-01"),
            competition="FIFA World Cup", neutral=False,
            home_confederation="UEFA", away_confederation="UEFA",
            home_fifa_rank=5, away_fifa_rank=8,
            tournament_stage="Final",
        )
        required_new = [
            "home_form_w3", "away_form_w3",
            "home_form_w10", "away_form_w10",
            "home_form_rw5", "away_form_rw5",
            "home_attack_w5", "away_attack_w5",
            "home_defense_w5", "away_defense_w5",
            "home_attack_rw5", "away_attack_rw5",
            "home_defense_rw5", "away_defense_rw5",
            "home_adj_form_w5", "away_adj_form_w5",
            "home_adj_attack_w5", "away_adj_attack_w5",
            "home_adj_defense_w5", "away_adj_defense_w5",
            "attack_diff_w5", "defense_diff_w5",
            "adj_form_diff_w5", "form_diff_w3", "form_diff_w10",
            "stage_importance",
        ]
        for k in required_new:
            self.assertIn(k, row, f"Missing Phase 4 key: {k}")

    def test_existing_phase1_keys_still_present(self):
        """Phase 1–3 keys must not be removed."""
        tracker = TeamStateTracker(_cfg())
        row = build_match_row(
            tracker=tracker,
            home_team="A", away_team="B",
            match_date=pd.Timestamp("2026-01-01"),
            competition="Friendly", neutral=False,
            home_confederation="UEFA", away_confederation="UEFA",
            home_fifa_rank=10, away_fifa_rank=15,
            tournament_stage="Unknown",
        )
        legacy = [
            "home_elo_pre", "away_elo_pre", "elo_win_prob",
            "home_form_last5", "away_form_last5",
            "home_goals_for_last5", "away_goals_for_last5",
            "home_goals_against_last5", "away_goals_against_last5",
            "home_rest_days_log", "away_rest_days_log",
            "home_long_break", "away_long_break",
            "elo_diff_home_away", "form_diff_home_away", "goal_balance_diff",
            "rank_diff", "competition_weight", "is_same_confederation",
        ]
        for k in legacy:
            self.assertIn(k, row, f"Legacy key removed: {k}")


class TestLambdaBounds(unittest.TestCase):
    """λ values must stay within realistic football bounds."""

    def setUp(self):
        self.model = TeamDependentScoreModel()
        self.model.fit(_features_df(50))

    def test_lambda_floor_extreme_weak_teams(self):
        """Very weak attack / very strong defence must not produce λ below 0.5."""
        lh, la = self.model.predict_lambdas(
            home_attack=0.01, away_attack=0.01,
            home_defense=10.0, away_defense=10.0,
            neutral=True,
        )
        self.assertGreaterEqual(lh, 0.5, f"λ_home={lh:.4f} below 0.5 floor")
        self.assertGreaterEqual(la, 0.5, f"λ_away={la:.4f} below 0.5 floor")

    def test_lambda_ceiling_extreme_strong_teams(self):
        """Very strong attack / very weak defence must not produce λ above 4.0."""
        lh, la = self.model.predict_lambdas(
            home_attack=20.0, away_attack=20.0,
            home_defense=10.0, away_defense=10.0,
            neutral=False,
        )
        self.assertLessEqual(lh, 4.0, f"λ_home={lh:.4f} exceeds 4.0 ceiling")
        self.assertLessEqual(la, 4.0, f"λ_away={la:.4f} exceeds 4.0 ceiling")


if __name__ == "__main__":
    unittest.main(verbosity=2)
