"""Malaria Atlas Project PfPR and PvPR survey points via the MAP GeoServer WFS.

Saves the raw GeoJSON per country and parasite, untouched. Cleaning (dropping
rows with "No permission to release data", missing examined/positives, years
outside 2000-2024) happens in build.py, not here, so the raw pull stays a
faithful copy of what MAP served.

Fallback: manual CSV export from https://data.malariaatlas.org (log it in
DATA.md as a manual step). DHS/MIS needs registration - last resort only.
"""
from __future__ import annotations

from mal.config import countries
from mal.fetch._common import get_json, log, raw_dir, save_records

WFS = "https://data.malariaatlas.org/geoserver/Malaria/ows"
# Latest published survey layers on the server (checked 2026-11-12).
LAYERS = {
    "pfpr": "Malaria:202406_Global_Pf_Parasite_Rate_Surveys",
    "pvpr": "Malaria:202406_Global_Pv_Parasite_Rate_Surveys",
}
LICENCE = "CC BY 4.0 (Malaria Atlas Project); per-record permissions_info applies"
PAGE = 5000


def fetch_layer(layer: str, iso3: str) -> dict:
    """All features for one country as a GeoJSON FeatureCollection (EPSG:4326)."""
    feats: list[dict] = []
    start = 0
    while True:
        params = {
            "service": "WFS", "version": "2.0.0", "request": "GetFeature",
            "typeNames": layer, "outputFormat": "application/json",
            "CQL_FILTER": f"country_id='{iso3}'",
            "count": PAGE, "startIndex": start, "sortBy": "id",
        }
        page = get_json(WFS, params)["features"]
        feats.extend(page)
        if len(page) < PAGE:
            return {"type": "FeatureCollection", "features": feats}
        start += PAGE


def run(force: bool = False) -> None:
    out = raw_dir("map")
    for key, layer in LAYERS.items():
        for iso3 in countries():
            dest = out / f"{key}_{iso3}.geojson"
            url = (f"{WFS}?service=WFS&version=2.0.0&request=GetFeature"
                   f"&typeNames={layer}&outputFormat=application/json"
                   f"&CQL_FILTER=country_id='{iso3}'")
            save_records(lambda l=layer, c=iso3: fetch_layer(l, c), dest,
                         f"map_{key}_{iso3}".lower(), url, LICENCE, force=force)
    log.info("        MAP surveys done (raw; filter unreleased rows in build.py)")
