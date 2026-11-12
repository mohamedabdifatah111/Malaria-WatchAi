"""Shared fetch helpers: HTTP with retries, hash-checked caching, manifest rows.

Every file a fetch script saves gets one row in data/manifest.csv with the
contract columns: source_id, url, accessed_utc, sha256, licence, rows.
A file is skipped on re-run when it exists and its SHA-256 matches the
manifest, so `python -m mal.fetch` is cheap to repeat.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from mal.config import ROOT, load_config, path

log = logging.getLogger("mal.fetch")

MANIFEST_COLUMNS = ["source_id", "url", "accessed_utc", "sha256", "licence", "rows"]


# --------------------------------------------------------------------------- HTTP
_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        cfg = load_config()["fetch"]
        s = requests.Session()
        retry = Retry(
            total=cfg["retries"],
            backoff_factor=2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))
        s.headers["User-Agent"] = cfg["user_agent"]
        _session = s
    return _session


def timeout() -> int:
    return load_config()["fetch"]["timeout_s"]


def get_json(url: str, params: dict | None = None) -> Any:
    r = session().get(url, params=params, timeout=timeout())
    r.raise_for_status()
    return r.json()


# ----------------------------------------------------------------------- hashing
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------- manifest
def read_manifest() -> dict[str, dict]:
    mp = path("manifest")
    if not mp.exists():
        return {}
    with open(mp, newline="", encoding="utf-8") as f:
        return {row["source_id"]: row for row in csv.DictReader(f)}


def write_manifest_row(source_id: str, url: str, sha256: str, licence: str,
                       rows: int | None) -> None:
    mp = path("manifest")
    mp.parent.mkdir(parents=True, exist_ok=True)
    current = read_manifest()
    current[source_id] = {
        "source_id": source_id,
        "url": url,
        "accessed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": sha256,
        "licence": licence,
        "rows": "" if rows is None else str(rows),
    }
    tmp = mp.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        w.writeheader()
        for sid in sorted(current):
            w.writerow({k: current[sid].get(k, "") for k in MANIFEST_COLUMNS})
    _replace_with_retry(tmp, mp)


def _replace_with_retry(src: Path, dst: Path, attempts: int = 10) -> None:
    """os.replace, tolerant of Windows locks (antivirus, indexer, an open viewer)."""
    for i in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(0.2 * (i + 1))
    try:  # last resort: overwrite in place (works if the holder allows sharing)
        dst.write_bytes(src.read_bytes())
        src.unlink(missing_ok=True)
    except PermissionError as e:
        raise ManifestLocked(dst) from e


class ManifestLocked(RuntimeError):
    def __init__(self, p: Path):
        super().__init__(f"{rel(p)} is open in another program (Excel locks CSVs). "
                         "Close it and re-run; cached files are skipped.")


def check_manifest_writable() -> None:
    """Fail before downloading anything if the manifest can't be written."""
    mp = path("manifest")
    if not mp.exists():
        return
    try:
        with open(mp, "r+b"):
            pass
    except PermissionError as e:
        raise ManifestLocked(mp) from e


def is_cached(source_id: str, dest: Path) -> bool:
    """True when dest exists and matches the hash recorded in the manifest."""
    row = read_manifest().get(source_id)
    return bool(row) and dest.exists() and sha256_file(dest) == row["sha256"]


def raw_dir(*parts: str) -> Path:
    d = path("raw").joinpath(*parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def rel(p: Path) -> str:
    return p.resolve().relative_to(ROOT).as_posix()


# ------------------------------------------------------------------- downloaders
def download(url: str, dest: Path, source_id: str, licence: str,
             rows: int | None = None, force: bool = False,
             params: dict | None = None,
             count: Callable[[Path], int] | None = None) -> Path:
    """Stream a URL to dest (via a .part file) and record it in the manifest.

    `count(dest)` may be given to compute the row count after download.
    """
    if not force and is_cached(source_id, dest):
        log.info("cached  %-40s %s", source_id, rel(dest))
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    log.info("get     %-40s %s", source_id, url)
    with session().get(url, params=params, stream=True, timeout=timeout()) as r:
        r.raise_for_status()
        with open(part, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    os.replace(part, dest)
    if count is not None:
        rows = count(dest)
    full_url = requests.Request("GET", url, params=params).prepare().url
    write_manifest_row(source_id, full_url, sha256_file(dest), licence, rows)
    log.info("saved   %-40s %s (%.1f MB)", source_id, rel(dest), dest.stat().st_size / 1e6)
    return dest


def save_records(records: Any, dest: Path,
                 source_id: str, url: str, licence: str,
                 force: bool = False) -> Path:
    """Save API records as JSON (raw, untouched) and record the row count.

    `records` may be a callable so cached runs skip the API call entirely.
    """
    if not force and is_cached(source_id, dest):
        log.info("cached  %-40s %s", source_id, rel(dest))
        return dest
    data = records() if callable(records) else records
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    n = len(data["features"]) if isinstance(data, dict) and "features" in data else len(data)
    write_manifest_row(source_id, url, sha256_file(dest), licence, n)
    log.info("saved   %-40s %s (%d records)", source_id, rel(dest), n)
    return dest


def record_existing(dest: Path, source_id: str, url: str, licence: str,
                    rows: int | None = None) -> None:
    """Add a manifest row for a file produced locally (e.g. a computed composite)."""
    write_manifest_row(source_id, url, sha256_file(dest), licence, rows)
