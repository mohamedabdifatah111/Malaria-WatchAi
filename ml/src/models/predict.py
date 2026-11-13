"""Fit the final model on all surveys and predict PfPR(2-10) for 2020.

Outputs (data/processed/)
  prevalence_grid.parquet          GeoParquet, 5 km cells (EPSG:4326 polygons)
  prevalence_district.parquet      modelled ADM0/ADM1/ADM2 rows + observed rows
  prevalence_uncertainty.parquet   uncertainty fields per modelled region (API 4.2)
  prevalence_adm1.geojson / prevalence_adm2.geojson   map display (EPSG:4326)
  model_metadata.json
ml/outputs/model_pfpr.joblib

Run:  python -m ml.src.models.predict   (after evaluate)
"""
from __future__ import annotations

import json
import logging

import geopandas as gpd
import joblib
import numpy as np
import pandas as pd

from ml.src import config, io
from ml.src.data import boundaries
from ml.src.features.build import load_spec, prediction_defaults
from ml.src.features.grid import cell_polygons
from ml.src.models import uncertainty
from ml.src.models.lgbm import LGBMPrevalence, feature_list
from ml.src.resistance.markers import wilson_ci

log = logging.getLogger("ml.predict")

DATASET_EVIDENCE = ["MAP-PR-SURVEYS", "WORLDCLIM-2.1", "MODIS-NDVI-2020", "WORLDPOP-2020",
                    "GHSL-SMOD-2020", "HYDRORIVERS-AF", "NE-LAKES", "GEOBOUNDARIES"]
ENV_FEATURES = ["temp_mean_c", "temp_seasonality", "precip_annual_mm", "precip_seasonality",
                "elevation_m", "ndvi_2020", "log_pop_density", "dist_water_km"]


def model_evidence_id() -> str:
    return f"MODEL-PFPR-{config.ml()['model_version']}"


def env_out_of_range(train: pd.DataFrame, target: pd.DataFrame) -> pd.Series:
    lo_q, hi_q = config.ml()["uncertainty"]["covariate_range_quantiles"]
    flag = pd.Series(False, index=target.index)
    for f in ENV_FEATURES:
        lo, hi = train[f].quantile([lo_q, hi_q])
        flag |= (target[f] < lo) | (target[f] > hi)
    return flag


def reliability(dist_km, extrap) -> np.ndarray:
    low = config.ml()["uncertainty"]["low_reliability_distance_km"]
    return np.where(extrap, "extrapolated", np.where(np.asarray(dist_km) > low, "low", "ok"))


def predict_grid(train: pd.DataFrame, grid: pd.DataFrame, bins: dict,
                 survey_bins: dict | None = None) -> tuple[pd.DataFrame, LGBMPrevalence]:
    ucfg = config.ml()["uncertainty"]
    model = LGBMPrevalence().fit(train)
    pl = model.predict_logit(grid)
    txy = train[["x_eqd", "y_eqd"]].to_numpy()
    gxy = grid[["x_eqd", "y_eqd"]].to_numpy()
    dist = uncertainty.nearest_distance_km(txy, gxy)
    lo, hi = uncertainty.intervals(pl, dist, bins)
    oor = env_out_of_range(train, grid).to_numpy()
    extrap = (dist > ucfg["extrapolation_distance_km"]) | oor
    out = grid[["cell_id", "country", "adm0_id", "adm1_id", "adm2_id", "lon", "lat", "x", "y",
                "pop_2020"]].copy()
    out["year"] = config.prediction_year()
    out["estimate"] = 1.0 / (1.0 + np.exp(-pl))
    out["lower_interval"] = lo
    out["upper_interval"] = hi
    out["interval_width"] = hi - lo
    if survey_bins is not None:
        out["survey_pi_lower"], out["survey_pi_upper"] = uncertainty.intervals(pl, dist, survey_bins)
    out["nearest_survey_distance_km"] = dist
    out["surveys_within_radius"] = uncertainty.count_within_km(txy, gxy, ucfg["density_radius_km"])
    out["covariates_outside_training_range"] = oor
    out["extrapolation_flag"] = extrap
    out["reliability_status"] = reliability(dist, extrap)
    return out, model


def _wmean(df, col, w="_w", by="_g"):
    return (df[col] * df[w]).groupby(df[by]).sum() / df[w].groupby(df[by]).sum()


