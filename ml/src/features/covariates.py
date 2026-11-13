"""Environmental covariates on the 5 km grid and at survey points.

Temporal status of each covariate (see ASSUMPTIONS.md):
  temp_*, precip_*   WorldClim 2.1 1970-2000 climatology (NOT 2020 observations)
  elevation_m        WorldClim 2.1 elevation (SRTM-derived), static
  ndvi_2020          MODIS MOD13A1 2020 annual median (applied to all survey years)
  pop / density      WorldPop 2020 UN-adjusted (applied to all survey years)
  urban_class        GHSL SMOD 2020 degree of urbanisation (applied to all years)
  dist_water_km      HydroRIVERS (Strahler >= threshold) + Natural Earth lakes, static
"""
from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.windows import from_bounds
from shapely import STRtree

from ml.src import config
from ml.src.features.grid import GridSpec

log = logging.getLogger("ml.covariates")

SMOD_TO_URBAN = {30: 2, 23: 1, 22: 1, 21: 1, 13: 0, 12: 0, 11: 0}  # 10 = water -> NaN


def _raw(*parts) -> Path:
    return config.raw_dir().joinpath(*parts)


def _reproject(paths: list[str], band: int, spec: GridSpec, resampling: Resampling) -> np.ndarray:
    """Reproject one band of one-or-more rasters onto the grid (first non-NaN wins)."""
    out = np.full(spec.shape, np.nan, dtype="float32")
    left, top = spec.transform.c, spec.transform.f
    gb = (left, top - spec.height * spec.res, left + spec.width * spec.res, top)
    for p in paths:
        with rasterio.open(p) as src:
            sb = transform_bounds(spec.crs, src.crs, *gb, densify_pts=21)
            pad = 2 * max(abs(src.res[0]), abs(src.res[1]))
            sb = (max(sb[0] - pad, src.bounds.left), max(sb[1] - pad, src.bounds.bottom),
                  min(sb[2] + pad, src.bounds.right), min(sb[3] + pad, src.bounds.top))
            if sb[0] >= sb[2] or sb[1] >= sb[3]:
                continue
            win = from_bounds(*sb, transform=src.transform).round_offsets().round_lengths()
            arr = src.read(band, window=win).astype("float32")
            if src.nodata is not None and not np.isnan(src.nodata):
                arr[arr == src.nodata] = np.nan
            tmp = np.full(spec.shape, np.nan, dtype="float32")
            reproject(arr, tmp, src_transform=src.window_transform(win), src_crs=src.crs,
                      src_nodata=np.nan, dst_transform=spec.transform, dst_crs=spec.crs,
                      dst_nodata=np.nan, resampling=resampling)
            out = np.where(np.isnan(out), tmp, out)
    return out


def population_to_grid(paths: dict[str, str], spec: GridSpec,
                       country_arr: np.ndarray) -> tuple[np.ndarray, dict]:
    """Sum WorldPop 1 km counts into grid cells by pixel centre.

    ``paths`` maps ISO3 -> that country's WorldPop raster; ``country_arr`` holds
    the ISO3 of each grid cell ('' outside the study area). A pixel whose centre
    lands in a cell of another country, the sea or a lake is moved to the
    nearest cell of its own country, so each country's total is conserved.
    """
    from scipy import ndimage

    acc = np.zeros(spec.shape, dtype="float64")
    check = {}
    for iso3, p in paths.items():
        own = country_arr == iso3
        _, (ri, ci) = ndimage.distance_transform_edt(~own, return_indices=True)
        with rasterio.open(p) as src:
            a = src.read(1, masked=True)
            rows, cols = np.nonzero(~np.ma.getmaskarray(a) & (a.filled(0) > 0))
            vals = a.data[rows, cols].astype("float64")
            t = src.transform
            xs = t.c + (cols + 0.5) * t.a
            ys = t.f + (rows + 0.5) * t.e
            gx, gy = Transformer.from_crs(src.crs, spec.crs, always_xy=True).transform(xs, ys)
        r, c = spec.rowcol(gx, gy)
        r = np.clip(r, 0, spec.height - 1)
        c = np.clip(c, 0, spec.width - 1)
        moved = ~own[r, c]
        r2, c2 = ri[r, c], ci[r, c]
        np.add.at(acc, (r2, c2), vals)
        check[iso3] = {"raster_total": float(vals.sum()),
                       "reassigned_to_nearest_own_cell": float(vals[moved].sum()),
                       "reassigned_share": float(vals[moved].sum() / vals.sum())}
    return acc, check


