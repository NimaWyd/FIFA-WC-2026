"""Phase 3 data-quality tests.

Covers:
- canonical team identity (alias resolution, safe lookup, confederation, rank)
- unknown team passthrough safety
- duplicate-match detection
- schema stability after normalization
- feature generation still works after dataset expansion
- inference path works with canonical team metadata

Run with:
    python -m pytest tests/test_phase3.py -v
    python tests/test_phase3.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.team_identity import (
    ALIAS_TO_CANONICAL,
    CANONICAL_TEAMS,
    get_confederation,
    get_fifa_rank,
    is_known_team,
    list_aliases,
    resolve_team,
    safe_resolve_team,
)
from src.data.schema import ensure_match_schema, normalize_team_name
from src.data.confederation_lookup import lookup_confederation


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


def _match_row(**overrides) -> dict:
    base = {
        "date": "2024-03-22",
        "home_team": "France",
        "away_team": "Germany",
        "home_score": 2,
        "away_score": 1,
        "neutral": False,
        "competition": "International Friendly",
        "home_confederation": "UEFA",
        "away_confederation": "UEFA",
        "home_fifa_rank": 2,
        "away_fifa_rank": 9,
        "tournament_stage": "Unknown",
    }
    base.update(overrides)
    return base


def _matches_df(*rows) -> pd.DataFrame:
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Team identity — resolve_team
# ---------------------------------------------------------------------------

class TestResolveTeam(unittest.TestCase):

    def test_usa_alias(self):
        self.assertEqual(resolve_team("USA"), "United States")

    def test_us_alias(self):
        self.assertEqual(resolve_team("US"), "United States")

    def test_south_korea_alias(self):
        self.assertEqual(resolve_team("South Korea"), "Korea Republic")

    def test_korea_alias(self):
        self.assertEqual(resolve_team("Korea"), "Korea Republic")

    def test_north_korea_alias(self):
        self.assertEqual(resolve_team("North Korea"), "Korea DPR")

    def test_iran_alias(self):
        self.assertEqual(resolve_team("Iran"), "IR Iran")

    def test_ivory_coast_alias(self):
        self.assertEqual(resolve_team("Ivory Coast"), "Côte d'Ivoire")

    def test_cote_divoire_unaccented(self):
        self.assertEqual(resolve_team("Cote d'Ivoire"), "Côte d'Ivoire")

    def test_bosnia_alias(self):
        self.assertEqual(resolve_team("Bosnia"), "Bosnia and Herzegovina")

    def test_bosnia_ampersand_alias(self):
        self.assertEqual(resolve_team("Bosnia & Herzegovina"), "Bosnia and Herzegovina")

    def test_czech_republic_alias(self):
        self.assertEqual(resolve_team("Czech Republic"), "Czechia")

    def test_turkiye_alias(self):
        self.assertEqual(resolve_team("Türkiye"), "Turkey")

    def test_turkiye_no_umlaut(self):
        self.assertEqual(resolve_team("Turkiye"), "Turkey")

    def test_west_germany_alias(self):
        self.assertEqual(resolve_team("West Germany"), "Germany")

    def test_zaire_alias(self):
        self.assertEqual(resolve_team("Zaire"), "DR Congo")

    def test_cape_verde_alias(self):
        self.assertEqual(resolve_team("Cape Verde"), "Cape Verde Islands")

    def test_swaziland_alias(self):
        self.assertEqual(resolve_team("Swaziland"), "Eswatini")

    def test_uae_alias(self):
        self.assertEqual(resolve_team("United Arab Emirates"), "UAE")

    def test_trinidad_ampersand(self):
        self.assertEqual(resolve_team("Trinidad & Tobago"), "Trinidad and Tobago")

    def test_republic_of_ireland(self):
        self.assertEqual(resolve_team("Republic of Ireland"), "Ireland")

    def test_north_macedonia_alias(self):
        self.assertEqual(resolve_team("Macedonia"), "North Macedonia")
        self.assertEqual(resolve_team("FYROM"), "North Macedonia")

    def test_soviet_union_alias(self):
        self.assertEqual(resolve_team("Soviet Union"), "Russia")

    def test_yugoslavia_alias(self):
        self.assertEqual(resolve_team("Yugoslavia"), "Serbia")

    def test_canonical_name_passthrough(self):
        self.assertEqual(resolve_team("France"), "France")
        self.assertEqual(resolve_team("Brazil"), "Brazil")
        self.assertEqual(resolve_team("Argentina"), "Argentina")

    def test_whitespace_stripped(self):
        self.assertEqual(resolve_team("  USA  "), "United States")
        self.assertEqual(resolve_team("  France  "), "France")

    def test_unknown_passthrough(self):
        self.assertEqual(resolve_team("Ruritania FC"), "Ruritania FC")

    def test_empty_string_passthrough(self):
        self.assertEqual(resolve_team(""), "")


# ---------------------------------------------------------------------------
# Team identity — safe_resolve_team
# ---------------------------------------------------------------------------

class TestSafeResolveTeam(unittest.TestCase):

    def test_known_alias_returns_canonical(self):
        self.assertEqual(safe_resolve_team("USA"), "United States")

    def test_canonical_name_returns_itself(self):
        self.assertEqual(safe_resolve_team("France"), "France")

    def test_unknown_returns_none(self):
        self.assertIsNone(safe_resolve_team("Ruritania FC"))

    def test_empty_string_returns_none(self):
        self.assertIsNone(safe_resolve_team(""))


# ---------------------------------------------------------------------------
# Team identity — is_known_team
# ---------------------------------------------------------------------------

class TestIsKnownTeam(unittest.TestCase):

    def test_canonical_is_known(self):
        self.assertTrue(is_known_team("France"))
        self.assertTrue(is_known_team("Korea Republic"))

    def test_alias_is_known(self):
        self.assertTrue(is_known_team("USA"))
        self.assertTrue(is_known_team("South Korea"))
        self.assertTrue(is_known_team("Iran"))

    def test_unknown_is_not_known(self):
        self.assertFalse(is_known_team("Ruritania FC"))


# ---------------------------------------------------------------------------
# Team identity — get_confederation
# ---------------------------------------------------------------------------

class TestGetConfederation(unittest.TestCase):

    def test_canonical_confederation(self):
        self.assertEqual(get_confederation("France"), "UEFA")
        self.assertEqual(get_confederation("Brazil"), "CONMEBOL")
        self.assertEqual(get_confederation("United States"), "CONCACAF")
        self.assertEqual(get_confederation("Nigeria"), "CAF")
        self.assertEqual(get_confederation("Japan"), "AFC")
        self.assertEqual(get_confederation("New Zealand"), "OFC")

    def test_alias_confederation(self):
        self.assertEqual(get_confederation("USA"), "CONCACAF")
        self.assertEqual(get_confederation("South Korea"), "AFC")
        self.assertEqual(get_confederation("Iran"), "AFC")
        self.assertEqual(get_confederation("Ivory Coast"), "CAF")

    def test_unknown_returns_default(self):
        self.assertEqual(get_confederation("Ruritania FC"), "UNKNOWN")
        self.assertEqual(get_confederation("Ruritania FC", default="OTHER"), "OTHER")


# ---------------------------------------------------------------------------
# Team identity — get_fifa_rank
# ---------------------------------------------------------------------------

class TestGetFifaRank(unittest.TestCase):

    def test_ranked_team(self):
        self.assertEqual(get_fifa_rank("Argentina"), 1)
        self.assertEqual(get_fifa_rank("France"), 2)
        self.assertEqual(get_fifa_rank("Spain"), 3)

    def test_alias_rank(self):
        self.assertEqual(get_fifa_rank("USA"), 13)
        self.assertEqual(get_fifa_rank("South Korea"), 26)
        self.assertEqual(get_fifa_rank("Iran"), 31)

    def test_unranked_team_returns_default(self):
        rank = get_fifa_rank("San Marino")
        self.assertEqual(rank, 75)

    def test_unknown_returns_default(self):
        self.assertEqual(get_fifa_rank("Ruritania FC"), 75)
        self.assertEqual(get_fifa_rank("Ruritania FC", default=99), 99)


# ---------------------------------------------------------------------------
# Team identity — list_aliases
# ---------------------------------------------------------------------------

class TestListAliases(unittest.TestCase):

    def test_usa_aliases(self):
        aliases = list_aliases("United States")
        self.assertIn("USA", aliases)
        self.assertIn("US", aliases)

    def test_unknown_team_empty_aliases(self):
        self.assertEqual(list_aliases("Ruritania FC"), [])

    def test_alias_input_resolves_then_lists(self):
        aliases = list_aliases("USA")
        self.assertIn("USA", aliases)


# ---------------------------------------------------------------------------
# confederation_lookup — backward compatibility
# ---------------------------------------------------------------------------

class TestConfederationLookup(unittest.TestCase):

    def test_canonical_name(self):
        self.assertEqual(lookup_confederation("Germany"), "UEFA")
        self.assertEqual(lookup_confederation("Japan"), "AFC")

    def test_alias_name(self):
        self.assertEqual(lookup_confederation("South Korea"), "AFC")
        self.assertEqual(lookup_confederation("USA"), "CONCACAF")
        self.assertEqual(lookup_confederation("Iran"), "AFC")

    def test_unknown_returns_unknown(self):
        self.assertEqual(lookup_confederation("Ruritania FC"), "UNKNOWN")


# ---------------------------------------------------------------------------
# schema.py — normalize_team_name (backward compat via team_identity)
# ---------------------------------------------------------------------------

class TestNormalizeTeamNameBackwardCompat(unittest.TestCase):

    def test_usa_resolves(self):
        self.assertEqual(normalize_team_name("USA"), "United States")

    def test_iran_resolves(self):
        self.assertEqual(normalize_team_name("Iran"), "IR Iran")

    def test_south_korea_resolves(self):
        self.assertEqual(normalize_team_name("South Korea"), "Korea Republic")

    def test_known_canonical_passthrough(self):
        self.assertEqual(normalize_team_name("Brazil"), "Brazil")

    def test_unknown_passthrough(self):
        self.assertEqual(normalize_team_name("Ruritania FC"), "Ruritania FC")

    def test_whitespace_stripped(self):
        self.assertEqual(normalize_team_name("  France  "), "France")


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication(unittest.TestCase):

    def _make_df(self, rows):
        return pd.DataFrame(rows)

    def test_exact_duplicate_removed(self):
        df = self._make_df([
            _match_row(date="2024-03-22", home_team="France", away_team="Germany"),
            _match_row(date="2024-03-22", home_team="France", away_team="Germany"),
        ])
        deduped = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="first")
        self.assertEqual(len(deduped), 1)

    def test_alias_duplicate_removed_after_normalization(self):
        df = self._make_df([
            _match_row(date="2024-03-22", home_team="USA", away_team="Mexico"),
            _match_row(date="2024-03-22", home_team="United States", away_team="Mexico"),
        ])
        df["home_team"] = df["home_team"].map(resolve_team)
        df["away_team"] = df["away_team"].map(resolve_team)
        deduped = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="first")
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped.iloc[0]["home_team"], "United States")

    def test_different_dates_not_deduped(self):
        df = self._make_df([
            _match_row(date="2024-03-22", home_team="France", away_team="Germany"),
            _match_row(date="2024-03-26", home_team="France", away_team="Germany"),
        ])
        deduped = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="first")
        self.assertEqual(len(deduped), 2)

    def test_different_teams_not_deduped(self):
        df = self._make_df([
            _match_row(date="2024-03-22", home_team="France", away_team="Germany"),
            _match_row(date="2024-03-22", home_team="France", away_team="Spain"),
        ])
        deduped = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="first")
        self.assertEqual(len(deduped), 2)

    def test_reversed_fixture_not_deduped(self):
        """France vs Germany and Germany vs France are different fixtures."""
        df = self._make_df([
            _match_row(date="2024-03-22", home_team="France", away_team="Germany"),
            _match_row(date="2024-03-22", home_team="Germany", away_team="France"),
        ])
        deduped = df.drop_duplicates(subset=["date", "home_team", "away_team"], keep="first")
        self.assertEqual(len(deduped), 2)


# ---------------------------------------------------------------------------
# Schema validation after normalization
# ---------------------------------------------------------------------------

class TestSchemaAfterNormalization(unittest.TestCase):

    def test_canonical_ids_in_schema(self):
        df = pd.DataFrame([
            _match_row(home_team="USA", away_team="Iran"),
            _match_row(home_team="South Korea", away_team="Ivory Coast"),
        ])
        out = ensure_match_schema(df)
        self.assertIn("United States", out["home_team"].values)
        self.assertIn("IR Iran", out["away_team"].values)
        self.assertIn("Korea Republic", out["home_team"].values)
        self.assertIn("Côte d'Ivoire", out["away_team"].values)

    def test_no_alias_leaks_through_schema(self):
        df = pd.DataFrame([_match_row(home_team="USA", away_team="West Germany")])
        out = ensure_match_schema(df)
        self.assertNotIn("USA", out["home_team"].values)
        self.assertNotIn("West Germany", out["away_team"].values)

    def test_optional_source_column_filled(self):
        df = pd.DataFrame([_match_row()])
        out = ensure_match_schema(df)
        self.assertIn("source", out.columns)
        self.assertEqual(out["source"].iloc[0], "unknown")

    def test_neutral_coercion_string(self):
        df = pd.DataFrame([_match_row(neutral="True")])
        out = ensure_match_schema(df)
        self.assertTrue(out["neutral"].iloc[0])

    def test_neutral_coercion_false_string(self):
        df = pd.DataFrame([_match_row(neutral="False")])
        out = ensure_match_schema(df)
        self.assertFalse(out["neutral"].iloc[0])


# ---------------------------------------------------------------------------
# Feature generation works after dataset expansion
# ---------------------------------------------------------------------------

class TestFeatureGenerationExpandedData(unittest.TestCase):

    def _make_multi_era_df(self) -> pd.DataFrame:
        return pd.DataFrame([
            # 1994 era
            _match_row(date="1994-06-20", home_team="Brazil", away_team="Russia",
                       competition="FIFA World Cup", tournament_stage="Group Stage"),
            # 2002 era
            _match_row(date="2002-06-05", home_team="Korea Republic", away_team="USA",
                       competition="FIFA World Cup", tournament_stage="Group Stage"),
            # 2010 era
            _match_row(date="2010-07-11", home_team="Spain", away_team="Netherlands",
                       competition="FIFA World Cup", tournament_stage="Final"),
            # 2018 era
            _match_row(date="2018-07-15", home_team="France", away_team="Croatia",
                       competition="FIFA World Cup", tournament_stage="Final"),
            # 2022 era
            _match_row(date="2022-12-18", home_team="Argentina", away_team="France",
                       competition="FIFA World Cup", tournament_stage="Final"),
        ])

    def test_feature_table_built_from_multi_era(self):
        from src.features.build_features import build_feature_table

        df = self._make_multi_era_df()
        features = build_feature_table(df, _cfg())
        self.assertEqual(len(features), 5)
        self.assertIn("home_elo_pre", features.columns)
        self.assertIn("target", features.columns)

    def test_first_match_base_elo(self):
        from src.features.build_features import build_feature_table

        df = self._make_multi_era_df()
        features = build_feature_table(df, _cfg())
        first = features.iloc[0]
        self.assertEqual(first["home_elo_pre"], 1500.0)
        self.assertEqual(first["away_elo_pre"], 1500.0)

    def test_elo_evolves_across_eras(self):
        from src.features.build_features import build_feature_table

        df = self._make_multi_era_df()
        features = build_feature_table(df, _cfg())
        # Brazil appears in row 0 (1994) and France in row 3 (2018).
        # By row 3, France's Elo must have been updated by row 2 (Spain won 2010 final).
        # Spain appeared in row 2 and row 3 involves France vs Croatia — but France
        # only appears in row 3, so check Spain (row 2) whose Elo must have moved
        # from row 0. Use Brazil which appears in row 0 and has updated Elo after that.
        # Actually Brazil is row 0 home_elo=1500; after row 0, Brazil beats Russia so
        # Brazil's Elo updates. Row 3 (Spain vs Netherlands) has Spain's pre-match Elo
        # after row 2 (Spain vs Netherlands in 2010 final) — wait, Spain is home in row 2.
        # Let's just check that Brazil's Elo is NOT 1500 for any row after the first.
        brazil_rows = features[features["home_team"] == "Brazil"]
        # Brazil only plays row 0, so check rows where Elo has clearly warmed up.
        # Korea Republic appears in row 1 and their Elo must differ from 1500 after row 0.
        kr_rows = features[features["home_team"] == "Korea Republic"]
        self.assertGreater(len(kr_rows), 0)
        kr_first = kr_rows.iloc[0]
        # Korea Republic played in row 1; Russia (away row 0) warmed up — Korea didn't
        # play in row 0, so their pre-match Elo in row 1 is still 1500.
        # Instead verify that Spain's pre-match Elo in row 2 reflects changes from rows 0-1.
        spain_rows = features[features["home_team"] == "Spain"]
        self.assertGreater(len(spain_rows), 0)
        # Spain is fresh in row 2 (no prior appearance) → Elo = 1500 at that point too.
        # The definitive check: after row 0, Brazil Elo changed; row 3 away_elo_pre for
        # France must differ if France appeared earlier — but France only appears in row 3.
        # Best approach: verify total non-base-Elo rows > 0 across all rows beyond first.
        non_base = features.iloc[1:][
            (features.iloc[1:]["home_elo_pre"] != 1500.0) |
            (features.iloc[1:]["away_elo_pre"] != 1500.0)
        ]
        self.assertGreater(len(non_base), 0, "No Elo evolution observed after first match")

    def test_aliases_resolved_in_feature_table(self):
        from src.features.build_features import build_feature_table

        df = pd.DataFrame([
            _match_row(home_team="USA", away_team="South Korea"),
            _match_row(date="2024-03-26", home_team="Korea Republic", away_team="United States"),
        ])
        features = build_feature_table(df, _cfg())
        # Both rows should share the same tracker state after alias normalization
        self.assertIn("Korea Republic", features["home_team"].values)
        self.assertIn("United States", features["away_team"].values)
        self.assertNotIn("USA", features["home_team"].values)
        self.assertNotIn("South Korea", features["home_team"].values)

    def test_target_labels_correct(self):
        from src.features.build_features import build_feature_table

        df = pd.DataFrame([
            _match_row(home_score=2, away_score=0),   # H
            _match_row(date="2024-03-25", home_score=1, away_score=1),  # D
            _match_row(date="2024-03-26", home_score=0, away_score=2),  # A
        ])
        features = build_feature_table(df, _cfg())
        self.assertEqual(features.iloc[0]["target"], "H")
        self.assertEqual(features.iloc[1]["target"], "D")
        self.assertEqual(features.iloc[2]["target"], "A")


# ---------------------------------------------------------------------------
# Inference path with canonical team metadata
# ---------------------------------------------------------------------------

class TestInferenceWithCanonicalMetadata(unittest.TestCase):

    def test_inference_row_uses_canonical_names(self):
        from src.app.predict_match import build_pre_match_row

        history = pd.DataFrame([
            _match_row(date="2023-01-01", home_team="USA", away_team="Mexico",
                       home_score=2, away_score=0),
        ])
        row = build_pre_match_row(
            history_df=history,
            home_team="United States",
            away_team="Mexico",
            match_date="2024-03-22",
            competition="CONCACAF Gold Cup",
            neutral=False,
            home_confederation="CONCACAF",
            away_confederation="CONCACAF",
            home_fifa_rank=13,
            away_fifa_rank=18,
            tournament_stage="Group Stage",
            cfg=_cfg(),
        )
        # USA history must warm up United States tracker state
        self.assertGreater(float(row["home_elo_pre"].iloc[0]), 1500.0)

    def test_inference_alias_history_equals_canonical_history(self):
        """Aliased history and canonical history must produce identical Elo."""
        from src.app.predict_match import build_pre_match_row

        base_history = pd.DataFrame([
            _match_row(date="2023-01-01", home_team="United States", away_team="Mexico",
                       home_score=2, away_score=0),
        ])
        alias_history = pd.DataFrame([
            _match_row(date="2023-01-01", home_team="USA", away_team="Mexico",
                       home_score=2, away_score=0),
        ])
        kwargs = dict(
            home_team="United States",
            away_team="Mexico",
            match_date="2024-03-22",
            competition="International Friendly",
            neutral=False,
            home_confederation="CONCACAF",
            away_confederation="CONCACAF",
            home_fifa_rank=13,
            away_fifa_rank=18,
            tournament_stage="Unknown",
            cfg=_cfg(),
        )
        row_canonical = build_pre_match_row(history_df=base_history, **kwargs)
        row_alias = build_pre_match_row(history_df=alias_history, **kwargs)

        self.assertAlmostEqual(
            float(row_canonical["home_elo_pre"].iloc[0]),
            float(row_alias["home_elo_pre"].iloc[0]),
            places=6,
        )


# ---------------------------------------------------------------------------
# Registry completeness sanity checks
# ---------------------------------------------------------------------------

class TestRegistryIntegrity(unittest.TestCase):

    def test_no_alias_maps_to_two_canonicals(self):
        """ALIAS_TO_CANONICAL must be injective (alias → unique canonical)."""
        seen: dict[str, str] = {}
        for alias, canonical in ALIAS_TO_CANONICAL.items():
            if alias in seen:
                self.assertEqual(seen[alias], canonical,
                                 f"Alias '{alias}' maps to '{seen[alias]}' and '{canonical}'")
            seen[alias] = canonical

    def test_all_canonical_names_self_map(self):
        for name in CANONICAL_TEAMS:
            self.assertEqual(ALIAS_TO_CANONICAL.get(name), name,
                             f"Canonical '{name}' not in alias map")

    def test_confederation_values_are_valid(self):
        valid = {"UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"}
        for name, meta in CANONICAL_TEAMS.items():
            conf = meta.get("confederation", "UNKNOWN")
            self.assertIn(conf, valid, f"Team '{name}' has invalid confederation '{conf}'")

    def test_fifa_rank_values_are_positive_or_none(self):
        for name, meta in CANONICAL_TEAMS.items():
            rank = meta.get("fifa_rank_2025")
            if rank is not None:
                self.assertGreater(rank, 0, f"Team '{name}' has non-positive rank {rank}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
