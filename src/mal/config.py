"""Load config.yaml once and resolve paths relative to the repo root."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def path(key: str) -> Path:
    """Absolute path for an entry under `paths:` in config.yaml."""
    return ROOT / load_config()["paths"][key]


def countries() -> dict[str, str]:
    """ISO3 -> ISO2 mapping for the study countries."""
    return dict(load_config()["countries"])
