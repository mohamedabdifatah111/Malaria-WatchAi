"""Covariate rasters/vectors for the 5 km prediction grid.

| covariate          | source                                          | saved as                          |
|--------------------|-------------------------------------------------|-----------------------------------|
| rainfall, temp     | WorldClim 2.1 bioclim, 30 s country tiles       | worldclim/{ISO3}_wc2.1_30s_bio.tif (bio1 = mean temp, bio12 = annual precip) |
| elevation          | WorldClim 2.1 elevation (SRTM-based), 30 s      | worldclim/{ISO3}_wc2.1_30s_elev.tif |
| population         | WorldPop 2020 UN-adjusted, 1 km                 | worldpop/{iso3}_ppp_2020_1km_*.tif (counts), *_pd_* (density) |
| urban/rural        | GHSL SMOD 2020 (degree of urbanisation), 1 km   | ghsl/GHS_SMOD_E2020_...zip        |
| distance to water  | HydroRIVERS Africa + Natural Earth 10 m lakes   | hydro/ (HydroLAKES only with --full) |
| vegetation         | MODIS MOD13A1 NDVI 2020, Planetary Computer     | ndvi/modis_ndvi_2020_median_0p05deg.tif (computed composite) |
| Duffy negativity   | MAP 2011 Duffy-negativity phenotype frequency   | map/duffy_negativity_5k.tif (bbox clip via WCS) |

All rasters stay in their native CRS here; reprojection/resampling to the
5 km grid (ESRI:102022) happens in build.py.
"""
from __future__ import annotations

import logging

from mal.config import countries, load_config
from mal.fetch._common import download, is_cached, log, raw_dir, record_existing, rel

WORLDCLIM = "https://geodata.ucdavis.edu/climate/worldclim/2_1/tiles/iso/{iso3}_wc2.1_30s_{var}.tif"
WORLDCLIM_LIC = "WorldClim 2.1 - free for academic/non-commercial use; cite Fick & Hijmans 2017"

WORLDPOP = {
    "ppp": "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/{ISO3}/{iso3}_ppp_2020_1km_Aggregated_UNadj.tif",
    "pd": "https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km_UNadj/2020/{ISO3}/{iso3}_pd_2020_1km_UNadj.tif",
}
WORLDPOP_LIC = "CC BY 4.0 (WorldPop)"

GHSL_SMOD = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_SMOD_GLOBE_R2023A/"
             "GHS_SMOD_E2020_GLOBE_R2023A_54009_1000/V2-0/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V2_0.zip")
GHSL_LIC = "CC BY 4.0 (European Commission JRC, GHSL R2023A)"

HYDRO = {
    "hydrorivers_af": ("https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_af_shp.zip",
                       "HydroRIVERS_v10_af_shp.zip"),
    "naturalearth_lakes_10m": ("https://naciscdn.org/naturalearth/10m/physical/ne_10m_lakes.zip",
                               "ne_10m_lakes.zip"),
    "naturalearth_rivers_10m": ("https://naciscdn.org/naturalearth/10m/physical/ne_10m_rivers_lake_centerlines.zip",
                                "ne_10m_rivers_lake_centerlines.zip"),
}
HYDROLAKES = ("https://data.hydrosheds.org/file/hydrolakes/HydroLAKES_polys_v10_shp.zip",
              "HydroLAKES_polys_v10_shp.zip")
HYDRO_LIC = {
    "hydrorivers_af": "HydroSHEDS licence (free, attribution required)",
    "hydrolakes": "HydroSHEDS licence (free, attribution required)",
    "naturalearth_lakes_10m": "Public domain (Natural Earth)",
    "naturalearth_rivers_10m": "Public domain (Natural Earth)",
}

DUFFY_WCS = "https://data.malariaatlas.org/geoserver/ows"
DUFFY_ID = "Explorer__2011_Duffy_Negativity_Phenotype_Frequency_5k_Decompressed"
MAP_LIC = "CC BY 4.0 (Malaria Atlas Project); cite Howes et al. 2011"

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
NDVI_COLLECTION = "modis-13A1-061"
NDVI_LIC = "NASA EOSDIS open data (no restrictions); via Microsoft Planetary Computer"


def fetch_worldclim(force: bool) -> None:
    out = raw_dir("worldclim")
    for iso3 in countries():
        for var in ("bio", "elev"):
            url = WORLDCLIM.format(iso3=iso3, var=var)
            download(url, out / f"{iso3}_wc2.1_30s_{var}.tif",
                     f"worldclim_{var}_{iso3}".lower(), WORLDCLIM_LIC, force=force)


def fetch_worldpop(force: bool) -> None:
    out = raw_dir("worldpop")
    for iso3 in countries():
        for kind, tpl in WORLDPOP.items():
            url = tpl.format(ISO3=iso3, iso3=iso3.lower())
            download(url, out / url.rsplit("/", 1)[1],
                     f"worldpop_{kind}_2020_{iso3}".lower(), WORLDPOP_LIC, force=force)


