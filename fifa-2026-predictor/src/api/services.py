"""Shared service layer for the API.

All routes call these functions.  Heavy logic lives in the existing shared
modules (predict_match, team_identity, scoreline_model, registry); this module
is a thin orchestration layer that wires them together and handles singleton
state (lazy-loaded model + history).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

import joblib
import numpy as np
import pandas as pd

from src.app.predict_match import build_pre_match_row
from src.data.team_identity import (
    CANONICAL_TEAMS,
    get_confederation,
    get_fifa_rank,
    is_known_team,
    resolve_team,
)
from src.features.registry import get_registry
from src.models.common import TARGET_MAP
from src.models.ensemble_model import EnsembleModel
from src.models.scoreline_model import TeamDependentScoreModel
from src.utils import PROJECT_ROOT, load_config
from src.data.load_squad_ratings import load_squad_ratings as _load_squad_ratings, DEFAULT_PATH as _SQUAD_RATINGS_PATH

# ---------------------------------------------------------------------------
# Module-level singletons — loaded once on first use
# ---------------------------------------------------------------------------

_model: Any = None
_model_artifact_name: str = "none"
_history_df: Optional[pd.DataFrame] = None
_cfg: Optional[dict] = None
_tournament_model: Any = None
_tournament_model_loaded: bool = False
_simulation_cache: Optional[dict] = None
_bracket_cache: Optional[dict] = None
_squad_ratings: dict = {}
_squad_ratings_loaded: bool = False


def _get_squad_ratings() -> dict:
    global _squad_ratings, _squad_ratings_loaded
    if not _squad_ratings_loaded:
        _squad_ratings = _load_squad_ratings(_SQUAD_RATINGS_PATH)
        _squad_ratings_loaded = True
    return _squad_ratings


def invalidate_data_caches() -> None:
    """Reset history and simulation caches so the next request reloads fresh data."""
    global _history_df, _simulation_cache, _bracket_cache, _squad_ratings, _squad_ratings_loaded
    _history_df = None
    _simulation_cache = None
    _bracket_cache = None
    _squad_ratings = {}
    _squad_ratings_loaded = False


def _get_cfg() -> dict:
    global _cfg
    if _cfg is None:
        _cfg = load_config()
    return _cfg


def _get_model() -> Any:
    """Lazy-load the best available trained model artifact."""
    global _model, _model_artifact_name
    if _model is not None:
        return _model

    artifact_dir = PROJECT_ROOT / _get_cfg()["paths"]["trained_model_dir"]
    # Prefer XGBoost; fall back to logistic regression
    for name in ("ensemble.joblib", "xgb.joblib", "logreg.joblib"):
        path = artifact_dir / name
        if path.exists():
            _model = joblib.load(path)
            _model_artifact_name = name
            break

    return _model


def _get_tournament_model() -> Any:
    """Lazy-load xgb_tournament.joblib if it exists; returns None if absent."""
    global _tournament_model, _tournament_model_loaded
    if _tournament_model_loaded:
        return _tournament_model

    _tournament_model_loaded = True
    artifact_dir = PROJECT_ROOT / _get_cfg()["paths"]["trained_model_dir"]
    path = artifact_dir / "xgb_tournament.joblib"
    if path.exists():
        _tournament_model = joblib.load(path)
        log.info("Loaded tournament model: %s", path)
    else:
        log.warning("xgb_tournament.joblib not found — all requests use ensemble model")
    return _tournament_model


def simulate(n: int = 1000) -> dict:
    """Run tournament simulation (cached for server lifetime)."""
    global _simulation_cache
    if _simulation_cache is not None:
        return _simulation_cache

    model = _get_model()
    if model is None:
        raise RuntimeError("No trained model artifact found.")
    history_df = _get_history()
    if history_df is None:
        raise RuntimeError("No match history file found.")
    cfg = _get_cfg()

    from src.simulation.tournament import build_tournament_states, run_simulation
    tracker = build_tournament_states(history_df, cfg)
    _simulation_cache = run_simulation(tracker, model, cfg, n=n, squad_ratings=_get_squad_ratings())
    return _simulation_cache


def predict_bracket() -> dict:
    """Deterministically predict the full WC2026 bracket (cached for server lifetime)."""
    global _bracket_cache
    if _bracket_cache is not None:
        return _bracket_cache

    model = _get_model()
    if model is None:
        raise RuntimeError("No trained model artifact found.")
    history_df = _get_history()
    if history_df is None:
        raise RuntimeError("No match history file found.")
    cfg = _get_cfg()

    from src.simulation.tournament import (
        build_tournament_states,
        precompute_all_probabilities,
        predict_bracket as _predict_bracket,
    )
    tracker = build_tournament_states(history_df, cfg)
    prob_cache = precompute_all_probabilities(tracker, model, cfg, squad_ratings=_get_squad_ratings())
    _bracket_cache = _predict_bracket(prob_cache)
    return _bracket_cache


def _select_model(base_model: Any, tournament_model: Any, competition_weight: float, min_weight: int) -> Any:
    """Return tournament model when available and competition qualifies; otherwise base."""
    if tournament_model is not None and competition_weight >= min_weight:
        return tournament_model
    return base_model


_REQUIRED_HISTORY_COLUMNS = {"home_team", "away_team", "home_score", "away_score"}


def normalize_history_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize a raw match history DataFrame loaded from any candidate CSV.

    Raises ValueError if critical columns (home_team, away_team) are missing.
    Drops rows with missing scores silently (state_tracker requires int goals).
    """
    missing = _REQUIRED_HISTORY_COLUMNS - {"home_score", "away_score"} - set(df.columns)
    if missing:
        raise ValueError(f"Match history CSV is missing required columns: {sorted(missing)}")

    df = df.copy()

    # Drop rows with missing scores — state_tracker requires integer goals
    for col in ("home_score", "away_score"):
        if col in df.columns:
            df = df.dropna(subset=[col])

    # Normalise the 'neutral' column (TRUE/FALSE strings from results.csv)
    if "neutral" in df.columns:
        df["neutral"] = (
            df["neutral"].astype(str).str.upper()
            .map({"TRUE": True, "FALSE": False, "1": True, "0": False})
            .fillna(False)
        )

    # Map results.csv 'tournament' column to 'competition' if needed
    if "tournament" in df.columns and "competition" not in df.columns:
        df = df.rename(columns={"tournament": "competition"})

    return df.reset_index(drop=True)


