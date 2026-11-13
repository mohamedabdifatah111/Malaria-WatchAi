"""Administrative boundaries (geoBoundaries gbOpen) for the study countries.

``region_id`` is the geoBoundaries ``shapeID`` - stable within a geoBoundaries
release (the commit is pinned in data/manifest.csv). ADM2 parents are assigned
by the ADM1 polygon containing each ADM2 representative point, because ADM1 and
ADM2 layers come from different national sources and do not always nest.
"""
from __future__ import annotations

from functools import lru_cache

import geopandas as gpd
import pandas as pd

from ml.src import config


def _read(iso3: str, level: str) -> gpd.GeoDataFrame:
    p = config.raw_dir() / "boundaries" / f"geoBoundaries-{iso3}-{level}.geojson"
    if not p.exists():
        raise FileNotFoundError(f"missing boundary file {p}; run `python -m mal.fetch`")
    g = gpd.read_file(p)
    g = g.to_crs("EPSG:4326") if g.crs and g.crs.to_epsg() != 4326 else g.set_crs("EPSG:4326", allow_override=True)
    g["geometry"] = g.geometry.make_valid()
    return gpd.GeoDataFrame({
        "country": iso3,
        "admin_level": level,
        "region_id": g["shapeID"].astype(str),
        "region_name": g["shapeName"].astype(str),
    }, geometry=g.geometry, crs="EPSG:4326")


@lru_cache(maxsize=1)
def load_regions() -> gpd.GeoDataFrame:
    """All ADM0/ADM1/ADM2 polygons with ``parent_id`` (EPSG:4326)."""
    frames = []
    for iso3 in config.countries():
        adm0 = _read(iso3, "ADM0")
        adm1 = _read(iso3, "ADM1")
        adm2 = _read(iso3, "ADM2")
        adm0["parent_id"] = None
        adm1["parent_id"] = adm0["region_id"].iloc[0]
        rep = gpd.GeoDataFrame(adm2[["region_id"]], geometry=adm2.representative_point(), crs=adm2.crs)
        j = gpd.sjoin(rep, adm1[["region_id", "geometry"]].rename(columns={"region_id": "parent"}),
                      how="left", predicate="within")
        j = j[~j.index.duplicated()]
        missing = j["parent"].isna()
        if missing.any():  # representative point fell in a gap between layers
            near = gpd.sjoin_nearest(rep[missing].to_crs(config.crs_distance()),
                                     adm1[["region_id", "geometry"]].rename(columns={"region_id": "parent"})
                                     .to_crs(config.crs_distance()), how="left")
            near = near[~near.index.duplicated()]
            j.loc[missing, "parent"] = near["parent"]
        adm2["parent_id"] = j["parent"].values
        frames += [adm0, adm1, adm2]
    out = pd.concat(frames, ignore_index=True)
    return gpd.GeoDataFrame(out, geometry="geometry", crs="EPSG:4326")


def level(admin_level: str) -> gpd.GeoDataFrame:
    r = load_regions()
    return r[r["admin_level"] == admin_level].reset_index(drop=True)


def assign_regions(points: gpd.GeoDataFrame, buffer_km: float = 5.0) -> pd.DataFrame:
    """Return adm0/adm1/adm2 ids for each point (index-aligned).

    Points inside a polygon get that polygon; points within ``buffer_km`` of a
    polygon (coastline / border precision) get the nearest one; others get NA.
    """
    pts = points[["geometry"]].copy()
    out = pd.DataFrame(index=points.index)
    pts_d = pts.to_crs(config.crs_distance())
    for lvl in ("ADM0", "ADM1", "ADM2"):
        polys = level(lvl)[["region_id", "country", "geometry"]].to_crs(config.crs_distance())
        near = gpd.sjoin_nearest(pts_d, polys, how="left", max_distance=buffer_km * 1000.0,
                                 distance_col="_d")
        near = near[~near.index.duplicated(keep="first")]
        out[f"{lvl.lower()}_id"] = near["region_id"].reindex(points.index)
        if lvl == "ADM0":
            out["adm0_country"] = near["country"].reindex(points.index)
            out["dist_outside_country_km"] = (near["_d"] / 1000.0).reindex(points.index)
    return out


def region_table() -> pd.DataFrame:
    """Non-spatial lookup: region_id -> country, level, name, parent."""
    r = load_regions()
    return pd.DataFrame(r.drop(columns="geometry"))
