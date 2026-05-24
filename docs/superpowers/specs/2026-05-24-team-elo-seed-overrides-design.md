# Team Elo Seed Overrides

**Date:** 2026-05-24  
**Status:** Approved

## Problem

USA (FIFA rank 16) is the highest-ranked team in Group D yet finishes last in simulation and individual match predictions. Their historical Elo (1801) is the lowest in the group due to bad 2025 results (0-4 vs Switzerland, 2-5 vs Belgium, 0-2 vs Portugal). Turkey (rank 22, Elo 1864), Australia (rank 27, Elo 1848), and Paraguay (rank 40, Elo 1810) all outrank USA in the model.

## Solution

Add a `team_elo_seeds` config block that overrides specific teams' Elo ratings **after** full match history replay, immediately before any tournament predictions. Seeds are post-replay corrections, not initial values — history is still fully replayed for all other state (form, H2H, goals, etc.).

## Design

### 1. `configs/config.yaml`

Add under `simulation`:

```yaml
simulation:
  team_elo_seeds:
    "United States": 1850.0
```

Value reasoning: USA (rank 16) should sit just above Australia (natural Elo 1848) and well above Paraguay (1810), while remaining below Turkey (1864) which beat USA in June 2025.

### 2. `src/simulation/tournament.py` — `build_tournament_states`

After the existing `penalty_elo_corrections` block:

```python
for team, elo in cfg.get("simulation", {}).get("team_elo_seeds", {}).items():
    tracker._ratings[team] = elo
```

### 3. `src/app/predict_match.py` — `predict_match`

After `tracker.replay_history(history)`:

```python
for team, elo in cfg.get("simulation", {}).get("team_elo_seeds", {}).items():
    tracker._ratings[team] = elo
```

## Scope

- Affects simulation bracket, Monte Carlo runs, and individual `/predict` match predictions.
- Does not touch training data, feature computation, or model artifacts — no retraining needed.
- Follows the existing `penalty_elo_corrections` pattern already in `build_tournament_states`.

## Trade-offs

- Manual: requires human judgment to pick seed values. Seeds should be revisited if significant new match data is added.
- Transparent: values are explicit in config, easy to adjust or remove.
- No train/serve skew: Elo seeds are applied at inference time only; training uses unmodified historical Elo.
