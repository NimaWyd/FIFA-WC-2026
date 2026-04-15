"""Shared utility helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_config(config_path: str = "configs/config.yaml") -> dict[str, Any]:
    """Load YAML config from project root."""
    absolute_path = PROJECT_ROOT / config_path
    if not absolute_path.exists():
        raise FileNotFoundError(f"Config file not found: {absolute_path}")

    with absolute_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def ensure_parent_dir(path: Path) -> None:
    """Create parent directory if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