def distance_to_water_km(x_eqd: np.ndarray, y_eqd: np.ndarray) -> np.ndarray:
    """Distance (km, Africa Equidistant Conic) to the nearest river reach or lake."""
    bbox = tuple(config.shared()["bbox"])
    k = config.ml()["covariates"]["river_min_strahler"]
    rz = _raw("hydro", "HydroRIVERS_v10_af_shp.zip").as_posix()
    rivers = gpd.read_file(f"zip://{rz}!HydroRIVERS_v10_af_shp/HydroRIVERS_v10_af.shp",
                           bbox=bbox, where=f"ORD_STRA >= {int(k)}", columns=["ORD_STRA"])
    lz = _raw("hydro", "ne_10m_lakes.zip").as_posix()
    lakes = gpd.read_file(f"zip://{lz}!ne_10m_lakes.shp", bbox=bbox, columns=["name"])
    geoms = pd.concat([rivers.to_crs(config.crs_distance()).geometry,
                       lakes.to_crs(config.crs_distance()).geometry], ignore_index=True)
    tree = STRtree(geoms.values)
    pts = gpd.points_from_xy(x_eqd, y_eqd)
    _, dist = tree.query_nearest(pts, return_distance=True, all_matches=False)
    log.info("water layer: %d river reaches (Strahler>=%d), %d lakes", len(rivers), k, len(lakes))
    return dist / 1000.0


def build_stack(spec: GridSpec, country_arr: np.ndarray) -> tuple[dict[str, np.ndarray], dict]:
    """All raster covariates on the grid, plus a provenance/QA dict."""
    ISO = config.countries()
    stack: dict[str, np.ndarray] = {}
    qa: dict = {}
    wc = [str(_raw("worldclim", f"{c}_wc2.1_30s_bio.tif")) for c in ISO]
    for name, band in config.ml()["covariates"]["worldclim_bands"].items():
        stack[name] = _reproject(wc, int(band), spec, Resampling.average)
    stack["elevation_m"] = _reproject([str(_raw("worldclim", f"{c}_wc2.1_30s_elev.tif")) for c in ISO], 1,
                                      spec, Resampling.average)
    stack["ndvi_2020"] = _reproject([str(_raw("ndvi", "modis_ndvi_2020_median_0p05deg.tif"))], 1, spec,
                                    Resampling.bilinear)
    gz = _raw("ghsl", "GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V2_0.zip").as_posix()
    smod = _reproject([f"zip://{gz}!GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V2_0.tif"], 1, spec,
                      Resampling.mode)
    urban = np.full(spec.shape, np.nan, dtype="float32")
    for code, cls in SMOD_TO_URBAN.items():
        urban[smod == code] = cls
    stack["urban_class"] = urban
    pop, qa["population_conservation"] = population_to_grid(
        {c: str(_raw("worldpop", f"{c.lower()}_ppp_2020_1km_Aggregated_UNadj.tif")) for c in ISO},
        spec, country_arr)
    stack["pop_2020"] = pop.astype("float32")
    cell_km2 = (spec.res / 1000.0) ** 2
    stack["log_pop_density"] = np.log1p(pop / cell_km2).astype("float32")
    return stack, qa


def sample_stack(stack: dict[str, np.ndarray], spec: GridSpec, x, y) -> pd.DataFrame:
    """Covariate values of the grid cell containing each (x, y) in the grid CRS."""
    r, c = spec.rowcol(x, y)
    ok = spec.inside(r, c)
    out = {}
    for k, arr in stack.items():
        v = np.full(len(r), np.nan, dtype="float64")
        v[ok] = arr[r[ok], c[ok]]
        out[k] = v
    return pd.DataFrame(out)


def to_eqd(lon, lat) -> tuple[np.ndarray, np.ndarray]:
    return Transformer.from_crs("EPSG:4326", config.crs_distance(), always_xy=True).transform(
        np.asarray(lon, float), np.asarray(lat, float))


def to_area(lon, lat) -> tuple[np.ndarray, np.ndarray]:
    return Transformer.from_crs("EPSG:4326", config.crs_area(), always_xy=True).transform(
        np.asarray(lon, float), np.asarray(lat, float))
