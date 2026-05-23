# fifa-2026-predictor/src/simulation/tournament.py
"""Monte Carlo simulation of the WC2026 tournament."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from src.data.team_identity import get_confederation, get_fifa_rank
from src.features.match_row_builder import build_match_row
from src.features.state_tracker import TeamStateTracker
from src.simulation.wc2026_bracket import (
    WC2026_GROUPS, WC2026_R32,
    WC2026_R16_PAIRS, WC2026_QF_PAIRS, WC2026_SF_PAIRS,
    _THIRD_PLACE_LOOKUP,
)

def _get_tournament_date(cfg: dict | None = None) -> pd.Timestamp:
    if cfg is not None:
        date_str = cfg.get("simulation", {}).get("tournament_start_date", "2026-06-11")
        return pd.Timestamp(date_str)
    from src.utils import load_config
    return pd.Timestamp(load_config().get("simulation", {}).get("tournament_start_date", "2026-06-11"))

_TOURNAMENT_DATE = _get_tournament_date()
_COMPETITION = "FIFA World Cup"

# Type alias for the pre-computed probability cache
ProbCache = dict[tuple[str, str], dict[str, float]]

# Visual reorder for R16: groups by which SF half they feed.
# Left half (→ QF97+QF98 → SF101): R16-89,90,93,94 (indices 0,1,4,5)
# Right half (→ QF99+QF100 → SF102): R16-91,92,95,96 (indices 2,3,6,7)
_R16_VIS = [0, 1, 4, 5, 2, 3, 6, 7]


def build_tournament_states(history_df: pd.DataFrame, cfg: dict) -> TeamStateTracker:
    """Replay all match history before the tournament start; return the tracker snapshot."""
    from src.data.schema import ensure_match_schema
    history = ensure_match_schema(history_df)
    history = history[history["date"] < _TOURNAMENT_DATE].sort_values("date")
    tracker = TeamStateTracker(cfg)
    tracker.replay_history(history)

    # Apply Elo corrections for penalty-shootout results not tracked in raw data.
    # Penalty wins are stored as draws in results.csv; winner deserves +K*0.5 instead.
    k = float(cfg.get("features", {}).get("elo_k_factor", 25.0))
    for correction in cfg.get("simulation", {}).get("penalty_elo_corrections", []):
        winner = correction["winner"]
        loser = correction["loser"]
        tracker._ratings[winner] = tracker._ratings[winner] + k * 0.5
        tracker._ratings[loser] = tracker._ratings[loser] - k * 0.5

    return tracker


def predict_match_proba(
    home: str, away: str, tracker: TeamStateTracker, model: Any, cfg: dict,
    match_date: pd.Timestamp = _TOURNAMENT_DATE,
    stage: str = "Group Stage",
    squad_ratings: "dict | None" = None,
) -> dict[str, float]:
    """Return {home_win, draw, away_win} for a single match. Used for one-off predictions."""
    from src.models.common import TARGET_MAP
    record = build_match_row(
        tracker=tracker,
        home_team=home,
        away_team=away,
        match_date=match_date,
        competition=_COMPETITION,
        neutral=True,
        home_confederation=get_confederation(home),
        away_confederation=get_confederation(away),
        home_fifa_rank=get_fifa_rank(home),
        away_fifa_rank=get_fifa_rank(away),
        tournament_stage=stage,
        elo_inactivity_halflife=float(cfg.get("features", {}).get("elo_inactivity_halflife", 0.0)),
        squad_ratings=squad_ratings,
    )
    feature_row = pd.DataFrame([record])
    probs_raw = model.predict_proba(feature_row)[0]
    clf = model.named_steps["classifier"]
    prob_by_class = {int(c): float(p) for c, p in zip(clf.classes_, probs_raw)}
    return {
        "home_win": prob_by_class.get(TARGET_MAP["H"], 0.0),
        "draw":     prob_by_class.get(TARGET_MAP["D"], 0.0),
        "away_win": prob_by_class.get(TARGET_MAP["A"], 0.0),
    }


def precompute_all_probabilities(
    tracker: TeamStateTracker, model: Any, cfg: dict,
    squad_ratings: "dict | None" = None,
) -> ProbCache:
    """Build feature rows for all 48×47 ordered team pairs and run ONE batched predict_proba.

    Returns {(home, away): {home_win, draw, away_win}} for every possible matchup.
    Reduces simulation time from O(n * matches) model calls to O(1) amortized.
    """
    from src.models.common import TARGET_MAP
    from src.data.team_identity import resolve_team
    unresolved = []
    for g in WC2026_GROUPS:
        for t in g["teams"]:
            try:
                resolve_team(t)
            except Exception:
                unresolved.append(t)
    if unresolved:
        raise ValueError(
            f"Bracket team name(s) not found in team registry: {unresolved}. "
            "Check wc2026_bracket.py for typos and update team_identity.py if needed."
        )

    all_teams = [t for g in WC2026_GROUPS for t in g["teams"]]
    halflife = float(cfg.get("features", {}).get("elo_inactivity_halflife", 0.0))

    pairs: list[tuple[str, str]] = []
    rows: list[dict] = []
    for home in all_teams:
        for away in all_teams:
            if home == away:
                continue
            pairs.append((home, away))
            rows.append(build_match_row(
                tracker=tracker,
                home_team=home,
                away_team=away,
                match_date=_TOURNAMENT_DATE,
                competition=_COMPETITION,
                neutral=True,
                home_confederation=get_confederation(home),
                away_confederation=get_confederation(away),
                home_fifa_rank=get_fifa_rank(home),
                away_fifa_rank=get_fifa_rank(away),
                tournament_stage="Group Stage",
                elo_inactivity_halflife=halflife,
                squad_ratings=squad_ratings,
            ))

    feature_df = pd.DataFrame(rows)
    probs_matrix = model.predict_proba(feature_df)  # (n_pairs, 3)

    clf = model.named_steps["classifier"]
    classes = [int(c) for c in clf.classes_]

    variance_factor = float(cfg.get("simulation", {}).get("tournament_variance_factor", 0.0))
    uniform = 1.0 / 3.0

    cache: ProbCache = {}
    for i, (home, away) in enumerate(pairs):
        prob_by_class = {c: float(probs_matrix[i, j]) for j, c in enumerate(classes)}
        hw = prob_by_class.get(TARGET_MAP["H"], 0.0)
        d  = prob_by_class.get(TARGET_MAP["D"], 0.0)
        aw = prob_by_class.get(TARGET_MAP["A"], 0.0)
        if variance_factor > 0.0:
            hw = (1 - variance_factor) * hw + variance_factor * uniform
            d  = (1 - variance_factor) * d  + variance_factor * uniform
            aw = (1 - variance_factor) * aw + variance_factor * uniform
        cache[(home, away)] = {"home_win": hw, "draw": d, "away_win": aw}

    return cache


def _sample_goals(outcome: str, rng: np.random.Generator) -> tuple[int, int]:
    """Sample a plausible scoreline consistent with the given outcome."""
    if outcome == "H":
        hg = 1 + int(rng.poisson(0.8))
        ag = int(rng.poisson(0.5))
        if hg <= ag:
            ag = max(0, hg - 1)
    elif outcome == "A":
        hg = int(rng.poisson(0.5))
        ag = 1 + int(rng.poisson(0.8))
        if ag <= hg:
            hg = max(0, ag - 1)
    else:
        g = int(rng.poisson(0.9))
        hg, ag = g, g
    return hg, ag


def _compute_group_standings(
    group_teams: list[str],
    records: dict[str, dict],
) -> list[str]:
    """Return teams sorted by pts -> GD -> GF (descending)."""
    return sorted(
        group_teams,
        key=lambda t: (records[t]["pts"], records[t]["gd"], records[t]["gf"]),
        reverse=True,
    )


def _assign_third_place_teams(
    best_third: list[tuple[str, str]],  # [(team, group_id), ...]
) -> dict[int, str]:
    """Assign 8 best 3rd-place teams to R32 slots using the official FIFA Annex C lookup table.

    Returns {match_number: team}.
    """
    group_to_team = {group: team for team, group in best_third}
    qualifying_groups = frozenset(group for _, group in best_third)
    match_to_group = _THIRD_PLACE_LOOKUP.get(qualifying_groups)
    if match_to_group is None:
        raise RuntimeError(f"No FIFA Annex C entry for qualifying groups {sorted(qualifying_groups)}")
    return {match: group_to_team[group] for match, group in match_to_group.items()}


def _knockout_winner(home: str, away: str, prob_cache: ProbCache, rng: np.random.Generator) -> tuple[str, str]:
    """Return (winner, loser) for a single knockout match (no draws)."""
    probs = prob_cache[(home, away)]
    p_h = probs["home_win"] + probs["draw"] / 2
    p_a = probs["away_win"] + probs["draw"] / 2
    total = p_h + p_a
    winner = home if rng.random() < p_h / total else away
    return winner, (away if winner == home else home)


def _simulate_knockout_round(
    matchups: list[tuple[str, str]],
    prob_cache: ProbCache,
    stage: str,
    rng: np.random.Generator,
) -> tuple[list[str], dict[str, str]]:
    """Simulate one knockout round. Returns (winners, {eliminated_team: stage})."""
    winners = []
    eliminated = {}
    for home, away in matchups:
        winner, loser = _knockout_winner(home, away, prob_cache, rng)
        winners.append(winner)
        eliminated[loser] = stage
    return winners, eliminated


def simulate_once(
    tracker: TeamStateTracker,
    model: Any,
    cfg: dict,
    rng: np.random.Generator,
    prob_cache: ProbCache | None = None,
) -> tuple[dict[str, str], dict[int, str]]:
    """Run one full WC2026 simulation. Returns {team: stage_reached} for all 48 teams.

    If prob_cache is provided (pre-computed via precompute_all_probabilities), no model
    calls are made during the simulation — all probability lookups are O(1) dict access.
    """
    if prob_cache is None:
        prob_cache = precompute_all_probabilities(tracker, model, cfg)

    results: dict[str, str] = {}
    records: dict[str, dict] = {}

    # -- Group stage ----------------------------------------------------------
    for group in WC2026_GROUPS:
        for team in group["teams"]:
            records[team] = {"pts": 0, "gd": 0, "gf": 0}
        for match in group["matches"]:
            h, a = match["home"], match["away"]
            # Randomise home/away per run to cancel neutral-ground bias (issue #117).
            if rng.random() < 0.5:
                h, a = a, h
            probs = prob_cache[(h, a)]
            outcome = rng.choice(
                ["H", "D", "A"],
                p=[probs["home_win"], probs["draw"], probs["away_win"]],
            )
            hg, ag = _sample_goals(outcome, rng)
            if outcome == "H":
                records[h]["pts"] += 3
            elif outcome == "D":
                records[h]["pts"] += 1
                records[a]["pts"] += 1
            else:
                records[a]["pts"] += 3
            records[h]["gd"] += hg - ag
            records[a]["gd"] += ag - hg
            records[h]["gf"] += hg
            records[a]["gf"] += ag

    # -- Determine standings --------------------------------------------------
    group_finishers: dict[str, list[str]] = {}
    for group in WC2026_GROUPS:
        group_finishers[group["id"]] = _compute_group_standings(group["teams"], records)

    winners = {gid: teams[0] for gid, teams in group_finishers.items()}
    runners_up = {gid: teams[1] for gid, teams in group_finishers.items()}

    for gid, teams in group_finishers.items():
        results[teams[3]] = "group_exit"

    # -- Best 8 third-place teams ---------------------------------------------
    third_place: list[tuple[str, str]] = [
        (teams[2], gid) for gid, teams in group_finishers.items()
    ]
    third_sorted = sorted(
        third_place,
        key=lambda x: (
            records[x[0]]["pts"],
            records[x[0]]["gd"],
            records[x[0]]["gf"],
            -(get_fifa_rank(x[0]) or 999),
        ),
        reverse=True,
    )
    best_third = third_sorted[:8]
    for team, _ in third_sorted[8:]:
        results[team] = "group_exit"

    # -- Assign 3rd-place teams to R32 slots ----------------------------------
    third_assignments = _assign_third_place_teams(best_third)

    # -- Build R32 matchups keyed by match number -----------------------------
    match_winners: dict[int, str] = {}
    for slot in WC2026_R32:
        team1 = winners[slot["slot1_group"]] if slot["slot1_type"] == "W" else runners_up[slot["slot1_group"]]
        team2 = (
            runners_up[slot["slot2_group"]]
            if slot["slot2_type"] == "RU"
            else third_assignments.get(slot["match"], best_third[0][0])
        )
        if rng.random() < 0.5:
            team1, team2 = team2, team1
        winner_r32, loser_r32 = _knockout_winner(team1, team2, prob_cache, rng)
        match_winners[slot["match"]] = winner_r32
        results[loser_r32] = "round_of_32"

    # -- R16: official cross-pairings (not simple adjacency) ------------------
    for i, (ma, mb) in enumerate(WC2026_R16_PAIRS):
        t1, t2 = match_winners[ma], match_winners[mb]
        if rng.random() < 0.5:
            t1, t2 = t2, t1
        winner_r16, loser_r16 = _knockout_winner(t1, t2, prob_cache, rng)
        match_winners[89 + i] = winner_r16
        results[loser_r16] = "round_of_16"

    # -- QF -------------------------------------------------------------------
    for i, (ma, mb) in enumerate(WC2026_QF_PAIRS):
        t1, t2 = match_winners[ma], match_winners[mb]
        if rng.random() < 0.5:
            t1, t2 = t2, t1
        winner_qf, loser_qf = _knockout_winner(t1, t2, prob_cache, rng)
        match_winners[97 + i] = winner_qf
        results[loser_qf] = "quarter_final"

    # -- SF -------------------------------------------------------------------
    for i, (ma, mb) in enumerate(WC2026_SF_PAIRS):
        t1, t2 = match_winners[ma], match_winners[mb]
        if rng.random() < 0.5:
            t1, t2 = t2, t1
        winner_sf, loser_sf = _knockout_winner(t1, t2, prob_cache, rng)
        match_winners[101 + i] = winner_sf
        results[loser_sf] = "semi_final"

    # -- 3rd place playoff ----------------------------------------------------
    sf_losers = [t for t, s in results.items() if s == "semi_final"]
    if len(sf_losers) == 2:
        t1, t2 = sf_losers
        if rng.random() < 0.5:
            t1, t2 = t2, t1
        third, fourth = _knockout_winner(t1, t2, prob_cache, rng)
        results[third] = "third_place"
        results[fourth] = "fourth_place"

    # -- Final ----------------------------------------------------------------
    finalist1, finalist2 = match_winners[101], match_winners[102]
    winner, runner_up = _knockout_winner(finalist1, finalist2, prob_cache, rng)
    results[winner] = "champion"
    results[runner_up] = "final"

    # Track final winner (slot 103) and 3rd-place winner (slot 104)
    match_winners[103] = winner
    third_place_team = next((t for t, s in results.items() if s == "third_place"), None)
    if third_place_team is not None:
        match_winners[104] = third_place_team

    return results, match_winners


def _neutral_probs(
    team1: str, team2: str, prob_cache: ProbCache,
) -> tuple[float, float, float]:
    """Return (p_team1_wins, p_draw, p_team2_wins) for a neutral-ground match.

    Averages both home/away orderings to cancel the model's learned home-advantage
    artifact — the same symmetry applied in services.predict() and simulate_once().
    """
    p1 = 0.5 * (prob_cache[(team1, team2)]["home_win"] + prob_cache[(team2, team1)]["away_win"])
    pd = 0.5 * (prob_cache[(team1, team2)]["draw"]     + prob_cache[(team2, team1)]["draw"])
    p2 = 0.5 * (prob_cache[(team1, team2)]["away_win"] + prob_cache[(team2, team1)]["home_win"])
    return p1, pd, p2


def _knockout_neutral_probs(
    team1: str, team2: str, prob_cache: ProbCache,
) -> tuple[float, float]:
    """Return (p_team1_wins, p_team2_wins) for a neutral knockout match (draws → 50/50)."""
    p1, pd, p2 = _neutral_probs(team1, team2, prob_cache)
    return p1 + pd / 2, p2 + pd / 2


def predict_bracket(prob_cache: ProbCache) -> dict:
    """Deterministically predict the full WC2026 knockout bracket.

    Uses expected points from neutral match probabilities to rank group standings,
    assigns 3rd-place teams to R32 slots, then propagates winners round by round.
    Returns per-match win probabilities for every round from R32 to Final.
    """
    # --- Group stage expected standings ---
    all_expected_pts: dict[str, float] = {}
    group_standings: dict[str, list[str]] = {}

    for group in WC2026_GROUPS:
        exp_pts = {t: 0.0 for t in group["teams"]}
        for match in group["matches"]:
            h, a = match["home"], match["away"]
            p_h, p_d, p_a = _neutral_probs(h, a, prob_cache)
            exp_pts[h] += p_h * 3 + p_d
            exp_pts[a] += p_a * 3 + p_d
        all_expected_pts.update(exp_pts)
        standings = sorted(
            group["teams"],
            key=lambda t: (exp_pts[t], -(get_fifa_rank(t) or 999)),
            reverse=True,
        )
        group_standings[group["id"]] = standings

    winners   = {gid: teams[0] for gid, teams in group_standings.items()}
    runners_up = {gid: teams[1] for gid, teams in group_standings.items()}

    # --- Best 8 third-place teams ---
    all_thirds = [(teams[2], gid) for gid, teams in group_standings.items()]
    all_thirds_sorted = sorted(
        all_thirds,
        key=lambda x: (
            all_expected_pts[x[0]],
            -(get_fifa_rank(x[0]) or 999),
        ),
        reverse=True,
    )
    best_thirds = all_thirds_sorted[:8]
    third_assignments = _assign_third_place_teams(best_thirds)

    # --- Round of 32 ---
    match_winners: dict[int, str] = {}
    r32_matches = []
    for slot in WC2026_R32:
        team1 = winners[slot["slot1_group"]] if slot["slot1_type"] == "W" else runners_up[slot["slot1_group"]]
        team2 = (
            runners_up[slot["slot2_group"]]
            if slot["slot2_type"] == "RU"
            else third_assignments.get(slot["match"], best_thirds[0][0])
        )
        p1, p2 = _knockout_neutral_probs(team1, team2, prob_cache)
        predicted_winner = team1 if p1 >= p2 else team2
        match_winners[slot["match"]] = predicted_winner
        r32_matches.append({
            "match_id": f"r32_{slot['match']}",
            "round": "Round of 32",
            "team1": team1, "team2": team2,
            "team1_win_prob": round(p1, 4),
            "team2_win_prob": round(p2, 4),
            "predicted_winner": predicted_winner,
        })
    rounds_out: list[dict] = [{"round": "Round of 32", "matches": r32_matches}]

    # --- Round of 16: official cross-pairings ---
    r16_matches = []
    for i, (ma, mb) in enumerate(WC2026_R16_PAIRS):
        team1, team2 = match_winners[ma], match_winners[mb]
        p1, p2 = _knockout_neutral_probs(team1, team2, prob_cache)
        predicted_winner = team1 if p1 >= p2 else team2
        match_winners[89 + i] = predicted_winner
        r16_matches.append({
            "match_id": f"r16_{i + 1}",
            "round": "Round of 16",
            "team1": team1, "team2": team2,
            "team1_win_prob": round(p1, 4),
            "team2_win_prob": round(p2, 4),
            "predicted_winner": predicted_winner,
        })
    # Reorder for visual bracket alignment (see module-level _R16_VIS).
    rounds_out.append({"round": "Round of 16", "matches": [r16_matches[i] for i in _R16_VIS]})

    # --- Quarter-Finals ---
    qf_matches = []
    for i, (ma, mb) in enumerate(WC2026_QF_PAIRS):
        team1, team2 = match_winners[ma], match_winners[mb]
        p1, p2 = _knockout_neutral_probs(team1, team2, prob_cache)
        predicted_winner = team1 if p1 >= p2 else team2
        match_winners[97 + i] = predicted_winner
        qf_matches.append({
            "match_id": f"qf_{i + 1}",
            "round": "Quarter-Final",
            "team1": team1, "team2": team2,
            "team1_win_prob": round(p1, 4),
            "team2_win_prob": round(p2, 4),
            "predicted_winner": predicted_winner,
        })
    rounds_out.append({"round": "Quarter-Final", "matches": qf_matches})

    # --- Semi-Finals ---
    sf_matches = []
    for i, (ma, mb) in enumerate(WC2026_SF_PAIRS):
        team1, team2 = match_winners[ma], match_winners[mb]
        p1, p2 = _knockout_neutral_probs(team1, team2, prob_cache)
        predicted_winner = team1 if p1 >= p2 else team2
        match_winners[101 + i] = predicted_winner
        sf_matches.append({
            "match_id": f"sf_{i + 1}",
            "round": "Semi-Final",
            "team1": team1, "team2": team2,
            "team1_win_prob": round(p1, 4),
            "team2_win_prob": round(p2, 4),
            "predicted_winner": predicted_winner,
        })
    rounds_out.append({"round": "Semi-Final", "matches": sf_matches})

    # --- 3rd Place Playoff ---
    sf_losers = []
    for i in range(len(WC2026_SF_PAIRS)):
        t1 = sf_matches[i]["team1"]
        t2 = sf_matches[i]["team2"]
        sf_losers.append(t2 if match_winners[101 + i] == t1 else t1)

    tp1, tp2 = sf_losers[0], sf_losers[1]
    p1_tp, p2_tp = _knockout_neutral_probs(tp1, tp2, prob_cache)
    third_place_winner = tp1 if p1_tp >= p2_tp else tp2
    rounds_out.append({
        "round": "3rd Place Playoff",
        "matches": [{
            "match_id": "third_place",
            "round": "3rd Place Playoff",
            "team1": tp1, "team2": tp2,
            "team1_win_prob": round(p1_tp, 4),
            "team2_win_prob": round(p2_tp, 4),
            "predicted_winner": third_place_winner,
        }],
    })

    # --- Final ---
    finalist1, finalist2 = match_winners[101], match_winners[102]
    p1, p2 = _knockout_neutral_probs(finalist1, finalist2, prob_cache)
    champion = finalist1 if p1 >= p2 else finalist2
    rounds_out.append({
        "round": "Final",
        "matches": [{
            "match_id": "final",
            "round": "Final",
            "team1": finalist1, "team2": finalist2,
            "team1_win_prob": round(p1, 4),
            "team2_win_prob": round(p2, 4),
            "predicted_winner": champion,
        }],
    })

    return {
        "rounds": rounds_out,
        "group_standings": group_standings,
        "champion": champion,
        "generated_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def predict_bracket_modal(
    modal_match_winners: dict[int, str],
    prob_cache: ProbCache,
    match_winner_counts: "dict[int, dict[str, int]] | None" = None,
) -> dict:
    """Build the WC2026 bracket using modal (most-likely) winners from Monte Carlo simulation.

    Uses the same group-stage and 3rd-place logic as predict_bracket(), but determines
    the winner of each knockout slot from simulation modal counts rather than raw probabilities.
    Falls back to higher-probability team when modal winner is neither slot team (rare upset paths).

    When match_winner_counts is provided, the Final (slot 103) and 3rd Place (slot 104) match
    cards display MC-frequency-based probabilities so the champion always appears as the favorite.
    """
    # --- Group stage expected standings (same as predict_bracket) ---
    all_expected_pts: dict[str, float] = {}
    group_standings: dict[str, list[str]] = {}
    for group in WC2026_GROUPS:
        exp_pts = {t: 0.0 for t in group["teams"]}
        for match in group["matches"]:
            h, a = match["home"], match["away"]
            p_h, p_d, p_a = _neutral_probs(h, a, prob_cache)
            exp_pts[h] += p_h * 3 + p_d
            exp_pts[a] += p_a * 3 + p_d
        all_expected_pts.update(exp_pts)
        standings = sorted(
            group["teams"],
            key=lambda t: (exp_pts[t], -(get_fifa_rank(t) or 999)),
            reverse=True,
        )
        group_standings[group["id"]] = standings

    winners    = {gid: teams[0] for gid, teams in group_standings.items()}
    runners_up = {gid: teams[1] for gid, teams in group_standings.items()}

    all_thirds = [(teams[2], gid) for gid, teams in group_standings.items()]
    all_thirds_sorted = sorted(
        all_thirds,
        key=lambda x: (all_expected_pts[x[0]], -(get_fifa_rank(x[0]) or 999)),
        reverse=True,
    )
    best_thirds = all_thirds_sorted[:8]
    third_assignments = _assign_third_place_teams(best_thirds)

    # --- Round of 32 ---
    match_predicted: dict[int, str] = {}
    r32_matches = []
    for slot in WC2026_R32:
        team1 = winners[slot["slot1_group"]] if slot["slot1_type"] == "W" else runners_up[slot["slot1_group"]]
        team2 = (
            runners_up[slot["slot2_group"]]
            if slot["slot2_type"] == "RU"
            else third_assignments.get(slot["match"], best_thirds[0][0])
        )
        p1, p2 = _knockout_neutral_probs(team1, team2, prob_cache)
        predicted_winner = modal_match_winners.get(slot["match"])
        if predicted_winner not in (team1, team2):
            predicted_winner = team1 if p1 >= p2 else team2
        match_predicted[slot["match"]] = predicted_winner
        r32_matches.append({
            "match_id": f"r32_{slot['match']}",
            "round": "Round of 32",
            "team1": team1, "team2": team2,
            "team1_win_prob": round(p1, 4),
            "team2_win_prob": round(p2, 4),
            "predicted_winner": predicted_winner,
        })
    rounds_out: list[dict] = [{"round": "Round of 32", "matches": r32_matches}]

    # --- Round of 16 ---
    r16_matches = []
    for i, (ma, mb) in enumerate(WC2026_R16_PAIRS):
        team1, team2 = match_predicted[ma], match_predicted[mb]
        p1, p2 = _knockout_neutral_probs(team1, team2, prob_cache)
        predicted_winner = modal_match_winners.get(89 + i)
        if predicted_winner not in (team1, team2):
            predicted_winner = team1 if p1 >= p2 else team2
        match_predicted[89 + i] = predicted_winner
        r16_matches.append({
            "match_id": f"r16_{i + 1}",
            "round": "Round of 16",
            "team1": team1, "team2": team2,
            "team1_win_prob": round(p1, 4),
            "team2_win_prob": round(p2, 4),
            "predicted_winner": predicted_winner,
        })
    # Reorder for visual bracket alignment (see module-level _R16_VIS).
    rounds_out.append({"round": "Round of 16", "matches": [r16_matches[i] for i in _R16_VIS]})

    # --- Quarter-Finals ---
    qf_matches = []
    for i, (ma, mb) in enumerate(WC2026_QF_PAIRS):
        team1, team2 = match_predicted[ma], match_predicted[mb]
        p1, p2 = _knockout_neutral_probs(team1, team2, prob_cache)
        predicted_winner = modal_match_winners.get(97 + i)
        if predicted_winner not in (team1, team2):
            predicted_winner = team1 if p1 >= p2 else team2
        match_predicted[97 + i] = predicted_winner
        qf_matches.append({
            "match_id": f"qf_{i + 1}",
            "round": "Quarter-Final",
            "team1": team1, "team2": team2,
            "team1_win_prob": round(p1, 4),
            "team2_win_prob": round(p2, 4),
            "predicted_winner": predicted_winner,
        })
    rounds_out.append({"round": "Quarter-Final", "matches": qf_matches})

    # --- Semi-Finals ---
    sf_matches = []
    for i, (ma, mb) in enumerate(WC2026_SF_PAIRS):
        team1, team2 = match_predicted[ma], match_predicted[mb]
        p1, p2 = _knockout_neutral_probs(team1, team2, prob_cache)
        predicted_winner = modal_match_winners.get(101 + i)
        if predicted_winner not in (team1, team2):
            predicted_winner = team1 if p1 >= p2 else team2
        match_predicted[101 + i] = predicted_winner
        sf_matches.append({
            "match_id": f"sf_{i + 1}",
            "round": "Semi-Final",
            "team1": team1, "team2": team2,
            "team1_win_prob": round(p1, 4),
            "team2_win_prob": round(p2, 4),
            "predicted_winner": predicted_winner,
        })
    rounds_out.append({"round": "Semi-Final", "matches": sf_matches})

    # --- 3rd Place Playoff ---
    sf_losers = []
    for i in range(len(WC2026_SF_PAIRS)):
        t1 = sf_matches[i]["team1"]
        t2 = sf_matches[i]["team2"]
        sf_losers.append(t2 if match_predicted[101 + i] == t1 else t1)
    tp1, tp2 = sf_losers[0], sf_losers[1]
    p1_tp, p2_tp = _knockout_neutral_probs(tp1, tp2, prob_cache)
    third_place_winner = modal_match_winners.get(104)
    if third_place_winner not in (tp1, tp2):
        third_place_winner = tp1 if p1_tp >= p2_tp else tp2
    # Use MC frequencies for 3rd place display probabilities when available
    if match_winner_counts and 104 in match_winner_counts:
        c1 = match_winner_counts[104].get(tp1, 0)
        c2 = match_winner_counts[104].get(tp2, 0)
        total = c1 + c2
        if total > 0:
            p1_tp, p2_tp = c1 / total, c2 / total
    rounds_out.append({
        "round": "3rd Place Playoff",
        "matches": [{
            "match_id": "third_place",
            "round": "3rd Place Playoff",
            "team1": tp1, "team2": tp2,
            "team1_win_prob": round(p1_tp, 4),
            "team2_win_prob": round(p2_tp, 4),
            "predicted_winner": third_place_winner,
        }],
    })

    # --- Final ---
    finalist1, finalist2 = match_predicted[101], match_predicted[102]
    p1, p2 = _knockout_neutral_probs(finalist1, finalist2, prob_cache)
    champion = modal_match_winners.get(103)
    if champion not in (finalist1, finalist2):
        champion = finalist1 if p1 >= p2 else finalist2
    # Use MC frequencies for Final display probabilities so champion always shows as favorite
    if match_winner_counts and 103 in match_winner_counts:
        c1 = match_winner_counts[103].get(finalist1, 0)
        c2 = match_winner_counts[103].get(finalist2, 0)
        total = c1 + c2
        if total > 0:
            p1, p2 = c1 / total, c2 / total
    rounds_out.append({
        "round": "Final",
        "matches": [{
            "match_id": "final",
            "round": "Final",
            "team1": finalist1, "team2": finalist2,
            "team1_win_prob": round(p1, 4),
            "team2_win_prob": round(p2, 4),
            "predicted_winner": champion,
        }],
    })

    return {
        "rounds": rounds_out,
        "group_standings": group_standings,
        "champion": champion,
        "generated_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def run_simulation(
    tracker: TeamStateTracker,
    model: Any,
    cfg: dict,
    n: int = 1000,
    squad_ratings: "dict | None" = None,
) -> dict:
    """Run n simulations. Pre-computes all match probabilities once before the loop."""
    from collections import Counter

    all_teams = {t: g["id"] for g in WC2026_GROUPS for t in g["teams"]}
    stage_keys = ["group_exit", "round_of_32", "round_of_16", "quarter_final",
                  "semi_final", "fourth_place", "third_place", "final", "champion"]
    counts: dict[str, dict[str, int]] = {t: {s: 0 for s in stage_keys} for t in all_teams}

    # Slots: R32 73-88, R16 89-96, QF 97-100, SF 101-102, Final 103, 3rd-place 104
    match_winner_counts: dict[int, Counter] = {
        m: Counter() for m in list(range(73, 103)) + [103, 104]
    }

    # Single batched model call covering all 48×47 pairs — O(1) lookups during simulation
    prob_cache = precompute_all_probabilities(tracker, model, cfg, squad_ratings=squad_ratings)

    rng = np.random.default_rng(cfg.get("project", {}).get("random_state", 42))
    for _ in range(n):
        stage_results, match_winners = simulate_once(
            tracker, model, cfg, rng, prob_cache=prob_cache
        )
        for team, stage in stage_results.items():
            counts[team][stage] += 1
        for slot, winner in match_winners.items():
            match_winner_counts[slot][winner] += 1

    modal_match_winners: dict[int, str] = {
        slot: counter.most_common(1)[0][0]
        for slot, counter in match_winner_counts.items()
        if counter
    }

    teams_out = []
    for team, group_id in all_teams.items():
        teams_out.append({
            "team": team,
            "group": group_id,
            **{s: round(counts[team][s] / n, 4) for s in stage_keys},
        })

    return {
        "n_simulations": n,
        "teams": teams_out,
        "modal_match_winners": modal_match_winners,
        # Raw per-slot win counts (popped by services.py before API response)
        "match_winner_counts": {slot: dict(counter) for slot, counter in match_winner_counts.items()},
        "generated_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
    }
