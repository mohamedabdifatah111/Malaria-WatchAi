"""Output writers. Every Parquet output carries run metadata in its schema."""
from __future__ import annotations

import json
import logging
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ml.src import config

log = logging.getLogger("ml")

_RUN_TS = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_timestamp() -> str:
    return _RUN_TS


def run_metadata(extra: dict | None = None) -> dict:
    cfg = config.ml()
    meta = {
        "pipeline": "malaria-watchai-ml",
        "model_name": cfg["model_name"],
        "model_version": cfg["model_version"],
        "prediction_year": config.prediction_year(),
        "generated_at": _RUN_TS,
        "config_hash": config.config_hash(),
        "seed": config.seed(),
        "python": platform.python_version(),
    }
    if extra:
        meta.update(extra)
    return meta


def write_parquet(df: pd.DataFrame, name: str, extra_meta: dict | None = None,
                  directory: Path | None = None) -> Path:
    """Write ``df`` to ``data/processed/<name>`` with run metadata attached."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    out = (directory or config.processed_dir()) / name
    table = pa.Table.from_pandas(df, preserve_index=False)
    md = dict(table.schema.metadata or {})
    md[b"malaria_watchai"] = json.dumps(run_metadata(extra_meta), default=str).encode()
    table = table.replace_schema_metadata(md)
    pq.write_table(table, out)
    log.info("wrote %s (%d rows)", out.relative_to(config.REPO_ROOT), len(df))
    return out


def write_geoparquet(gdf, name: str, extra_meta: dict | None = None,
                     directory: Path | None = None) -> Path:
    out = (directory or config.processed_dir()) / name
    gdf.to_parquet(out, index=False)
    # Re-open to attach run metadata next to the GeoParquet 'geo' key.
    import pyarrow.parquet as pq

    table = pq.read_table(out)
    md = dict(table.schema.metadata or {})
    md[b"malaria_watchai"] = json.dumps(run_metadata(extra_meta), default=str).encode()
    pq.write_table(table.replace_schema_metadata(md), out)
    log.info("wrote %s (%d rows)", out.relative_to(config.REPO_ROOT), len(gdf))
    return out


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.isoformat()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def clean_json(obj):
    """Replace NaN/inf with None recursively so the JSON is standards-valid."""
    if isinstance(obj, dict):
        return {str(k): clean_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean_json(v) for v in obj]
    if isinstance(obj, float) and not np.isfinite(obj):
        return None
    if isinstance(obj, np.floating):
        return None if not np.isfinite(obj) else float(obj)
    return obj


def write_json(obj: dict, name: str, directory: Path | None = None) -> Path:
    out = (directory or config.processed_dir()) / name
    with open(out, "w", encoding="utf-8") as f:
        json.dump(clean_json(json.loads(json.dumps(obj, default=_json_default))), f,
                  indent=2, allow_nan=False)
    log.info("wrote %s", out.relative_to(config.REPO_ROOT))
    return out