def aggregate_regions(cells: pd.DataFrame, surveys: pd.DataFrame) -> pd.DataFrame:
    """Population-weighted means of cell predictions per ADM0/ADM1/ADM2."""
    ucfg = config.ml()["uncertainty"]
    regions = boundaries.region_table().set_index("region_id")
    frames = []
    for lvl, col in (("ADM0", "adm0_id"), ("ADM1", "adm1_id"), ("ADM2", "adm2_id")):
        d = cells[cells[col].notna()].copy()
        d["_g"] = d[col]
        tot = d.groupby("_g")["pop_2020"].transform("sum")
        d["_w"] = np.where(tot > 0, d["pop_2020"], 1.0)
        d["_x"] = d["extrapolation_flag"].astype(float)
        g = pd.DataFrame({
            "estimate": _wmean(d, "estimate"),
            # Conservative approximation: assumes cell errors fully correlated.
            "lower_interval": _wmean(d, "lower_interval"),
            "upper_interval": _wmean(d, "upper_interval"),
            "nearest_survey_distance_km": _wmean(d, "nearest_survey_distance_km"),
            "extrapolated_population_share": _wmean(d, "_x"),
            "population_2020": d.groupby("_g")["pop_2020"].sum(),
            "n_cells": d.groupby("_g").size(),
        })
        n_surv = surveys.groupby(col).size() if col != "adm0_id" else surveys.groupby("country").size()
        key = g.index if col != "adm0_id" else g.index.map(regions["country"])
        g["survey_density"] = pd.Series(key, index=g.index).map(n_surv).fillna(0).astype(int)
        g["admin_level"] = lvl
        g["aggregation_method"] = "population_weighted_mean_of_5km_cells"
        frames.append(g)
        # Regions smaller than a grid cell contain no cell centre: take the cell
        # nearest their representative point, and leave population unknown.
        polys = boundaries.level(lvl)
        missing = polys[~polys["region_id"].isin(g.index)]
        if len(missing):
            from scipy.spatial import cKDTree
            from ml.src.features.covariates import to_area
            rp = missing.representative_point()
            mx, my = to_area(rp.x, rp.y)
            _, idx = cKDTree(cells[["x", "y"]].to_numpy()).query(np.c_[mx, my])
            near = cells.iloc[idx]
            f = pd.DataFrame({
                "estimate": near["estimate"].to_numpy(),
                "lower_interval": near["lower_interval"].to_numpy(),
                "upper_interval": near["upper_interval"].to_numpy(),
                "nearest_survey_distance_km": near["nearest_survey_distance_km"].to_numpy(),
                "extrapolated_population_share": near["extrapolation_flag"].astype(float).to_numpy(),
                "population_2020": np.nan, "n_cells": 0,
                "survey_density": [int((surveys[col] == r).sum()) for r in missing["region_id"]],
                "admin_level": lvl,
                "aggregation_method": "nearest_5km_cell (region smaller than grid cell)",
            }, index=pd.Index(missing["region_id"].to_numpy()))
            frames.append(f)
            log.info("%s: %d regions smaller than a grid cell filled from nearest cell", lvl, len(missing))
    out = pd.concat(frames)
    out.index.name = "region_id"
    out = out.reset_index()
    out = out.join(regions[["country", "region_name", "parent_id"]], on="region_id")
    out["interval_width"] = out["upper_interval"] - out["lower_interval"]
    share = out["extrapolated_population_share"]
    out["extrapolation_flag"] = share > 0.5
    out["reliability_status"] = np.where(share > 0.5, "extrapolated",
                                         np.where((share > 0.2) | (out["nearest_survey_distance_km"]
                                                                   > ucfg["low_reliability_distance_km"]), "low", "ok"))
    out["status"] = np.where(out["extrapolation_flag"], "extrapolated", "ok")
    out["year"] = config.prediction_year()
    out["source_type"] = "modelled"
    out["data_classification"] = "modelled"
    out["indicator"] = "PfPR"
    out["age_band"] = "2-10"
    out["interval_level"] = 1 - ucfg["alpha"]
    out["model_version"] = config.ml()["model_version"]
    out["evidence_ids"] = [[model_evidence_id()] + DATASET_EVIDENCE for _ in range(len(out))]
    return out


def observed_regions(surveys: pd.DataFrame) -> pd.DataFrame:
    """Pooled observed survey prevalence per region and survey year (not age-standardised)."""
    regions = boundaries.region_table().set_index("region_id")
    adm0 = boundaries.level("ADM0").set_index("country")["region_id"]
    s = surveys.copy()
    s["adm0_id"] = s["country"].map(adm0)
    frames = []
    for lvl, col in (("ADM0", "adm0_id"), ("ADM1", "adm1_id"), ("ADM2", "adm2_id")):
        g = s[s[col].notna()].groupby([col, "year"]).agg(
            n_positive=("positive", "sum"), n_examined=("examined", "sum"), n_surveys=("survey_id", "size"),
            evidence_ids=("evidence_ids", lambda x: sorted({e for l in x for e in l})))
        g = g.reset_index().rename(columns={col: "region_id"})
        g["admin_level"] = lvl
        frames.append(g)
    o = pd.concat(frames, ignore_index=True)
    o["estimate"] = o["n_positive"] / o["n_examined"]
    ci = wilson_ci(o["n_positive"].round().to_numpy(), o["n_examined"].round().to_numpy())
    o["lower_interval"], o["upper_interval"] = ci
    o["interval_width"] = o["upper_interval"] - o["lower_interval"]
    o["interval_level"] = 0.95
    o = o.join(regions[["country", "region_name", "parent_id"]], on="region_id")
    o["source_type"] = "observed"
    o["data_classification"] = "observed"
    o["indicator"] = "PfPR"
    o["age_band"] = "as surveyed (mixed)"
    o["status"] = "ok"
    o["model_version"] = None
    o["evidence_ids"] = [["MAP-PR-SURVEYS"] + e for e in o["evidence_ids"]]
    return o


