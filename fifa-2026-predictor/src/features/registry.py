"""
Feature block registry.

Provides a central, authoritative place to define, toggle, and execute
feature blocks. Each block is a named unit of feature logic that contributes
key-value pairs to the match row dict.

Usage
-----
Import the module-level singleton and decorate or register blocks::

    from src.features.registry import get_registry

    registry = get_registry()
    registry.enable("player_aggregate")
    extra = registry.build_all(context)   # dict of extra features

The four standard blocks ("form", "elo", "tournament", "player_aggregate")
are pre-registered. The first three are structural placeholders (the actual
values come from build_match_row). The "player_aggregate" block is disabled
by default until player data sources are populated.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureBlock:
    """A named, toggleable unit of feature-building logic."""
    name: str
    build_fn: Callable[[Dict[str, Any]], Dict[str, Any]]
    enabled: bool = True
    description: str = ""
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Registry class
# ---------------------------------------------------------------------------

class FeatureRegistry:
    """
    Central registry for feature blocks.

    Blocks are keyed by name. ``build_all(context)`` executes every enabled
    block and merges their outputs into one dict. Exceptions inside individual
    blocks are caught and logged so a single failing block never crashes the
    whole pipeline.
    """

    def __init__(self) -> None:
        self._blocks: Dict[str, FeatureBlock] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, block: FeatureBlock) -> None:
        """Register a FeatureBlock. Overwrites any existing block with the same name."""
        if block.name in self._blocks:
            log.debug("Overwriting existing feature block '%s'", block.name)
        self._blocks[block.name] = block

    def feature_block(
        self,
        name: str,
        *,
        enabled: bool = True,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Callable:
        """
        Decorator that registers a function as a named feature block.

        The decorated function must accept a single ``context`` dict and
        return a dict of feature_name -> value.
        """
        def decorator(fn: Callable) -> Callable:
            self.register(FeatureBlock(
                name=name,
                build_fn=fn,
                enabled=enabled,
                description=description,
                tags=tags or [],
            ))
            return fn
        return decorator

    # ------------------------------------------------------------------
    # Enable / disable
    # ------------------------------------------------------------------

    def enable(self, name: str) -> None:
        """Enable a registered block."""
        self._require(name).enabled = True

    def disable(self, name: str) -> None:
        """Disable a block; it stays registered but is skipped in build_all."""
        self._require(name).enabled = False

    def set_enabled(self, name: str, enabled: bool) -> None:
        self._require(name).enabled = enabled

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def build_all(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all enabled blocks and merge their outputs.

        If two blocks emit the same key, the later-registered block wins.
        Exceptions are logged and the block is skipped.
        """
        features: Dict[str, Any] = {}
        for block in self._blocks.values():
            if not block.enabled:
                continue
            try:
                result = block.build_fn(context)
                if result:
                    features.update(result)
            except Exception as exc:
                log.warning(
                    "Feature block '%s' raised an exception and was skipped: %s",
                    block.name, exc,
                )
        return features

    def build_block(self, name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single named block regardless of its enabled state."""
        return self._require(name).build_fn(context)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_blocks(self) -> List[str]:
        """Return names of all registered blocks (enabled and disabled)."""
        return list(self._blocks.keys())

    def enabled_blocks(self) -> List[str]:
        """Return names of enabled blocks in registration order."""
        return [name for name, b in self._blocks.items() if b.enabled]

    def get_block(self, name: str) -> Optional[FeatureBlock]:
        """Return the FeatureBlock for *name*, or None."""
        return self._blocks.get(name)

    def is_enabled(self, name: str) -> bool:
        block = self._blocks.get(name)
        return block.enabled if block else False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require(self, name: str) -> FeatureBlock:
        if name not in self._blocks:
            raise KeyError(f"No feature block registered with name '{name}'")
        return self._blocks[name]

    def __len__(self) -> int:
        return len(self._blocks)

    def __contains__(self, name: str) -> bool:
        return name in self._blocks

    def __repr__(self) -> str:
        blocks = [
            f"{n}({'on' if b.enabled else 'off'})"
            for n, b in self._blocks.items()
        ]
        return f"FeatureRegistry([{', '.join(blocks)}])"


# ---------------------------------------------------------------------------
# Built-in block functions
# ---------------------------------------------------------------------------

def _form_block(context: Dict[str, Any]) -> Dict[str, Any]:
    """Intentional no-op placeholder.

    Form features are assembled by ``match_row_builder.build_match_row`` — not
    here — to keep training and inference in a single code path and prevent
    train/serve skew. This block exists so that "form" appears in
    ``list_blocks()`` / ``enabled_blocks()`` for introspection; it will never
    contribute features through ``build_all()``.
    """
    return {}


def _elo_block(context: Dict[str, Any]) -> Dict[str, Any]:
    """Intentional no-op placeholder.

    Elo features are assembled by ``match_row_builder.build_match_row``.
    This block exists only for registry introspection — it never contributes
    features through ``build_all()``.
    """
    return {}


def _tournament_block(context: Dict[str, Any]) -> Dict[str, Any]:
    """Intentional no-op placeholder.

    Tournament/competition context features are assembled by
    ``match_row_builder.build_match_row``. This block exists only for
    registry introspection — it never contributes features through
    ``build_all()``.
    """
    return {}


def _player_aggregate_block(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Player aggregate feature block.

    Reads optional player data slices from *context* and returns
    home_/away_-prefixed player-derived features.

    Expected context keys (all optional):
      home_team    (str)
      away_team    (str)
      match_date   (str, ISO YYYY-MM-DD)
      match_id     (str, optional)
      rosters_df   (pd.DataFrame, optional)
      ratings_df   (pd.DataFrame, optional)
      injuries_df  (pd.DataFrame, optional)
      lineups_df   (pd.DataFrame, optional)
    """
    home_team = context.get("home_team")
    away_team = context.get("away_team")
    match_date = context.get("match_date")

    if not home_team or not away_team or not match_date:
        return {}

    from src.features.player_aggregator import build_player_match_features

    return build_player_match_features(
        home_team=str(home_team),
        away_team=str(away_team),
        match_date=str(match_date),
        match_id=context.get("match_id"),
        rosters_df=context.get("rosters_df"),
        ratings_df=context.get("ratings_df"),
        injuries_df=context.get("injuries_df"),
        lineups_df=context.get("lineups_df"),
    )


# ---------------------------------------------------------------------------
# Module-level singleton + pre-registered blocks
# ---------------------------------------------------------------------------

_REGISTRY = FeatureRegistry()

_REGISTRY.register(FeatureBlock(
    name="form",
    build_fn=_form_block,
    enabled=True,
    description="Team form features (built by match_row_builder)",
    tags=["core"],
))
_REGISTRY.register(FeatureBlock(
    name="elo",
    build_fn=_elo_block,
    enabled=True,
    description="Elo rating features (built by match_row_builder)",
    tags=["core"],
))
_REGISTRY.register(FeatureBlock(
    name="tournament",
    build_fn=_tournament_block,
    enabled=True,
    description="Tournament/competition context features (built by match_row_builder)",
    tags=["core"],
))
_REGISTRY.register(FeatureBlock(
    name="player_aggregate",
    build_fn=_player_aggregate_block,
    enabled=False,   # disabled until real player data sources are populated
    description="Player-derived team-level features (ratings, injuries, lineups)",
    tags=["player", "experimental"],
))


def get_registry() -> FeatureRegistry:
    """Return the module-level singleton FeatureRegistry."""
    return _REGISTRY
