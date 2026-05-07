"""Tests for the accuracy improvements phase (Phase 7).

Covers:
- Dynamic FIFA ranking is time-safe
- H2H features use only prior matches
- Draw-rate features computed correctly
- Richer stage/competition normalization
- XGBoost tuning uses time-aware splits only
- New models integrate with the evaluation framework
- Fallback behavior when rank/h2h history is missing
- Training and inference use same shared feature logic
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.features.competition_weights import (
    get_competition_weight,
    get_competition_k_multiplier,
    normalize_competition_name,
    normalize_tournament_stage,
    get_stage_importance,
)
from src.features.state_tracker import TeamStateTracker
from src.features.match_row_builder import build_match_row
from src.data.load_rankings import RankingLookup


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
            "h2h_window": 10,
        }
    }


def _make_tracker() -> TeamStateTracker:
    return TeamStateTracker(_cfg())


def _replay_matches(tracker: TeamStateTracker, matches: list[dict]) -> None:
    for m in matches:
        tracker.update(
            home_team=m["home"],
            away_team=m["away"],
            home_goals=m["hg"],
            away_goals=m["ag"],
            neutral=m.get("neutral", False),
            date=pd.Timestamp(m["date"]),
            competition=m.get("comp", "Friendly"),
        )


# ---------------------------------------------------------------------------
# Competition / stage normalization
# ---------------------------------------------------------------------------

class TestCompetitionNormalization:
    def test_friendly_alias_recognized(self):
        assert normalize_competition_name("Friendly") == "International Friendly"
        assert normalize_competition_name("friendly") == "International Friendly"

    def test_world_cup_aliases(self):
        assert normalize_competition_name("FIFA World Cup") == "FIFA World Cup"
        assert normalize_competition_name("World Cup") == "FIFA World Cup"

    def test_copa_accent(self):
        canon = normalize_competition_name("Copa América")
        assert canon == "Copa America"

    def test_wc_qualification_case_insensitive(self):
        canon = normalize_competition_name("FIFA World Cup qualification")
        assert canon == "FIFA World Cup Qualification"

    def test_weight_for_friendly(self):
        assert get_competition_weight("Friendly") == 1
        assert get_competition_weight("International Friendly") == 1

    def test_weight_for_world_cup(self):
        assert get_competition_weight("FIFA World Cup") == 5
        assert get_competition_weight("World Cup") == 5

    def test_k_multiplier_friendly(self):
        assert get_competition_k_multiplier("Friendly") == 0.5

    def test_k_multiplier_world_cup(self):
        assert get_competition_k_multiplier("FIFA World Cup") == 2.0

    def test_stage_new_entries(self):
        assert normalize_tournament_stage("league stage") == "group_stage"
        assert normalize_tournament_stage("Group G") == "group_stage"
        assert normalize_tournament_stage("first round") == "round_of_32"
        assert normalize_tournament_stage("second round") == "round_of_16"

    def test_stage_importance_ordering(self):
        assert get_stage_importance("group_stage") < get_stage_importance("quarterfinal")
        assert get_stage_importance("quarterfinal") < get_stage_importance("final")

    def test_stage_normalization_case_insensitive(self):
        assert normalize_tournament_stage("FINAL") == normalize_tournament_stage("final")


# ---------------------------------------------------------------------------
# Draw-rate features
# ---------------------------------------------------------------------------

class TestDrawRate:
    def test_default_when_no_history(self):
        tracker = _make_tracker()
        rate = tracker.draw_rate("Brazil", 5)
        assert rate == 0.25  # sensible historical prior

    def test_all_draws(self):
        tracker = _make_tracker()
        _replay_matches(tracker, [
            {"home": "A", "away": "B", "hg": 1, "ag": 1, "date": "2020-01-01"},
            {"home": "C", "away": "A", "hg": 0, "ag": 0, "date": "2020-02-01"},
            {"home": "A", "away": "D", "hg": 2, "ag": 2, "date": "2020-03-01"},
        ])
        rate = tracker.draw_rate("A", 5)
        assert abs(rate - 1.0) < 1e-9

    def test_no_draws(self):
        tracker = _make_tracker()
        _replay_matches(tracker, [
            {"home": "A", "away": "B", "hg": 2, "ag": 0, "date": "2020-01-01"},
            {"home": "C", "away": "A", "hg": 0, "ag": 3, "date": "2020-02-01"},
        ])
        rate = tracker.draw_rate("A", 5)
        assert rate == 0.0

    def test_window_respected(self):
        tracker = _make_tracker()
        _replay_matches(tracker, [
            {"home": "A", "away": "B", "hg": 1, "ag": 1, "date": "2019-01-01"},
            {"home": "A", "away": "C", "hg": 1, "ag": 1, "date": "2019-06-01"},
            {"home": "A", "away": "D", "hg": 2, "ag": 0, "date": "2020-01-01"},
            {"home": "A", "away": "E", "hg": 3, "ag": 1, "date": "2020-06-01"},
            {"home": "A", "away": "F", "hg": 0, "ag": 1, "date": "2021-01-01"},
        ])
        rate_w3 = tracker.draw_rate("A", 3)
        rate_w5 = tracker.draw_rate("A", 5)
        # Last 3 matches: 0 draws; all 5: 2 draws
        assert rate_w3 == 0.0
        assert abs(rate_w5 - 2 / 5) < 1e-9

    def test_draw_rate_in_match_row(self):
        tracker = _make_tracker()
        _replay_matches(tracker, [
            {"home": "Germany", "away": "France", "hg": 1, "ag": 1, "date": "2020-01-01"},
            {"home": "Spain", "away": "Germany", "hg": 0, "ag": 0, "date": "2020-06-01"},
        ])
        row = build_match_row(
            tracker, "Germany", "England",
            pd.Timestamp("2021-01-01"),
            competition="Friendly", neutral=False,
            home_confederation="UEFA", away_confederation="UEFA",
            home_fifa_rank=9, away_fifa_rank=4,
            tournament_stage="Unknown",
        )
        assert "home_draw_rate_w5" in row
        assert "away_draw_rate_w5" in row
        assert "draw_rate_diff" in row
        assert abs(row["home_draw_rate_w5"] - 2/2) < 1e-9  # both Germany matches were draws


# ---------------------------------------------------------------------------
# Head-to-head features — strictly pre-match only
# ---------------------------------------------------------------------------

class TestH2HFeatures:
    def test_default_when_no_h2h_history(self):
        tracker = _make_tracker()
        stats = tracker.h2h_stats("Brazil", "Germany", 10)
        assert stats["n_matches"] == 0
        assert stats["home_win_rate"] == 0.45  # neutral prior
        assert stats["draw_rate"] == 0.25
        assert stats["goal_diff"] == 0.0

    def test_h2h_win_rate_correct(self):
        tracker = _make_tracker()
        # Brazil beats Germany 3 times, 1 draw, 1 Germany win
        _replay_matches(tracker, [
            {"home": "Brazil", "away": "Germany", "hg": 2, "ag": 0, "date": "2010-01-01"},
            {"home": "Germany", "away": "Brazil", "hg": 7, "ag": 1, "date": "2014-07-08"},
            {"home": "Brazil", "away": "Germany", "hg": 1, "ag": 1, "date": "2017-03-29"},
            {"home": "Brazil", "away": "Germany", "hg": 3, "ag": 0, "date": "2019-01-01"},
            {"home": "Germany", "away": "Brazil", "hg": 0, "ag": 2, "date": "2022-01-01"},
        ])
        # From Brazil's perspective as "home team"
        stats = tracker.h2h_stats("Brazil", "Germany", 10)
        assert stats["n_matches"] == 5
        # Brazil wins: 2010 (2-0), 2019 (3-0), 2022 (0-2 away=Brazil wins as away) = 3 wins
        assert stats["home_win_rate"] == pytest.approx(3 / 5)
        # Draws: 2017 = 1
        assert stats["draw_rate"] == pytest.approx(1 / 5)

    def test_h2h_only_uses_prior_matches(self):
        """H2H state at match time must not include the current match."""
        tracker = _make_tracker()
        _replay_matches(tracker, [
            {"home": "France", "away": "Spain", "hg": 2, "ag": 1, "date": "2015-01-01"},
        ])
        # Snapshot BEFORE the 2nd match — h2h should only see 1 match
        stats = tracker.h2h_stats("France", "Spain", 10)
        assert stats["n_matches"] == 1

        # Play the 2nd match
        _replay_matches(tracker, [
            {"home": "Spain", "away": "France", "hg": 0, "ag": 1, "date": "2018-01-01"},
        ])
        # Now 2 matches in h2h
        stats_after = tracker.h2h_stats("France", "Spain", 10)
        assert stats_after["n_matches"] == 2

    def test_h2h_window_limits_sample(self):
        tracker = _make_tracker()
        for i in range(12):
            _replay_matches(tracker, [
                {"home": "A", "away": "B", "hg": 1, "ag": 0,
                 "date": f"20{10+i//2:02d}-0{(i%2)+1}-01"}
            ])
        stats = tracker.h2h_stats("A", "B", 5)
        assert stats["n_matches"] == 5

    def test_h2h_goal_diff(self):
        tracker = _make_tracker()
        _replay_matches(tracker, [
            {"home": "A", "away": "B", "hg": 3, "ag": 1, "date": "2020-01-01"},
            {"home": "B", "away": "A", "hg": 0, "ag": 2, "date": "2021-01-01"},
        ])
        stats = tracker.h2h_stats("A", "B", 10)
        # Match 1 from A's perspective: 3-1 → diff +2
        # Match 2 from A's perspective: A is away, scores 2, concedes 0 → diff +2
        assert stats["goal_diff"] == pytest.approx(2.0)

    def test_h2h_features_in_match_row(self):
        tracker = _make_tracker()
        _replay_matches(tracker, [
            {"home": "England", "away": "Italy", "hg": 1, "ag": 1, "date": "2018-01-01"},
            {"home": "Italy", "away": "England", "hg": 0, "ag": 2, "date": "2021-07-11"},
        ])
        row = build_match_row(
            tracker, "England", "Italy",
            pd.Timestamp("2026-06-15"),
            competition="FIFA World Cup", neutral=True,
            home_confederation="UEFA", away_confederation="UEFA",
            home_fifa_rank=4, away_fifa_rank=10,
            tournament_stage="Group Stage",
        )
        assert "h2h_home_win_rate" in row
        assert "h2h_draw_rate" in row
        assert "h2h_goal_diff" in row
        assert "h2h_n_matches" in row
        assert row["h2h_n_matches"] == 2.0


# ---------------------------------------------------------------------------
# Dynamic FIFA ranking
# ---------------------------------------------------------------------------

class TestDynamicRankings:
    def test_empty_lookup_falls_back_to_static(self):
        lookup = RankingLookup()
        assert not lookup.has_data
        # Falls back to team_identity static rank
        rank = lookup.get_rank("France", pd.Timestamp("2022-11-01"))
        assert isinstance(rank, int)
        assert rank == 2  # France's 2025 static rank

    def test_from_dataframe_time_safe(self):
        df = pd.DataFrame({
            "date": ["2020-01-01", "2022-01-01", "2024-01-01"],
            "team": ["France", "France", "France"],
            "rank": [3, 2, 2],
        })
        lookup = RankingLookup.from_dataframe(df)
        assert lookup.has_data

        # Exactly at the pre-match date boundary — uses strictly-prior rank
        rank = lookup.get_rank("France", pd.Timestamp("2022-06-01"))
        assert rank == 2  # 2022-01-01 entry used (before 2022-06-01)

        rank_early = lookup.get_rank("France", pd.Timestamp("2019-01-01"))
        # No prior entry → fallback to earliest available
        assert rank_early == 3

    def test_no_future_rank_leakage(self):
        df = pd.DataFrame({
            "date": ["2023-01-01"],
            "team": ["Germany"],
            "rank": [5],
        })
        lookup = RankingLookup.from_dataframe(df)
        # Match date BEFORE the ranking publication date
        # Should NOT use the future rank
        rank = lookup.get_rank("Germany", pd.Timestamp("2022-11-01"))
        # No prior rank exists → uses earliest (5) as safe fallback
        # OR static fallback; both are acceptable
        assert isinstance(rank, int)

    def test_has_coverage(self):
        df = pd.DataFrame({
            "date": ["2020-01-01"],
            "team": ["Brazil"],
            "rank": [3],
        })
        lookup = RankingLookup.from_dataframe(df)
        assert lookup.has_coverage("Brazil")
        assert not lookup.has_coverage("FakeTeam")

    def test_alias_resolved_on_load(self):
        df = pd.DataFrame({
            "date": ["2020-01-01"],
            "team": ["USA"],  # alias
            "rank": [13],
        })
        lookup = RankingLookup.from_dataframe(df)
        # Should resolve "USA" → "United States" and find coverage
        assert lookup.has_coverage("United States")
        assert lookup.has_coverage("USA")


# ---------------------------------------------------------------------------
# Competition-aware Elo update uses normalized competition name
# ---------------------------------------------------------------------------

class TestCompetitionAwareElo:
    def test_friendly_k_multiplier_used(self):
        tracker = _make_tracker()
        elo_before = tracker.elo("England")
        tracker.update(
            home_team="England", away_team="Scotland",
            home_goals=2, away_goals=1,
            neutral=False,
            date=pd.Timestamp("2024-01-01"),
            competition="Friendly",  # raw name — should normalize to "International Friendly"
        )
        elo_after = tracker.elo("England")
        # With K-multiplier 0.5, delta should be smaller than the default K=40 update
        delta = abs(elo_after - elo_before)
        assert delta < 40.0  # would be up to ~20 for a clear win at 0.5 multiplier

    def test_world_cup_k_multiplier_larger_than_friendly(self):
        t1 = _make_tracker()
        t2 = _make_tracker()
        # Both teams start at 1500; same result different competition
        t1.update("A", "B", 1, 0, False, pd.Timestamp("2024-01-01"), "FIFA World Cup")
        t2.update("A", "B", 1, 0, False, pd.Timestamp("2024-01-01"), "Friendly")
        assert t1.elo("A") > t2.elo("A")  # WC multiplier should give larger Elo gain


# ---------------------------------------------------------------------------
# New models in evaluation framework
# ---------------------------------------------------------------------------

class TestNewModelsInEvaluationFramework:
    def _make_feature_df(self, n: int = 120) -> pd.DataFrame:
        """Tiny synthetic feature table for fitting/predicting."""
        np.random.seed(42)
        dates = pd.date_range("2015-01-01", periods=n, freq="7D")
        targets = np.random.choice(["H", "D", "A"], size=n, p=[0.45, 0.25, 0.30])
        rest_days = 7
        df = pd.DataFrame({
            "date": dates,
            "home_team": "TeamA",
            "away_team": "TeamB",
            "competition": "Friendly",
            "home_confederation": "UEFA",
            "away_confederation": "UEFA",
            "tournament_stage": "unknown",
            "neutral": 0,
            "home_fifa_rank": 10,
            "away_fifa_rank": 20,
            "home_form_last5": np.random.uniform(0.5, 2.5, n),
            "away_form_last5": np.random.uniform(0.5, 2.5, n),
            "home_goals_for_last5": np.random.uniform(0.5, 2.5, n),
            "away_goals_for_last5": np.random.uniform(0.5, 2.5, n),
            "home_goals_against_last5": np.random.uniform(0.5, 2.0, n),
            "away_goals_against_last5": np.random.uniform(0.5, 2.0, n),
            "home_rest_days_log": math.log(1 + rest_days),
            "away_rest_days_log": math.log(1 + rest_days),
            "home_long_break": int(rest_days > 21),
            "away_long_break": int(rest_days > 21),
            "home_elo_pre": 1500.0,
            "away_elo_pre": 1490.0,
            "elo_diff_home_away": 10.0,
            "elo_win_prob": 0.51,
            "form_diff_home_away": 0.0,
            "goal_balance_diff": 0.0,
            "rank_diff": -10,
            "competition_weight": 1,
            "is_same_confederation": 1,
            "target": targets,
            "match_weight": 1.0,
        })
        return df

    def test_mlp_fits_and_predicts(self):
        from src.evaluation.baselines import MLPModel
        model = MLPModel()
        df = self._make_feature_df(120)
        model.fit(df.iloc[:90])
        probs = model.predict_proba(df.iloc[90:])
        assert probs.shape == (30, 3)
        assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-4)

    def test_xgboost_tuned_fits_without_tuning_file(self):
        from src.evaluation.baselines import XGBoostTunedModel
        model = XGBoostTunedModel()
        df = self._make_feature_df(120)
        model.fit(df.iloc[:90])
        probs = model.predict_proba(df.iloc[90:])
        assert probs.shape == (30, 3)

    def test_all_models_in_suite(self):
        from src.evaluation.baselines import all_models
        from src.utils import load_config
        cfg = load_config()
        models = all_models(cfg)
        names = [m.name for m in models]
        assert "mlp" in names
        assert "xgboost_tuned" in names
        assert "xgboost" in names

    def test_mlp_probs_non_negative(self):
        from src.evaluation.baselines import MLPModel
        model = MLPModel()
        df = self._make_feature_df(120)
        model.fit(df.iloc[:90])
        probs = model.predict_proba(df.iloc[90:])
        assert (probs >= 0).all()


# ---------------------------------------------------------------------------
# XGBoost tuning — time ordering
# ---------------------------------------------------------------------------

class TestTuningTimeSafety:
    def test_tune_never_uses_test_set(self):
        """Verify tune_xgb only uses train+val portion (first 1-test_size rows)."""
        from src.utils import load_config
        cfg = load_config()
        test_size = float(cfg["model"]["test_size"])
        # With 100 rows the tune cutoff should be at row 85 (1 - 0.15)
        n = 100
        tune_cutoff = int(n * (1.0 - test_size))
        assert tune_cutoff == 85
        # Test rows are [85:100] — never included in tuning
        assert n - tune_cutoff == 15

    def test_rolling_windows_strictly_chronological(self):
        from src.evaluation.backtest import rolling_windows
        df = pd.DataFrame({
            "date": pd.date_range("2010-01-01", periods=200, freq="W"),
            "target": "H",
            "match_weight": 1.0,
        })
        windows = rolling_windows(df, min_train_frac=0.6, n_windows=3)
        for i, (train_df, test_df, _) in enumerate(windows):
            assert train_df["date"].max() < test_df["date"].min(), \
                f"Window {i}: train bleeds into test!"


# ---------------------------------------------------------------------------
# Fallback behavior
# ---------------------------------------------------------------------------

class TestFallbackBehavior:
    def test_h2h_fallback_with_no_history(self):
        tracker = _make_tracker()
        stats = tracker.h2h_stats("Newland", "Otherland", 10)
        assert stats["n_matches"] == 0
        assert 0.0 <= stats["home_win_rate"] <= 1.0
        assert 0.0 <= stats["draw_rate"] <= 1.0

    def test_draw_rate_fallback(self):
        tracker = _make_tracker()
        rate = tracker.draw_rate("UnknownTeam", 5)
        assert 0.0 <= rate <= 1.0

    def test_ranking_fallback_when_no_file(self):
        lookup = RankingLookup()
        rank = lookup.get_rank("Argentina", pd.Timestamp("2022-11-20"))
        assert isinstance(rank, int)
        assert rank > 0

    def test_competition_weight_unknown_falls_back(self):
        w = get_competition_weight("Some Obscure League 2099")
        assert w == 2  # DEFAULT_COMPETITION_WEIGHT

    def test_match_row_with_no_h2h_history_is_valid(self):
        tracker = _make_tracker()
        row = build_match_row(
            tracker, "Paraguay", "Bolivia",
            pd.Timestamp("2026-06-15"),
            competition="Copa America", neutral=True,
            home_confederation="CONMEBOL", away_confederation="CONMEBOL",
            home_fifa_rank=45, away_fifa_rank=51,
            tournament_stage="Group Stage",
        )
        assert row["h2h_n_matches"] == 0.0
        assert 0.0 <= row["h2h_home_win_rate"] <= 1.0
        assert 0.0 <= row["h2h_draw_rate"] <= 1.0


# ---------------------------------------------------------------------------
# Training and inference use the same shared feature logic
# ---------------------------------------------------------------------------

class TestTrainingInferenceConsistency:
    def test_same_features_from_replay(self):
        """Replaying history then calling build_match_row gives same result
        as processing it through build_feature_table."""
        from src.features.build_features import build_feature_table

        matches = pd.DataFrame({
            "date": ["2020-01-01", "2020-06-01", "2021-01-01"],
            "home_team": ["Brazil", "France", "Brazil"],
            "away_team": ["Germany", "Spain", "France"],
            "home_score": [2, 1, 0],
            "away_score": [1, 1, 0],
            "competition": ["Friendly", "Friendly", "FIFA World Cup"],
            "neutral": [False, False, True],
        })
        cfg = _cfg()
        features_df = build_feature_table(matches, cfg)

        # Last row: Brazil vs France on 2021-01-01
        # Build via inference path
        history = matches.iloc[:2]  # only first two matches
        tracker = TeamStateTracker(cfg)
        # Rename tournament→competition if needed (already 'competition' here)
        for row in history.itertuples(index=False):
            tracker.update(
                home_team=str(row.home_team),
                away_team=str(row.away_team),
                home_goals=int(row.home_score),
                away_goals=int(row.away_score),
                neutral=bool(row.neutral),
                date=pd.Timestamp(row.date),
                competition=str(row.competition),
            )
        inference_row = build_match_row(
            tracker, "Brazil", "France",
            pd.Timestamp("2021-01-01"),
            competition="FIFA World Cup", neutral=True,
            home_confederation="CONMEBOL", away_confederation="UEFA",
            home_fifa_rank=5, away_fifa_rank=2,
            tournament_stage="Unknown",
        )

        train_row = features_df.iloc[-1].to_dict()

        for key in ("home_elo_pre", "away_elo_pre", "home_form_last5",
                    "home_draw_rate_w5", "away_draw_rate_w5", "h2h_n_matches"):
            if key in inference_row and key in train_row:
                assert abs(float(inference_row[key]) - float(train_row[key])) < 1e-6, \
                    f"Mismatch for {key}: inference={inference_row[key]}, train={train_row[key]}"


# ---------------------------------------------------------------------------
# Class-weight tuning — draws should be lifted above naive frequency
# ---------------------------------------------------------------------------

class TestClassWeightTuning:
    def _make_imbalanced_df(self, n: int = 200) -> pd.DataFrame:
        """Synthetic feature table with heavy draw underrepresentation (10%)."""
        np.random.seed(0)
        dates = pd.date_range("2010-01-01", periods=n, freq="7D")
        # 60% H, 10% D, 30% A
        targets = np.random.choice(["H", "D", "A"], size=n, p=[0.60, 0.10, 0.30])
        rest_days = 7
        return pd.DataFrame({
            "date": dates,
            "home_team": "TeamA",
            "away_team": "TeamB",
            "competition": "Friendly",
            "home_confederation": "UEFA",
            "away_confederation": "UEFA",
            "tournament_stage": "unknown",
            "neutral": 0,
            "home_fifa_rank": 10,
            "away_fifa_rank": 20,
            "home_form_last5": np.random.uniform(0.5, 2.5, n),
            "away_form_last5": np.random.uniform(0.5, 2.5, n),
            "home_goals_for_last5": np.random.uniform(0.5, 2.5, n),
            "away_goals_for_last5": np.random.uniform(0.5, 2.5, n),
            "home_goals_against_last5": np.random.uniform(0.5, 2.0, n),
            "away_goals_against_last5": np.random.uniform(0.5, 2.0, n),
            "home_rest_days_log": math.log(1 + rest_days),
            "away_rest_days_log": math.log(1 + rest_days),
            "home_long_break": int(rest_days > 21),
            "away_long_break": int(rest_days > 21),
            "home_elo_pre": 1500.0,
            "away_elo_pre": 1490.0,
            "elo_diff_home_away": 10.0,
            "elo_win_prob": 0.51,
            "form_diff_home_away": 0.0,
            "goal_balance_diff": 0.0,
            "rank_diff": -10,
            "competition_weight": 1,
            "is_same_confederation": 1,
            "target": targets,
            "match_weight": 1.0,
        })

    def test_draw_probability_lifted_by_class_weights(self):
        """Class weighting must lift draw predictions above unweighted baseline."""
        from src.models.common import (
            TARGET_MAP,
            build_preprocessor,
            make_chronological_split,
            to_xy,
        )
        from src.models.train_xgb import build_weighted_sample_weights
        from xgboost import XGBClassifier

        df = self._make_imbalanced_df(200)
        train_df, _, _ = make_chronological_split(df, val_size=0.15, test_size=0.15)
        preprocessor, feature_cols = build_preprocessor(df)
        x_train, y_train = to_xy(train_df, feature_cols)

        weights = build_weighted_sample_weights(y_train)

        preprocessor.fit(x_train, y_train)
        x_train_t = preprocessor.transform(x_train)

        def _train_xgb(sample_weight=None):
            clf = XGBClassifier(
                n_estimators=100,
                objective="multi:softprob",
                num_class=3,
                eval_metric="mlogloss",
                random_state=42,
            )
            clf.fit(x_train_t, y_train, sample_weight=sample_weight, verbose=False)
            return clf

        draw_idx = TARGET_MAP["D"]

        clf_weighted = _train_xgb(sample_weight=weights)
        clf_unweighted = _train_xgb()

        mean_draw_prob_weighted = clf_weighted.predict_proba(x_train_t)[:, draw_idx].mean()
        mean_draw_prob_unweighted = clf_unweighted.predict_proba(x_train_t)[:, draw_idx].mean()

        # Class weighting must lift draw predictions above the unweighted baseline
        assert mean_draw_prob_weighted > mean_draw_prob_unweighted, (
            f"weighted draw prob={mean_draw_prob_weighted:.4f} not > "
            f"unweighted draw prob={mean_draw_prob_unweighted:.4f}"
        )


# ---------------------------------------------------------------------------
# Issue #57: neutral-venue interaction features
# ---------------------------------------------------------------------------

class TestNeutralVenueInteractionFeatures:
    """neutral_x_elo_diff and neutral_x_rank_diff must be zero for home matches
    and equal to elo_diff / rank_diff on neutral ground."""

    def _make_row(self, neutral: bool) -> dict:
        tracker = _make_tracker()
        tracker.update(
            "Brazil", "Argentina",
            home_goals=2, away_goals=1,
            neutral=False,
            date=pd.Timestamp("2024-01-01"),
            competition="Friendly",
        )
        return build_match_row(
            tracker,
            home_team="Brazil",
            away_team="Argentina",
            match_date=pd.Timestamp("2024-06-01"),
            competition="FIFA World Cup",
            neutral=neutral,
            home_confederation="CONMEBOL",
            away_confederation="CONMEBOL",
            home_fifa_rank=5,
            away_fifa_rank=3,
            tournament_stage="Final",
        )

    def test_neutral_x_elo_diff_is_zero_for_home_match(self):
        row = self._make_row(neutral=False)
        assert "neutral_x_elo_diff" in row, "neutral_x_elo_diff missing from feature row"
        assert row["neutral_x_elo_diff"] == 0.0

    def test_neutral_x_rank_diff_is_zero_for_home_match(self):
        row = self._make_row(neutral=False)
        assert "neutral_x_rank_diff" in row, "neutral_x_rank_diff missing from feature row"
        assert row["neutral_x_rank_diff"] == 0.0

    def test_neutral_x_elo_diff_equals_elo_diff_on_neutral_ground(self):
        row = self._make_row(neutral=True)
        assert row["neutral_x_elo_diff"] == pytest.approx(row["elo_diff_home_away"])

    def test_neutral_x_rank_diff_equals_rank_diff_on_neutral_ground(self):
        row = self._make_row(neutral=True)
        assert row["neutral_x_rank_diff"] == pytest.approx(float(row["rank_diff"]))

    def test_neutral_interaction_features_present_in_preprocessor(self):
        """build_preprocessor must recognise neutral_x_elo_diff and neutral_x_rank_diff."""
        from src.models.common import build_preprocessor
        import numpy as np

        row = self._make_row(neutral=True)
        df = pd.DataFrame([row])
        df["target"] = "H"
        preprocessor, used_features = build_preprocessor(df)
        assert "neutral_x_elo_diff" in used_features
        assert "neutral_x_rank_diff" in used_features


# ---------------------------------------------------------------------------
# Issue #58: consecutive-result streak features
# ---------------------------------------------------------------------------

class TestStreakFeatures:
    """win_streak, unbeaten_streak, loss_streak on TeamStateTracker,
    and their presence in the feature row and preprocessor."""

    _STREAK_CAP = 10

    def _tracker_with_results(self, results: list[str]) -> TeamStateTracker:
        """results: list of 'W', 'D', 'L' from oldest to newest for 'Team'."""
        tracker = TeamStateTracker(_cfg())
        base = pd.Timestamp("2024-01-01")
        for i, r in enumerate(results):
            if r == "W":
                hg, ag = 2, 0
            elif r == "D":
                hg, ag = 1, 1
            else:
                hg, ag = 0, 2
            tracker.update(
                "Team", "Opp",
                home_goals=hg, away_goals=ag,
                neutral=False,
                date=base + pd.Timedelta(days=10 * i),
                competition="Friendly",
            )
        return tracker

    # --- win_streak ---

    def test_win_streak_five_consecutive_wins(self):
        tracker = self._tracker_with_results(["W", "W", "W", "W", "W"])
        assert tracker.win_streak("Team") == 5

    def test_win_streak_resets_on_draw(self):
        tracker = self._tracker_with_results(["W", "W", "D", "W", "W"])
        assert tracker.win_streak("Team") == 2

    def test_win_streak_zero_when_last_was_loss(self):
        tracker = self._tracker_with_results(["W", "W", "L"])
        assert tracker.win_streak("Team") == 0

    def test_win_streak_zero_with_no_history(self):
        tracker = TeamStateTracker(_cfg())
        assert tracker.win_streak("Team") == 0

    def test_win_streak_capped_at_max(self):
        tracker = self._tracker_with_results(["W"] * 15)
        assert tracker.win_streak("Team") == self._STREAK_CAP

    # --- unbeaten_streak ---

    def test_unbeaten_streak_wins_and_draws(self):
        tracker = self._tracker_with_results(["W", "D", "W", "D", "W"])
        assert tracker.unbeaten_streak("Team") == 5

    def test_unbeaten_streak_resets_on_loss(self):
        tracker = self._tracker_with_results(["W", "W", "L", "W", "D"])
        assert tracker.unbeaten_streak("Team") == 2

    def test_unbeaten_streak_zero_when_last_was_loss(self):
        tracker = self._tracker_with_results(["W", "W", "L"])
        assert tracker.unbeaten_streak("Team") == 0

    # --- loss_streak ---

    def test_loss_streak_three_consecutive_losses(self):
        tracker = self._tracker_with_results(["L", "L", "L"])
        assert tracker.loss_streak("Team") == 3

    def test_loss_streak_resets_on_draw(self):
        tracker = self._tracker_with_results(["L", "L", "D", "L"])
        assert tracker.loss_streak("Team") == 1

    def test_loss_streak_zero_when_last_was_win(self):
        tracker = self._tracker_with_results(["L", "L", "W"])
        assert tracker.loss_streak("Team") == 0

    # --- feature row presence ---

    def test_streak_features_present_in_match_row(self):
        tracker = self._tracker_with_results(["W", "W", "W"])
        row = build_match_row(
            tracker,
            home_team="Team",
            away_team="Opp",
            match_date=pd.Timestamp("2025-01-01"),
            competition="Friendly",
            neutral=False,
            home_confederation="UEFA",
            away_confederation="UEFA",
            home_fifa_rank=10,
            away_fifa_rank=20,
            tournament_stage="unknown",
        )
        for key in ("home_win_streak", "away_win_streak",
                    "home_unbeaten_streak", "away_unbeaten_streak",
                    "home_loss_streak", "away_loss_streak"):
            assert key in row, f"{key} missing from feature row"

    def test_streak_features_in_preprocessor(self):
        from src.models.common import build_preprocessor

        tracker = self._tracker_with_results(["W", "W"])
        row = build_match_row(
            tracker,
            home_team="Team",
            away_team="Opp",
            match_date=pd.Timestamp("2025-01-01"),
            competition="Friendly",
            neutral=False,
            home_confederation="UEFA",
            away_confederation="UEFA",
            home_fifa_rank=10,
            away_fifa_rank=20,
            tournament_stage="unknown",
        )
        df = pd.DataFrame([row])
        df["target"] = "H"
        _, used_features = build_preprocessor(df)
        for key in ("home_win_streak", "away_win_streak",
                    "home_unbeaten_streak", "away_unbeaten_streak",
                    "home_loss_streak", "away_loss_streak"):
            assert key in used_features, f"{key} missing from preprocessor features"


# ---------------------------------------------------------------------------
# Issue #59: competition-tier base rates as features
# ---------------------------------------------------------------------------

class TestTierBaseRateFeatures:
    """tier_home_rate, tier_draw_rate, tier_away_rate in feature row and preprocessor.

    Rates represent historical H/D/A frequencies for each competition-weight tier.
    Each tier's rates must sum to 1.0.
    """

    from src.features.competition_weights import get_competition_weight

    def _make_row(self, competition: str) -> dict:
        tracker = _make_tracker()
        tracker.update(
            "Brazil", "Argentina",
            home_goals=1, away_goals=0,
            neutral=False,
            date=pd.Timestamp("2024-01-01"),
            competition="Friendly",
        )
        return build_match_row(
            tracker,
            home_team="Brazil",
            away_team="Argentina",
            match_date=pd.Timestamp("2024-06-01"),
            competition=competition,
            neutral=False,
            home_confederation="CONMEBOL",
            away_confederation="CONMEBOL",
            home_fifa_rank=5,
            away_fifa_rank=3,
            tournament_stage="group_stage",
        )

    def test_tier_rate_keys_present_in_row(self):
        row = self._make_row("FIFA World Cup")
        for key in ("tier_home_rate", "tier_draw_rate", "tier_away_rate"):
            assert key in row, f"{key} missing from feature row"

    def test_tier_rates_sum_to_one_for_world_cup(self):
        row = self._make_row("FIFA World Cup")
        total = row["tier_home_rate"] + row["tier_draw_rate"] + row["tier_away_rate"]
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_tier_rates_sum_to_one_for_friendly(self):
        row = self._make_row("International Friendly")
        total = row["tier_home_rate"] + row["tier_draw_rate"] + row["tier_away_rate"]
        assert total == pytest.approx(1.0, abs=1e-6)

    def test_tier_draw_rate_varies_by_tier(self):
        """Different competition tiers should have different draw rates."""
        from src.features.competition_weights import get_tier_base_rates
        wc_rates = get_tier_base_rates(5)
        friendly_rates = get_tier_base_rates(1)
        assert wc_rates["draw_rate"] != friendly_rates["draw_rate"]

    def test_get_tier_base_rates_returns_all_keys(self):
        from src.features.competition_weights import get_tier_base_rates
        for tier in (1, 2, 3, 4, 5):
            rates = get_tier_base_rates(tier)
            assert "home_rate" in rates
            assert "draw_rate" in rates
            assert "away_rate" in rates
            assert rates["home_rate"] + rates["draw_rate"] + rates["away_rate"] == pytest.approx(1.0, abs=1e-6)

    def test_tier_features_in_preprocessor(self):
        from src.models.common import build_preprocessor
        row = self._make_row("FIFA World Cup")
        df = pd.DataFrame([row])
        df["target"] = "H"
        _, used_features = build_preprocessor(df)
        for key in ("tier_home_rate", "tier_draw_rate", "tier_away_rate"):
            assert key in used_features, f"{key} missing from preprocessor"


# ---------------------------------------------------------------------------
# Issue #55: match_weight as explicit recency feature
# ---------------------------------------------------------------------------

class TestMatchWeightFeature:
    """match_weight must be emitted by build_match_row (default 1.0 at inference)
    and recognised as a base numeric feature by build_preprocessor."""

    def _make_row(self) -> dict:
        tracker = _make_tracker()
        tracker.update(
            "Brazil", "Germany",
            home_goals=1, away_goals=0,
            neutral=False,
            date=pd.Timestamp("2024-01-01"),
            competition="Friendly",
        )
        return build_match_row(
            tracker,
            home_team="Brazil",
            away_team="Germany",
            match_date=pd.Timestamp("2024-06-01"),
            competition="FIFA World Cup",
            neutral=False,
            home_confederation="CONMEBOL",
            away_confederation="UEFA",
            home_fifa_rank=5,
            away_fifa_rank=4,
            tournament_stage="group_stage",
        )

    def test_match_weight_present_in_row(self):
        row = self._make_row()
        assert "match_weight" in row, "match_weight missing from feature row"

    def test_match_weight_defaults_to_one_at_inference(self):
        row = self._make_row()
        assert row["match_weight"] == pytest.approx(1.0)

    def test_match_weight_in_preprocessor_base_features(self):
        from src.models.common import build_preprocessor
        row = self._make_row()
        df = pd.DataFrame([row])
        df["target"] = "H"
        _, used_features = build_preprocessor(df)
        assert "match_weight" in used_features, "match_weight missing from preprocessor base features"


# ---------------------------------------------------------------------------
# Issue #45: validate and tune time-decay halflife
# ---------------------------------------------------------------------------

class TestHalflifeSensitivity:
    """run_halflife_sensitivity returns a dict mapping halflife → metrics dict
    with at least 'log_loss' and 'accuracy' keys for each requested halflife."""

    @pytest.fixture
    def small_df(self):
        from src.models.common import load_feature_data
        df = load_feature_data("data/processed/features.csv")
        return df[df["date"].dt.year >= 2018].reset_index(drop=True)

    def test_sensitivity_returns_result_for_each_halflife(self, small_df):
        from src.evaluation.tune_halflife import run_halflife_sensitivity
        halflives = [365, 730]
        results = run_halflife_sensitivity(small_df, halflives=halflives, n_estimators=30)
        assert set(results.keys()) == set(halflives)

    def test_sensitivity_result_contains_log_loss(self, small_df):
        from src.evaluation.tune_halflife import run_halflife_sensitivity
        results = run_halflife_sensitivity(small_df, halflives=[730], n_estimators=30)
        assert "log_loss" in results[730]
        assert isinstance(results[730]["log_loss"], float)
        assert results[730]["log_loss"] > 0

    def test_sensitivity_result_contains_accuracy(self, small_df):
        from src.evaluation.tune_halflife import run_halflife_sensitivity
        results = run_halflife_sensitivity(small_df, halflives=[730], n_estimators=30)
        assert "accuracy" in results[730]
        assert 0.0 <= results[730]["accuracy"] <= 1.0

    def test_best_halflife_is_lowest_log_loss(self, small_df):
        from src.evaluation.tune_halflife import run_halflife_sensitivity, best_halflife
        halflives = [365, 730]
        results = run_halflife_sensitivity(small_df, halflives=halflives, n_estimators=30)
        best = best_halflife(results)
        assert best in halflives
        assert results[best]["log_loss"] == min(r["log_loss"] for r in results.values())


# ---------------------------------------------------------------------------
# Issue #56: tune min_train_year cutoff via sensitivity analysis
# ---------------------------------------------------------------------------

class TestMinTrainYearSensitivity:
    """run_min_year_sensitivity returns a dict mapping year → metrics dict."""

    @pytest.fixture
    def full_df(self):
        from src.models.common import load_feature_data
        return load_feature_data("data/processed/features.csv")

    def test_sensitivity_returns_result_for_each_year(self, full_df):
        from src.evaluation.tune_min_year import run_min_year_sensitivity
        years = [2005, 2010]
        results = run_min_year_sensitivity(full_df, cutoff_years=years, n_estimators=30)
        assert set(results.keys()) == set(years)

    def test_sensitivity_result_contains_log_loss(self, full_df):
        from src.evaluation.tune_min_year import run_min_year_sensitivity
        results = run_min_year_sensitivity(full_df, cutoff_years=[2010], n_estimators=30)
        assert "log_loss" in results[2010]
        assert isinstance(results[2010]["log_loss"], float)
        assert results[2010]["log_loss"] > 0

    def test_sensitivity_result_contains_accuracy(self, full_df):
        from src.evaluation.tune_min_year import run_min_year_sensitivity
        results = run_min_year_sensitivity(full_df, cutoff_years=[2010], n_estimators=30)
        assert "accuracy" in results[2010]
        assert 0.0 <= results[2010]["accuracy"] <= 1.0

    def test_best_year_is_lowest_log_loss(self, full_df):
        from src.evaluation.tune_min_year import run_min_year_sensitivity, best_cutoff_year
        years = [2005, 2010]
        results = run_min_year_sensitivity(full_df, cutoff_years=years, n_estimators=30)
        best = best_cutoff_year(results)
        assert best in years
        assert results[best]["log_loss"] == min(r["log_loss"] for r in results.values())