DISTRICT_COLUMNS = ["country", "region_id", "region_name", "admin_level", "parent_id", "year", "indicator",
                    "age_band", "source_type", "data_classification", "estimate", "lower_interval", "upper_interval",
                    "interval_width", "interval_level", "nearest_survey_distance_km", "survey_density",
                    "extrapolated_population_share", "extrapolation_flag", "reliability_status",
                    "population_2020", "n_surveys", "n_examined", "n_positive", "aggregation_method",
                    "status", "model_version", "evidence_ids"]


def run() -> dict:
    metrics = json.loads((config.processed_dir() / "metrics.json").read_text(encoding="utf-8"))
    u = metrics["uncertainty"]
    train = pd.read_parquet(config.interim_dir() / "survey_features.parquet")
    grid = pd.read_parquet(config.processed_dir() / "grid_2020.parquet")
    cells, model = predict_grid(train, grid, u["prevalence_interval"]["bins"],
                                u["survey_prediction_interval"]["bins"])
    joblib.dump(model, config.outputs_dir() / "model_pfpr.joblib")

    spec = load_spec()
    gcells = gpd.GeoDataFrame(cells.drop(columns=["x", "y"]).assign(
        feature_id=cells["cell_id"].astype(str),  # API 4.2 /prevalence/map/
        source_type="modelled", data_classification="modelled", indicator="PfPR", age_band="2-10",
        model_version=config.ml()["model_version"],
        evidence_ids=[[model_evidence_id()] + DATASET_EVIDENCE] * len(cells)),
        geometry=cell_polygons(cells, spec).values, crs="EPSG:4326")
    io.write_geoparquet(gcells, "prevalence_grid.parquet", {"units": {"estimate": "PfPR proportion 0-1"}})

    mod = aggregate_regions(cells, train)
    obs = observed_regions(train)
    district = pd.concat([mod, obs], ignore_index=True).reindex(columns=DISTRICT_COLUMNS)
    io.write_parquet(district, "prevalence_district.parquet",
                     {"units": {"estimate": "PfPR proportion 0-1", "population_2020": "persons"},
                      "notes": "modelled rows: population-weighted mean of 5 km cells, PfPR 2-10, "
                               "microscopy; observed rows: pooled survey prevalence, mixed ages/methods"})
    unc_cols = ["country", "region_id", "region_name", "admin_level", "year", "estimate", "lower_interval",
                "upper_interval", "interval_width", "interval_level", "nearest_survey_distance_km",
                "survey_density", "extrapolated_population_share", "extrapolation_flag",
                "reliability_status", "data_classification", "model_version", "evidence_ids"]
    io.write_parquet(mod[unc_cols], "prevalence_uncertainty.parquet",
                     {"method": metrics["uncertainty"]["method"],
                      "empirical_coverage": u["prevalence_interval"]["coverage"]})

    regions = boundaries.load_regions()
    for lvl in ("ADM1", "ADM2"):
        geo = regions[regions["admin_level"] == lvl][["region_id", "geometry"]].merge(
            mod[mod["admin_level"] == lvl].drop(columns=["evidence_ids"]), on="region_id")
        geo["geometry"] = geo.geometry.simplify(0.005, preserve_topology=True)
        geo["evidence_ids"] = ";".join([model_evidence_id()] + DATASET_EVIDENCE)
        geo.insert(0, "feature_id", geo["region_id"])  # API 4.2 /prevalence/map/
        geo["generated_at"] = io.run_timestamp()
        geo.to_file(config.processed_dir() / f"prevalence_{lvl.lower()}.geojson", driver="GeoJSON")

    latest = train.groupby("country")["year"].max().to_dict()
    meta = io.run_metadata({
        "model_type": "LightGBM gradient-boosted trees (regression on empirical logit)",
        "target": "PfPR in 2-10 year olds by microscopy, proportion 0-1",
        "features": feature_list(),
        "prediction_defaults": prediction_defaults(),
        "hyperparameters": model.params,
        "feature_importance_gain_share": model.importance(),
        "training_surveys": int(len(train)),
        "training_surveys_by_country": train.groupby("country").size().to_dict(),
        "latest_survey_year_by_country": latest,
        "temporal_extrapolation_note": (
            "Tree models cannot extrapolate a time trend: 2020 predictions reflect the latest survey "
            "years in each country (see latest_survey_year_by_country), not an observed 2020 level."),
        "evaluation_method": "spatial block 5-fold CV (primary), leave-one-ADM1-out, random 5-fold",
        "evaluation_summary": {s: v["models"]["lightgbm"]["overall"] for s, v in metrics["schemes"].items()},
        "uncertainty": metrics["uncertainty"]["method"],
        "uncertainty_coverage": u["prevalence_interval"]["coverage"],
        "evidence_id": model_evidence_id(),
        "source_data": DATASET_EVIDENCE,
    })
    io.write_json(meta, "model_metadata.json")
    return {"cells": len(cells), "regions": len(mod),
            "reliability": cells["reliability_status"].value_counts().to_dict()}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(run())
