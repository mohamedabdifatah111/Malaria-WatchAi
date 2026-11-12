"""Configuration and path resolution for the ML pipeline.

Shared settings come from the repo-root ``config.yaml`` (owned by the data
layer); ML settings from ``ml/config/ml_config.yaml``.

Raw inputs are read from ``data/raw`` by default. Set ``MAL_RAW_DIR`` to read
them from another checkout (for example a git worktree that shares one data
download). Outputs always go to this checkout.
"""
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_ROOT = REPO_ROOT / "ml"


@lru_cache(maxsize=1)
def shared() -> dict:
    with open(REPO_ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def ml() -> dict:
    with open(ML_ROOT / "config" / "ml_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def seed() -> int:
    return int(shared()["seed"])


def countries() -> list[str]:
    return list(ml()["countries"])


def prediction_year() -> int:
    return int(shared()["prediction_year"])


def survey_years() -> tuple[int, int]:
    lo, hi = shared()["survey_years"]
    return int(lo), int(hi)


def crs_area() -> str:
    return shared()["crs"]["area"]


def crs_distance() -> str:
    return shared()["crs"]["distance"]


def grid_resolution_m() -> float:
    return float(shared()["grid_resolution_m"])


def raw_dir() -> Path:
    env = os.environ.get("MAL_RAW_DIR")
    return Path(env) if env else REPO_ROOT / shared()["paths"]["raw"]


def manifest_path() -> Path:
    env = os.environ.get("MAL_RAW_DIR")
    if env:
        candidate = Path(env).parent / "manifest.csv"
        if candidate.exists():
            return candidate
    return REPO_ROOT / shared()["paths"]["manifest"]


def interim_dir() -> Path:
    p = REPO_ROOT / shared()["paths"]["interim"]
    p.mkdir(parents=True, exist_ok=True)
    return p


def processed_dir() -> Path:
    p = REPO_ROOT / shared()["paths"]["processed"]
    p.mkdir(parents=True, exist_ok=True)
    return p


def outputs_dir() -> Path:
    p = ML_ROOT / "outputs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_hash() -> str:
    """Short hash of both config files, stored in every output's metadata."""
    h = hashlib.sha256()
    for p in (REPO_ROOT / "config.yaml", ML_ROOT / "config" / "ml_config.yaml"):
        h.update(p.read_bytes())
    return h.hexdigest()[:12]
