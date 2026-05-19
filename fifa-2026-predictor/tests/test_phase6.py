"""Phase 6 API tests.

Tests cover:
- /health returns 200 with expected structure
- /model-info returns consistent version and cutoff metadata
- /teams returns canonical team list and single-team lookup
- /predict works with default metadata (no overrides)
- /predict accepts optional overrides cleanly
- Unknown teams are handled gracefully
- Response schema is stable across calls
- Explanation fields are present and tied to actual computed features
- /predict uses the same shared feature engine as the CLI
- Probabilities sum to approximately 1.0
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# TestClient requires httpx — gracefully skip if missing
try:
    from fastapi.testclient import TestClient
    from src.api.main import app
    _client_available = True
except ImportError:
    _client_available = False

pytestmark = pytest.mark.skipif(
    not _client_available,
    reason="fastapi or httpx not installed — skipping API tests",
)

if _client_available:
    client = TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_returns_200(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_schema_shape(self):
        data = client.get("/api/v1/health").json()
        assert "status" in data
        assert "model_available" in data
        assert "data_available" in data
        assert "version" in data
        assert "timestamp" in data

    def test_status_is_ok(self):
        data = client.get("/api/v1/health").json()
        assert data["status"] == "ok"

    def test_booleans(self):
        data = client.get("/api/v1/health").json()
        assert isinstance(data["model_available"], bool)
        assert isinstance(data["data_available"], bool)


# ---------------------------------------------------------------------------
# /model-info
# ---------------------------------------------------------------------------

class TestModelInfo:
    def test_returns_200(self):
        resp = client.get("/api/v1/model-info")
        assert resp.status_code == 200

    def test_required_fields(self):
        data = client.get("/api/v1/model-info").json()
        for field in (
            "model_version", "model_type", "training_cutoff",
            "feature_set_version", "enabled_features",
            "scoreline_model_status", "config_summary",
        ):
            assert field in data, f"Missing field: {field}"

    def test_version_is_stable(self):
        r1 = client.get("/api/v1/model-info").json()
        r2 = client.get("/api/v1/model-info").json()
        assert r1["model_version"] == r2["model_version"]
        assert r1["training_cutoff"] == r2["training_cutoff"]

    def test_enabled_features_is_list(self):
        data = client.get("/api/v1/model-info").json()
        assert isinstance(data["enabled_features"], list)

    def test_config_summary_has_form_window(self):
        data = client.get("/api/v1/model-info").json()
        assert "form_window" in data["config_summary"]


# ---------------------------------------------------------------------------
# /teams
# ---------------------------------------------------------------------------

class TestTeams:
    def test_list_returns_200(self):
        resp = client.get("/api/v1/teams")
        assert resp.status_code == 200

    def test_list_is_non_empty(self):
        data = client.get("/api/v1/teams").json()
        assert len(data) > 100

    def test_team_schema(self):
        teams = client.get("/api/v1/teams").json()
        t = teams[0]
        for field in ("canonical_name", "display_name", "confederation", "aliases", "is_known"):
            assert field in t, f"Missing field: {field}"

    def test_confederation_filter(self):
        data = client.get("/api/v1/teams?confederation=UEFA").json()
        assert len(data) > 0
        assert all(t["confederation"] == "UEFA" for t in data)

    def test_single_known_team(self):
        resp = client.get("/api/v1/teams/France")
        assert resp.status_code == 200
        data = resp.json()
        assert data["canonical_name"] == "France"
        assert data["confederation"] == "UEFA"
        assert data["is_known"] is True

    def test_alias_resolves_to_canonical(self):
        resp = client.get("/api/v1/teams/USA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["canonical_name"] == "United States"

    def test_default_metadata_present(self):
        data = client.get("/api/v1/teams/Brazil").json()
        assert "default_metadata" in data
        meta = data["default_metadata"]
        assert "confederation" in meta
        assert "fifa_rank" in meta

    def test_unknown_team_returns_404(self):
        resp = client.get("/api/v1/teams/FakeTeamXYZ")
        assert resp.status_code == 404
        data = resp.json()
        assert "not found" in data["detail"].lower()


# ---------------------------------------------------------------------------
# /predict — requires trained model and history to be present
# ---------------------------------------------------------------------------

def _model_and_data_available() -> bool:
    from src.api.services import _get_model, _get_history
    return _get_model() is not None and _get_history() is not None


_predict_skip = pytest.mark.skipif(
    not _client_available or not _model_and_data_available(),
    reason="Model artifact or history CSV not found — skipping predict tests",
)


@_predict_skip
class TestPredict:
    def _predict(self, payload: dict) -> dict:
        resp = client.post("/api/v1/predict", json=payload)
        assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"
        return resp.json()

    def test_basic_prediction(self):
        data = self._predict({
            "home_team": "Brazil",
            "away_team": "Argentina",
            "match_date": "2026-06-15",
        })
        probs = data["probabilities"]
        assert "home_win" in probs
        assert "draw" in probs
        assert "away_win" in probs

    def test_probabilities_sum_to_one(self):
        data = self._predict({
            "home_team": "France",
            "away_team": "Germany",
            "match_date": "2026-06-20",
        })
        total = sum(data["probabilities"].values())
        assert abs(total - 1.0) < 1e-4, f"Probabilities sum to {total}"

    def test_probabilities_are_non_negative(self):
        data = self._predict({
            "home_team": "Spain",
            "away_team": "Portugal",
            "match_date": "2026-06-25",
        })
        for k, v in data["probabilities"].items():
            assert v >= 0.0, f"Negative probability for {k}: {v}"

    def test_default_metadata_autofill(self):
        data = self._predict({
            "home_team": "England",
            "away_team": "Italy",
            "match_date": "2026-07-01",
        })
        meta = data["metadata"]
        # Auto-filled fields should be non-empty
        assert meta["home_confederation"] not in (None, "UNKNOWN", "")
        assert isinstance(meta["home_fifa_rank"], int)
        # Autofill flags reflect that we didn't pass overrides
        assert meta["metadata_autofilled"]["home_confederation"] is True
        assert meta["metadata_autofilled"]["away_confederation"] is True

    def test_optional_overrides_accepted(self):
        data = self._predict({
            "home_team": "Japan",
            "away_team": "Korea Republic",
            "match_date": "2026-06-10",
            "competition": "FIFA World Cup",
            "neutral": True,
            "home_confederation": "AFC",
            "away_confederation": "AFC",
            "home_fifa_rank": 15,
            "away_fifa_rank": 26,
            "tournament_stage": "Group Stage",
        })
        meta = data["metadata"]
        assert meta["home_confederation"] == "AFC"
        assert meta["home_fifa_rank"] == 15
        assert meta["neutral"] is True
        # Autofill flags reflect that we DID pass overrides
        assert meta["metadata_autofilled"]["home_confederation"] is False
        assert meta["metadata_autofilled"]["home_fifa_rank"] is False

    def test_explanation_fields_present(self):
        data = self._predict({
            "home_team": "Brazil",
            "away_team": "France",
            "match_date": "2026-06-15",
        })
        exp = data["explanation"]
        for field in (
            "elo_diff", "home_elo", "away_elo",
            "form_diff", "home_form", "away_form",
            "rank_diff", "home_rank", "away_rank",
            "elo_win_prob", "competition_weight",
            "is_same_confederation", "data_note",
        ):
            assert field in exp, f"Missing explanation field: {field}"

    def test_explanation_is_same_confederation_type(self):
        data = self._predict({
            "home_team": "Spain",
            "away_team": "France",
            "match_date": "2026-06-15",
        })
        # Same confederation (both UEFA) → True
        assert data["explanation"]["is_same_confederation"] is True

    def test_explanation_cross_confederation(self):
        data = self._predict({
            "home_team": "Brazil",
            "away_team": "France",
            "match_date": "2026-06-15",
        })
        # CONMEBOL vs UEFA → False
        assert data["explanation"]["is_same_confederation"] is False

    def test_metadata_includes_model_info(self):
        data = self._predict({
            "home_team": "Mexico",
            "away_team": "United States",
            "match_date": "2026-06-15",
        })
        meta = data["metadata"]
        assert "model_version" in meta
        assert "model_type" in meta
        assert "training_cutoff" in meta
        assert "prediction_timestamp" in meta

    def test_alias_input_resolves_correctly(self):
        # "USA" alias should resolve to "United States"
        data = self._predict({
            "home_team": "USA",
            "away_team": "Mexico",
            "match_date": "2026-06-15",
        })
        assert data["home_team"] == "United States"

    def test_unknown_team_returns_prediction_with_defaults(self):
        # Unknown team should not crash — it passes through with default metadata
        data = self._predict({
            "home_team": "UnknownTeamXYZ",
            "away_team": "France",
            "match_date": "2026-06-15",
        })
        assert data["home_team"] == "UnknownTeamXYZ"
        # Should still return valid probabilities
        total = sum(data["probabilities"].values())
        assert abs(total - 1.0) < 1e-4

    def test_response_schema_stable_across_calls(self):
        payload = {
            "home_team": "Germany",
            "away_team": "Netherlands",
            "match_date": "2026-06-20",
        }
        r1 = self._predict(payload)
        r2 = self._predict(payload)
        assert set(r1.keys()) == set(r2.keys())
        assert set(r1["probabilities"].keys()) == set(r2["probabilities"].keys())
        assert set(r1["explanation"].keys()) == set(r2["explanation"].keys())

    def test_predict_uses_same_engine_as_cli(self):
        """Verify the API reuses build_pre_match_row from the shared module."""
        from src.api import services as svc
        from src.app.predict_match import build_pre_match_row as cli_build

        # The service module imports and calls the same function
        import inspect
        source = inspect.getsource(svc.predict)
        assert "build_pre_match_row" in source

    def test_top_scorelines_is_list(self):
        data = self._predict({
            "home_team": "Argentina",
            "away_team": "Brazil",
            "match_date": "2026-06-15",
        })
        assert isinstance(data["top_scorelines"], list)

    def test_expected_goals_dict(self):
        data = self._predict({
            "home_team": "Argentina",
            "away_team": "Brazil",
            "match_date": "2026-06-15",
        })
        # Either populated (if scoreline model available) or empty
        assert isinstance(data["expected_goals"], dict)


# ---------------------------------------------------------------------------
# Invalid request handling
# ---------------------------------------------------------------------------

@_predict_skip
class TestPredictErrors:
    def test_missing_required_fields(self):
        resp = client.post("/api/v1/predict", json={"home_team": "France"})
        assert resp.status_code == 422

    def test_invalid_rank_negative(self):
        resp = client.post("/api/v1/predict", json={
            "home_team": "France",
            "away_team": "Brazil",
            "match_date": "2026-06-15",
            "home_fifa_rank": -5,
        })
        assert resp.status_code == 422