def _get_history() -> Optional[pd.DataFrame]:
    """Lazy-load match history, trying several candidate paths."""
    global _history_df
    if _history_df is not None:
        return _history_df

    candidates = [
        PROJECT_ROOT / "data/processed/matches_clean.csv",
        PROJECT_ROOT / "data/raw/results.csv",
        PROJECT_ROOT / "data/raw/demo_international_matches.csv",
    ]
    for path in candidates:
        if path.exists():
            raw = pd.read_csv(path)
            try:
                _history_df = normalize_history_csv(raw)
            except ValueError as exc:
                log.warning("Skipping %s: %s", path, exc)
                continue
            break

    return _history_df


# ---------------------------------------------------------------------------
# Team metadata helpers
# ---------------------------------------------------------------------------

def resolve_team_metadata(
    raw_name: str,
    confederation_override: Optional[str],
    rank_override: Optional[int],
) -> tuple[str, str, int]:
    """Return (canonical_name, confederation, fifa_rank) with auto-fill."""
    canonical = resolve_team(raw_name)
    confederation = confederation_override or get_confederation(canonical)
    rank = rank_override if rank_override is not None else get_fifa_rank(canonical)
    return canonical, confederation, rank


# ---------------------------------------------------------------------------
# /predict service
# ---------------------------------------------------------------------------

_CI_MIN_WEIGHT = 0.15  # per-class weight threshold below which a model is excluded from that class's CI


def _extract_ensemble_ci(
    model: Any, feature_row: "pd.DataFrame"
) -> Optional[dict[str, tuple[float, float]]]:
    """Weighted-std confidence interval with per-class model filtering.

    For each outcome class independently, only models whose per-class blend
    weight meets _CI_MIN_WEIGHT are included. This prevents a model that is
    nearly irrelevant to a specific class (e.g. LogReg at 0.05 for away_win)
    from inflating that class's CI with its extreme predictions.

    Returns {outcome: (lo, hi)} clamped to [0, 1], or None for non-ensemble.
    """
    if not isinstance(model, EnsembleModel):
        return None
    try:
        all_p = model.base_probas(feature_row)  # (3, n, 3): [model, row, class]
        row = all_p[:, 0, :]                    # (3, 3): [model, class] — A=0, D=1, H=2
        w = model.per_class_weights             # (3, 3): [model, class]

        lo_list, hi_list = [], []
        for c in range(3):
            wc = w[:, c]                        # (3,): per-class weights for class c
            keep = wc >= _CI_MIN_WEIGHT
            if not keep.any():
                keep = np.ones(3, dtype=bool)   # fallback: keep all
            wc_k = wc[keep] / wc[keep].sum()    # normalize retained weights
            rc_k = row[keep, c]

            mean_c = (wc_k * rc_k).sum()
            std_c = np.sqrt((wc_k * (rc_k - mean_c) ** 2).sum())
            lo_list.append(float(np.clip(mean_c - std_c, 0.0, 1.0)))
            hi_list.append(float(np.clip(mean_c + std_c, 0.0, 1.0)))

        return {
            "home_win": (lo_list[2], hi_list[2]),
            "draw":     (lo_list[1], hi_list[1]),
            "away_win": (lo_list[0], hi_list[0]),
        }
    except Exception as exc:
        log.warning("CI extraction failed: %s", exc)
        return None


