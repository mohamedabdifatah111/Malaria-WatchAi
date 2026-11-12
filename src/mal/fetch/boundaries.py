"""geoBoundaries gbOpen ADM0/ADM1/ADM2 polygons for the four countries.

Note: in Kenya ADM1 = counties (e.g. Busia County), ADM2 = sub-counties.
Fallback if geoBoundaries is down: GADM (check its licence before use).
"""
from __future__ import annotations

import json
from pathlib import Path

from mal.config import countries
from mal.fetch._common import download, get_json, raw_dir

API = "https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{level}/"
LEVELS = ("ADM0", "ADM1", "ADM2")


def geojson_count(p: Path) -> int:
    with open(p, encoding="utf-8") as f:
        return len(json.load(f)["features"])


def run(force: bool = False) -> None:
    out = raw_dir("boundaries")
    for iso3 in countries():
        for level in LEVELS:
            dest = out / f"geoBoundaries-{iso3}-{level}.geojson"
            sid = f"geoboundaries_{iso3}_{level}".lower()
            meta = get_json(API.format(iso3=iso3, level=level))
            licence = meta.get("boundaryLicense") or "see geoBoundaries metadata"
            download(meta["gjDownloadURL"], dest, sid, licence,
                     force=force, count=geojson_count)
