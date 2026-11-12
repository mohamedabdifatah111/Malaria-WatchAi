"""Build model-ready feature tables.

Outputs
  data/interim/covariates_5km.npz        cached covariate stack + grid spec
  data/interim/survey_features.parquet    cleaned PfPR surveys + covariates
  data/processed/grid_2020.parquet        prediction grid + covariates (2020)

Run:  python -m ml.src.features.build [--refresh]
"""
from __future__ import annotations

import argparse
import json
import logging

import geopandas as gpd
import numpy as np
import pandas as pd
from affine import Affine

from ml.src import config, io
from ml.src.features import covariates as cov
from ml.src.features.grid import GridSpec, build_grid

log = logging.getLogger("ml.features")

STACK_FILE = "covariates_5km.npz"


def load_or_build_stack(refresh: bool = False):
    p = config.interim_dir() / STACK_FILE
    grid, spec = build_grid()
    if p.exists() and not refresh:
        z = np.load(p, allow_pickle=False)
        saved = json.loads(str(z["_spec"]))
        if saved == json.loads(json.dumps(spec.to_dict())):
            stack = {k: z[k] for k in z.files if not k.startswith("_")}
            qa = json.loads(str(z["_qa"]))
            log.info("loaded cached covariate stack %s", p.name)
            return grid, spec, stack, qa
        log.info("grid changed; rebuilding covariate stack")
    country_arr = np.full(spec.shape, "", dtype="<U3")
    country_arr[grid["row"].to_numpy(), grid["col"].to_numpy()] = grid["country"].to_numpy(dtype=str)
    stack, qa = cov.build_stack(spec, country_arr)
    np.savez_compressed(p, _spec=json.dumps(spec.to_dict()), _qa=json.dumps(qa), **stack)
    return grid, spec, stack, qa


def prediction_defaults() -> dict:
    s = config.ml()["surveys"]
    lo, hi = s["prediction_age"]
    return {"year": config.prediction_year(), "lower_age": float(lo), "upper_age": float(hi),
            "diag_rdt": 0.0 if s["prediction_method"] == "microscopy" else 1.0}


def survey_features(surveys: gpd.GeoDataFrame, spec: GridSpec, stack) -> pd.DataFrame:
    df = pd.DataFrame(surveys.drop(columns="geometry"))
    df["x"], df["y"] = cov.to_area(df["longitude"], df["latitude"])
    df["x_eqd"], df["y_eqd"] = cov.to_eqd(df["longitude"], df["latitude"])
    s = cov.sample_stack(stack, spec, df["x"], df["y"])
    s.index = df.index
    df = pd.concat([df, s], axis=1)
    df["dist_water_km"] = cov.distance_to_water_km(df["x_eqd"].to_numpy(), df["y_eqd"].to_numpy())
    return df


def grid_features(grid: pd.DataFrame, spec: GridSpec, stack) -> pd.DataFrame:
    df = grid.copy()
    for k, arr in stack.items():
        df[k] = arr[df["row"].to_numpy(), df["col"].to_numpy()]
    df["x_eqd"], df["y_eqd"] = cov.to_eqd(df["lon"], df["lat"])
    df["dist_water_km"] = cov.distance_to_water_km(df["x_eqd"].to_numpy(), df["y_eqd"].to_numpy())
    for k, v in prediction_defaults().items():
        df[k] = v
    return df


def run(refresh: bool = False) -> dict:
    grid, spec, stack, qa = load_or_build_stack(refresh)
    surveys = gpd.read_parquet(config.processed_dir() / "surveys.parquet")
    sf = survey_features(surveys, spec, stack)
    gf = grid_features(grid, spec, stack)
    feats = config.ml()["features"]
    qa["survey_feature_missing"] = {f: int(sf[f].isna().sum()) for f in feats}
    qa["grid_feature_missing"] = {f: int(gf[f].isna().sum()) for f in feats}
    qa["grid_cells"] = int(len(gf))
    qa["grid_population_total"] = float(gf["pop_2020"].sum())
    qa["grid_population_by_country"] = gf.groupby("country")["pop_2020"].sum().round(0).to_dict()
    qa["grid_spec"] = spec.to_dict()
    sf.to_parquet(config.interim_dir() / "survey_features.parquet", index=False)
    io.write_parquet(gf, "grid_2020.parquet", {
        "grid_crs": spec.crs, "cell_size_m": spec.res,
        "covariate_temporal_status": {
            "temp_mean_c": "climatology 1970-2000", "temp_seasonality": "climatology 1970-2000",
            "precip_annual_mm": "climatology 1970-2000", "precip_seasonality": "climatology 1970-2000",
            "elevation_m": "static", "ndvi_2020": "2020 annual median", "pop_2020": "2020",
            "urban_class": "2020", "dist_water_km": "static"},
        "prediction_defaults": prediction_defaults()})
    io.write_json(qa, "feature_qa.json", directory=config.outputs_dir())
    return qa


def load_spec() -> GridSpec:
    z = np.load(config.interim_dir() / STACK_FILE, allow_pickle=False)
    d = json.loads(str(z["_spec"]))
    return GridSpec(Affine(*d["transform"]), d["width"], d["height"], d["crs"], d["res"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="rebuild the cached covariate stack")
    qa = run(ap.parse_args().refresh)
    print(json.dumps({k: qa[k] for k in ("grid_cells", "grid_population_by_country",
                                         "population_conservation", "survey_feature_missing",
                                         "grid_feature_missing")}, indent=1, default=str))
