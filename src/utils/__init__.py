"""
src/utils/__init__.py
─────────────────────
Shared helpers used across the entire project.

Public API
----------
- load_config()          → dict  – reads config/app.yaml (cached)
- get_project_root()     → Path  – absolute path to the repo root
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml


def get_project_root() -> Path:
    """Return the absolute path to the repository root (contains main.py)."""
    return Path(__file__).resolve().parents[2]


@functools.lru_cache(maxsize=1)
def load_config() -> dict:
    """
    Load and cache ``config/app.yaml``.

    Returns an empty dict if the file does not exist so that callers
    can always do ``load_config().get("key", default)`` safely.
    """
    config_path = get_project_root() / "config" / "app.yaml"
    if not config_path.exists():
        return {}
    with config_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}