def predict(
    home_team: str,
    away_team: str,
    match_date: str,
    competition: Optional[str],
    neutral: Optional[bool],
    home_confederation: Optional[str],
    away_confederation: Optional[str],
    home_fifa_rank: Optional[int],
    away_fifa_rank: Optional[int],
    tournament_stage: Optional[str],
) -> dict[str, Any]:
    """Run a pre-match prediction using the shared feature pipeline.

    Team confederation and FIFA rank are auto-filled from the canonical
    registry when not explicitly provided.  The feature row is constructed
    by the same ``build_pre_match_row`` function used by the CLI, ensuring
    training-inference consistency.
    """
    base_model = _get_model()
    if base_model is None:
        raise RuntimeError(
            "No trained model artifact found. "
            "Run training first (python -m src.models.train_xgb or train_logreg)."
        )

    history_df = _get_history()
    if history_df is None:
        raise RuntimeError(
            "No match history file found. "
            "Expected data/processed/matches_clean.csv or data/raw/results.csv."
        )

    cfg = _get_cfg()
    default_competition: str = cfg["inference"]["default_competition"]
    default_neutral: bool = cfg["inference"]["default_neutral"]

    # Resolve canonical names and auto-fill confederation / rank
    home_canonical, home_conf, home_rank = resolve_team_metadata(
        home_team, home_confederation, home_fifa_rank
    )
    away_canonical, away_conf, away_rank = resolve_team_metadata(
        away_team, away_confederation, away_fifa_rank
    )

    comp = competition or default_competition
    is_neutral = neutral if neutral is not None else default_neutral
    stage = tournament_stage or "Unknown"

    # Build the feature row using the shared pipeline — no logic duplicated here
    feature_row = build_pre_match_row(
        history_df=history_df,
        home_team=home_canonical,
        away_team=away_canonical,
        match_date=match_date,
        competition=comp,
        neutral=is_neutral,
        home_confederation=home_conf,
        away_confederation=away_conf,
        home_fifa_rank=home_rank,
        away_fifa_rank=away_rank,
        tournament_stage=stage,
        cfg=cfg,
        squad_ratings=_get_squad_ratings(),
    )

    cfg_min = int(cfg["model"].get("tournament_model_min_weight", 3))
    comp_weight = float(feature_row.iloc[0].get("competition_weight", 1))
    model = _select_model(base_model, _get_tournament_model(), comp_weight, cfg_min)
    log.debug("Using model: %s (competition_weight=%.0f)", type(model).__name__, comp_weight)

    # Outcome probabilities
    clf = model.named_steps["classifier"]
    probs_raw = model.predict_proba(feature_row)[0]
    prob_by_class = {int(c): float(p) for c, p in zip(clf.classes_, probs_raw)}
    probabilities = {
        "home_win": prob_by_class.get(TARGET_MAP["H"], 0.0),
        "draw": prob_by_class.get(TARGET_MAP["D"], 0.0),
        "away_win": prob_by_class.get(TARGET_MAP["A"], 0.0),
    }

    # Issue #109: on neutral ground, average P(home,away) and P(away,home) to
    # cancel the model's learned home-advantage artifact. Both orderings are
    # equally valid on a neutral pitch, so their mean is the unbiased estimate.
    if is_neutral:
        swapped_row = build_pre_match_row(
            history_df=history_df,
            home_team=away_canonical,
            away_team=home_canonical,
            match_date=match_date,
            competition=comp,
            neutral=True,
            home_confederation=away_conf,
            away_confederation=home_conf,
            home_fifa_rank=away_rank,
            away_fifa_rank=home_rank,
            tournament_stage=stage,
            cfg=cfg,
            squad_ratings=_get_squad_ratings(),
        )
        probs_swapped_raw = model.predict_proba(swapped_row)[0]
        prob_swapped = {int(c): float(p) for c, p in zip(clf.classes_, probs_swapped_raw)}
        # In the swapped row "home" = original away team, so:
        #   prob_swapped[TARGET_MAP["H"]] = P(original away wins)
        #   prob_swapped[TARGET_MAP["A"]] = P(original home wins)
        # Symmetrize from original home team's perspective:
        probabilities = {
            "home_win": 0.5 * (probabilities["home_win"] + prob_swapped.get(TARGET_MAP["A"], 0.0)),
            "draw":     0.5 * (probabilities["draw"]     + prob_swapped.get(TARGET_MAP["D"], 0.0)),
            "away_win": 0.5 * (probabilities["away_win"] + prob_swapped.get(TARGET_MAP["H"], 0.0)),
        }

    # Scoreline distribution (optional — no error if params file absent)
    top_scorelines: list[dict] = []
    expected_goals: dict[str, float] = {}
    scoreline_status = "unavailable"
    scoreline_path = PROJECT_ROOT / "src/models/artifacts/scoreline_params.json"
    if not scoreline_path.exists():
        scoreline_path = PROJECT_ROOT / "src/models/artifacts/poisson_params.json"
    if scoreline_path.exists():
        try:
            score_model = TeamDependentScoreModel.load(scoreline_path)
            row_dict = feature_row.iloc[0].to_dict()
            # Use natural lambdas derived from team attack/defense ratings.
            # calibrate_lambdas_to_outcomes forced high xG (2.0-2.5) when
            # draw probability was low, making 2-1 appear too often. Natural
            # lambdas stay realistic (1.0-2.0 range). See issue #118.
            lh, la = score_model.predict_lambdas_from_row(row_dict)
            expected_goals = {"home": round(lh, 3), "away": round(la, 3)}
            raw_scorelines = TeamDependentScoreModel.top_scorelines(lh, la, top_n=5)
            top_scorelines = [
                {"scoreline": s, "probability": round(p, 4)} for s, p in raw_scorelines
            ]
            scoreline_status = "available"
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            log.critical("Scoreline model file is corrupt or unreadable: %s", exc)
        except Exception as exc:
            log.error("Scoreline model prediction failed unexpectedly: %s", exc)
    else:
        log.warning("Scoreline model params not found at %s — scoreline predictions unavailable", scoreline_path)

    # Confidence intervals derived from per-model probability spread
    confidence = _extract_ensemble_ci(model, feature_row)

    # Explanation derived directly from the computed feature row — no fabrication
    row = feature_row.iloc[0].to_dict()
    explanation = _build_explanation(row, home_rank, away_rank)

    model_type = "xgboost" if "xgb" in _model_artifact_name else "logistic_regression"

    return {
        "home_team": home_canonical,
        "away_team": away_canonical,
        "match_date": match_date,
        "probabilities": probabilities,
        "top_scorelines": top_scorelines,
        "expected_goals": expected_goals,
        "explanation": explanation,
        "confidence": confidence,
        "metadata": {
            "model_version": "1.0.0",
            "model_type": model_type,
            "artifact": _model_artifact_name,
            "training_cutoff": _get_training_cutoff(),
            "feature_set_version": "phase5",
            "scoreline_model_status": scoreline_status,
            "competition_used": comp,
            "neutral": is_neutral,
            "neutral_symmetry_applied": is_neutral,
            "home_confederation": home_conf,
            "away_confederation": away_conf,
            "home_fifa_rank": home_rank,
            "away_fifa_rank": away_rank,
            "tournament_stage": stage,
            "prediction_timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata_autofilled": {
                "home_confederation": home_confederation is None,
                "away_confederation": away_confederation is None,
                "home_fifa_rank": home_fifa_rank is None,
                "away_fifa_rank": away_fifa_rank is None,
            },
        },
    }


