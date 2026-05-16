"""Tests for issue #125: WC2026 venue features (altitude, dome, capacity)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.wc2026_venues import STADIUMS, CITY_ALTITUDE_M, altitude_from_city, lookup_venue
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
            "recency_halflife_days": 180.0,
        }
    }


def _build_row(venue=None) -> dict:
    tracker = TeamStateTracker(_cfg())
    return build_match_row(
        tracker=tracker,
        home_team="Brazil",
        away_team="Germany",
        match_date=pd.Timestamp("2026-07-01"),
        competition="FIFA World Cup",
        neutral=True,
        home_confederation="CONMEBOL",
        away_confederation="UEFA",
        home_fifa_rank=5,
        away_fifa_rank=16,
        tournament_stage="Quarter-Final",
        venue=venue,
    )


# ---------------------------------------------------------------------------
# STADIUMS coverage
# ---------------------------------------------------------------------------

class TestStadiumsCoverage:
    def test_all_16_stadiums_present(self):
        assert len(STADIUMS) == 16

    def test_high_altitude_mexican_venues(self):
        # Mexico City and Guadalajara are the genuinely high-altitude venues.
        # Monterrey (~538m) is not considered high-altitude by FIFA standards.
        assert STADIUMS["Mexico City"]["altitude_m"] > 1000
        assert STADIUMS["Guadalajara"]["altitude_m"] > 1000
        assert STADIUMS["Mexico City"]["altitude_m"] > 2000
        assert STADIUMS["Guadalajara"]["altitude_m"] > 1500

    def test_stadium_required_fields(self):
        required = {"name", "city", "country", "capacity", "altitude_m", "surface", "is_dome"}
        for venue_city, data in STADIUMS.items():
            missing = required - set(data.keys())
            assert not missing, f"{venue_city} missing fields: {missing}"

    def test_capacity_positive(self):
        for venue_city, data in STADIUMS.items():
            assert data["capacity"] > 0, f"{venue_city} has non-positive capacity"

    def test_is_dome_boolean(self):
        for venue_city, data in STADIUMS.items():
            assert data["is_dome"] in (True, False), f"{venue_city} is_dome must be bool"


# ---------------------------------------------------------------------------
# City altitude lookup
# ---------------------------------------------------------------------------

class TestCityAltitude:
    def test_la_paz_above_3000m(self):
        assert altitude_from_city("La Paz") > 3000

    def test_quito_above_2500m(self):
        assert altitude_from_city("Quito") > 2500

    def test_bogota_above_2000m(self):
        assert altitude_from_city("Bogotá") > 2000 or altitude_from_city("Bogota") > 2000

    def test_unknown_city_returns_zero(self):
        assert altitude_from_city("London") == 0
        assert altitude_from_city("") == 0
        assert altitude_from_city("NonExistentCity") == 0

    def test_mexico_city_in_lookup(self):
        assert altitude_from_city("Mexico City") > 2000


# ---------------------------------------------------------------------------
# match_row_builder venue features
# ---------------------------------------------------------------------------

class TestVenueFeatures:
    def test_venue_features_present_when_no_venue(self):
        row = _build_row(venue=None)
        assert "venue_altitude_m" in row
        assert "venue_is_dome" in row
        assert "venue_capacity" in row

    def test_defaults_zero_when_no_venue(self):
        row = _build_row(venue=None)
        assert row["venue_altitude_m"] == 0.0
        assert row["venue_is_dome"] == 0
        assert row["venue_capacity"] == 0.0

    def test_altitude_passed_from_venue_dict(self):
        venue = {"altitude_m": 2240, "is_dome": False, "capacity": 87523}
        row = _build_row(venue=venue)
        assert row["venue_altitude_m"] == 2240.0

    def test_is_dome_passed_from_venue_dict(self):
        venue = {"altitude_m": 170, "is_dome": True, "capacity": 80000}
        row = _build_row(venue=venue)
        assert row["venue_is_dome"] == 1

    def test_capacity_passed_from_venue_dict(self):
        venue = {"altitude_m": 8, "is_dome": False, "capacity": 82500}
        row = _build_row(venue=venue)
        assert row["venue_capacity"] == 82500.0


# ---------------------------------------------------------------------------
# lookup_venue integration
# ---------------------------------------------------------------------------

class TestLookupVenue:
    def test_mexico_city_group_match(self):
        venue = lookup_venue("Mexico", "South Africa", "2026-06-11")
        assert venue is not None
        assert venue["altitude_m"] == 2240
        assert venue["venue_city"] == "Mexico City"

    def test_guadalajara_altitude_above_1000m(self):
        venue = lookup_venue("Korea Republic", "Czechia", "2026-06-12")
        assert venue is not None
        assert venue["altitude_m"] > 1000

    def test_nonexistent_match_returns_none(self):
        assert lookup_venue("Brazil", "Germany", "2026-07-01") is None

    def test_venue_dict_contains_ml_fields(self):
        venue = lookup_venue("Mexico", "South Africa", "2026-06-11")
        assert venue is not None
        for field in ("altitude_m", "is_dome", "capacity"):
            assert field in venue, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# venue_features.csv
# ---------------------------------------------------------------------------

class TestVenueFeaturesCsv:
    @pytest.fixture
    def csv_path(self):
        p = Path(__file__).resolve().parents[1] / "data/processed/venue_features.csv"
        if not p.exists():
            pytest.skip("venue_features.csv not generated yet")
        return p

    def test_csv_has_16_rows(self, csv_path):
        df = pd.read_csv(csv_path)
        assert len(df) == 16

    def test_csv_columns(self, csv_path):
        df = pd.read_csv(csv_path)
        required = {"venue_city", "venue_name", "country", "capacity", "altitude_m", "is_dome"}
        assert required.issubset(set(df.columns))

    def test_mexican_high_altitude_venues(self, csv_path):
        df = pd.read_csv(csv_path)
        mexican = df[df["country"] == "Mexico"]
        assert len(mexican) == 3
        # Mexico City and Guadalajara are genuinely high-altitude (>1000m).
        # Monterrey (~538m) is moderate and correctly below that threshold.
        high_alt = mexican[mexican["altitude_m"] > 1000]
        assert len(high_alt) == 2
        assert set(high_alt["venue_city"]) == {"Mexico City", "Guadalajara"}