def fetch_ghsl(force: bool) -> None:
    download(GHSL_SMOD, raw_dir("ghsl") / GHSL_SMOD.rsplit("/", 1)[1],
             "ghsl_smod_2020", GHSL_LIC, force=force)


def fetch_hydro(force: bool, full: bool) -> None:
    out = raw_dir("hydro")
    for sid, (url, name) in HYDRO.items():
        download(url, out / name, sid, HYDRO_LIC[sid], force=force)
    if full or load_config()["fetch"].get("hydrolakes"):
        download(HYDROLAKES[0], out / HYDROLAKES[1], "hydrolakes",
                 HYDRO_LIC["hydrolakes"], force=force)
    else:
        log.info("skip    hydrolakes (820 MB) - using Natural Earth lakes; pass --full to fetch")


def fetch_duffy(force: bool) -> None:
    lon0, lat0, lon1, lat1 = load_config()["bbox"]
    params = {
        "service": "WCS", "version": "2.0.1", "request": "GetCoverage",
        "coverageId": DUFFY_ID, "format": "image/geotiff",
        "subset": [f"Long({lon0},{lon1})", f"Lat({lat0},{lat1})"],
    }
    download(DUFFY_WCS, raw_dir("map") / "duffy_negativity_5k.tif",
             "map_duffy_negativity", MAP_LIC, force=force, params=params)


def fetch_ndvi(force: bool) -> None:
    """Annual 2020 NDVI: median of Terra MOD13A1 16-day composites at 0.05 deg.

    Reads COG overviews only, so the whole 4-country box is a few MB of
    traffic per date instead of full 500 m tiles.
    """
    dest = raw_dir("ndvi") / "modis_ndvi_2020_median_0p05deg.tif"
    sid = "modis_ndvi_2020"
    if not force and is_cached(sid, dest):
        log.info("cached  %-40s %s", sid, rel(dest))
        return

    import numpy as np
    import odc.stac
    import planetary_computer as pc
    import pystac_client
    import rasterio
    from rasterio.transform import from_origin

    year = load_config()["prediction_year"]
    bbox = load_config()["bbox"]
    cat = pystac_client.Client.open(STAC, modifier=pc.sign_inplace)
    items = [it for it in cat.search(collections=[NDVI_COLLECTION], bbox=bbox,
                                     datetime=f"{year}-01-01/{year}-12-31").items()
             if it.id.startswith("MOD13A1")]  # Terra only; Aqua duplicates dates
    log.info("ndvi    %d Terra MOD13A1 items for %s", len(items), year)
    logging.getLogger("rasterio").setLevel(logging.ERROR)
    ds = odc.stac.load(items, bands=["500m_16_days_NDVI"], bbox=bbox,
                       crs="EPSG:4326", resolution=0.05, groupby="solar_day",
                       resampling="average", nodata=-3000, dtype="int16")
    arr = ds["500m_16_days_NDVI"].values.astype("float32")
    # MOD13A1 valid range is -2000..10000 (fill = -3000). The Planetary Computer
    # COG overviews carry ~0.1-0.5% int16-overflow pixels (+-32768); drop them
    # per date so the annual median stays clean. Checked against full-res
    # block means: overview error elsewhere is ~0.006 NDVI.
    arr[(arr < -2000) | (arr > 10000)] = np.nan
    med = np.nanmedian(arr, axis=0) * 0.0001  # MODIS scale factor
    med = np.where(np.isfinite(med), med, -9999).astype("float32")

    xs, ys = ds.longitude.values, ds.latitude.values
    res = float(abs(xs[1] - xs[0]))
    transform = from_origin(float(xs.min()) - res / 2, float(ys.max()) + res / 2, res, res)
    with rasterio.open(dest, "w", driver="GTiff", height=med.shape[0], width=med.shape[1],
                       count=1, dtype="float32", crs="EPSG:4326", transform=transform,
                       nodata=-9999, compress="deflate") as dst:
        dst.write(med, 1)
        dst.update_tags(source=f"{NDVI_COLLECTION} {year}, {ds.sizes['time']} dates, median",
                        items=",".join(sorted(i.id for i in items)))
    record_existing(dest, sid,
                    f"{STAC}/collections/{NDVI_COLLECTION} (bbox={bbox}, {year}, Terra, median)",
                    NDVI_LIC, None)
    log.info("saved   %-40s %s (%d dates)", sid, rel(dest), ds.sizes["time"])


def run(force: bool = False, full: bool = False) -> None:
    fetch_worldclim(force)
    fetch_worldpop(force)
    fetch_ghsl(force)
    fetch_hydro(force, full)
    fetch_duffy(force)
    fetch_ndvi(force)