def _safe_float(val: Any, default: float) -> float:
    """Cast *val* to float, returning *default* on NaN/None/error."""
    try:
        result = float(val)
        return result if result == result else default  # NaN check
    except (TypeError, ValueError):
        return default


def _build_explanation(row: dict[str, Any], home_rank: int, away_rank: int) -> dict[str, Any]:
    """Produce an explanation dict from actual pre-match feature values."""
    return {
        "elo_diff": round(_safe_float(row.get("elo_diff_home_away"), 0.0), 1),
        "home_elo": round(_safe_float(row.get("home_elo_pre"), 1500.0), 1),
        "away_elo": round(_safe_float(row.get("away_elo_pre"), 1500.0), 1),
        "form_diff": round(_safe_float(row.get("form_diff_home_away"), 0.0), 4),
        "home_form": round(_safe_float(row.get("home_form_last5"), 0.0), 4),
        "away_form": round(_safe_float(row.get("away_form_last5"), 0.0), 4),
        "rank_diff": int(_safe_float(row.get("rank_diff"), float(home_rank - away_rank))),
        "home_rank": home_rank,
        "away_rank": away_rank,
        "elo_win_prob": round(_safe_float(row.get("elo_win_prob"), 0.5), 4),
        "competition_weight": round(_safe_float(row.get("competition_weight"), 1.0), 2),
        "is_same_confederation": bool(int(_safe_float(row.get("is_same_confederation"), 0.0))),
        "data_note": (
            "All explanation values are derived from the pre-match rolling feature row "
            "computed by the shared TeamStateTracker — no post-match data is used."
        ),
    }


def _get_training_cutoff() -> str:
    history = _get_history()
    if history is not None and "date" in history.columns:
        last = pd.to_datetime(history["date"], errors="coerce").max()
        if pd.notna(last):
            return str(last.date())
    return "unknown"


# ---------------------------------------------------------------------------
# /teams service
# ---------------------------------------------------------------------------

def get_team_info(raw_name: str) -> dict[str, Any]:
    canonical = resolve_team(raw_name)
    meta = CANONICAL_TEAMS.get(canonical, {})
    rank = meta.get("fifa_rank_2025")
    conf = meta.get("confederation", "UNKNOWN")
    return {
        "canonical_name": canonical,
        "display_name": canonical,
        "confederation": conf,
        "fifa_rank": rank,
        "aliases": list(meta.get("aliases", [])),
        "is_known": is_known_team(raw_name),
        "default_metadata": {
            "confederation": conf,
            "fifa_rank": rank if rank is not None else _get_cfg()["features"]["default_fifa_rank"],
            "default_competition": _get_cfg()["inference"]["default_competition"],
        },
    }


def list_all_teams(confederation_filter: Optional[str] = None) -> list[dict[str, Any]]:
    result = []
    cfg = _get_cfg()
    default_rank = cfg["features"]["default_fifa_rank"]
    default_comp = cfg["inference"]["default_competition"]
    for name, meta in sorted(CANONICAL_TEAMS.items()):
        conf = meta.get("confederation", "UNKNOWN")
        if confederation_filter and conf.upper() != confederation_filter.upper():
            continue
        rank = meta.get("fifa_rank_2025")
        result.append({
            "canonical_name": name,
            "display_name": name,
            "confederation": conf,
            "fifa_rank": rank,
            "aliases": list(meta.get("aliases", [])),
            "is_known": True,
            "default_metadata": {
                "confederation": conf,
                "fifa_rank": rank if rank is not None else default_rank,
                "default_competition": default_comp,
            },
        })
    return result


# ---------------------------------------------------------------------------
# /model-info service
# ---------------------------------------------------------------------------

def get_model_info() -> dict[str, Any]:
    model = _get_model()
    cfg = _get_cfg()
    registry = get_registry()
    scoreline_path = PROJECT_ROOT / "src/models/artifacts/scoreline_params.json"

    model_type = "none"
    if model is not None:
        model_type = "xgboost" if "xgb" in _model_artifact_name else "logistic_regression"

    return {
        "model_version": "1.0.0",
        "model_type": model_type,
        "training_cutoff": _get_training_cutoff(),
        "feature_set_version": "phase5",
        "enabled_features": registry.enabled_blocks(),
        "scoreline_model_status": "available" if scoreline_path.exists() else "unavailable",
        "config_summary": {
            "form_window": cfg["features"]["form_window"],
            "elo_k_factor": cfg["features"]["elo_k_factor"],
            "default_fifa_rank": cfg["features"]["default_fifa_rank"],
            "default_competition": cfg["inference"]["default_competition"],
            "default_neutral": cfg["inference"]["default_neutral"],
        },
    }


# ---------------------------------------------------------------------------
# /health service
# ---------------------------------------------------------------------------

def get_health() -> dict[str, Any]:
    model = _get_model()
    history = _get_history()
    return {
        "status": "ok",
        "model_available": model is not None,
        "data_available": history is not None,
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
