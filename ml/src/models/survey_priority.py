"""Where to survey next: rank districts by how much one new survey would reduce
uncertainty for the people living there and nearby.

For every ADM2 district we place one hypothetical survey at the district's
population-weighted centre and recompute, for every 5 km cell, the distance to
the nearest survey. The cell's prevalence-interval half-width depends on that
distance through the calibrated distance bins (see uncertainty.py), so a new
survey narrows the interval of cells it brings into a closer distance band.

    uncertainty_burden      = sum over cells of population x interval width
    expected_reduction      = burden now - burden with the hypothetical survey
                              (summed over ALL cells, not just the district)

Districts are ranked by expected_reduction. This is a transparent planning aid,
not an optimal survey design: it uses only the model's distance-based
uncertainty, ignores logistics, cost, seasonality and existing programme data,
and evaluates one survey at a time.

Outputs: data/processed/survey_priority.parquet, survey_priority_adm2.geojson
Run:     python -m ml.src.models.survey_priority   (after predict)
"""
from __future__ import annotations

import json
import logging

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ml.src import config, io
from ml.src.data import boundaries
from ml.src.features.covariates import to_eqd
from ml.src.models import uncertainty
from ml.src.models.predict import DATASET_EVIDENCE, model_evidence_id

log = logging.getLogger("ml.priority")


def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def candidate_sites(cells: pd.DataFrame) -> pd.DataFrame:
    """Population-weighted centre of each ADM2 (cell centre nearest that point)."""
    d = cells[cells["adm2_id"].notna()].copy()
    d["_w"] = d["pop_2020"].where(d["pop_2020"] > 0, 0) + 1e-9
    g = d.groupby("adm2_id").apply(
        lambda x: pd.Series({"cx": np.average(x["x_eqd"], weights=x["_w"]),
                             "cy": np.average(x["y_eqd"], weights=x["_w"])}), include_groups=False)
    # snap to a real populated cell inside the district
    snapped = []
    for rid, r in g.iterrows():
        x = d[d["adm2_id"] == rid]
        i = np.argmin((x["x_eqd"] - r["cx"]) ** 2 + (x["y_eqd"] - r["cy"]) ** 2)
        snapped.append({"region_id": rid, "site_x_eqd": x["x_eqd"].iloc[i], "site_y_eqd": x["y_eqd"].iloc[i],
                        "site_lon": x["lon"].iloc[i], "site_lat": x["lat"].iloc[i]})
    return pd.DataFrame(snapped)


def expected_reductions(cells: pd.DataFrame, sites: pd.DataFrame, bins: dict) -> np.ndarray:
    pl = _logit(cells["estimate"])
    dist = cells["nearest_survey_distance_km"].to_numpy()
    pop = cells["pop_2020"].to_numpy()
    lo, hi = uncertainty.intervals(pl, dist, bins)
    width_now = hi - lo
    # a survey only matters for cells it brings into a closer band; beyond the
    # largest finite band edge nothing changes
    reach_km = max(bins["edges_km"]) + 1.0
    tree = cKDTree(cells[["x_eqd", "y_eqd"]].to_numpy() / 1000.0)
    out = np.zeros(len(sites))
    for k, s in enumerate(sites.itertuples()):
        idx = np.asarray(tree.query_ball_point([s.site_x_eqd / 1000.0, s.site_y_eqd / 1000.0], r=reach_km))
        if idx.size == 0:
            continue
        dnew = np.hypot(cells["x_eqd"].to_numpy()[idx] - s.site_x_eqd,
                        cells["y_eqd"].to_numpy()[idx] - s.site_y_eqd) / 1000.0
        dmin = np.minimum(dist[idx], dnew)
        lo2, hi2 = uncertainty.intervals(pl[idx], dmin, bins)
        out[k] = float(np.sum(pop[idx] * (width_now[idx] - (hi2 - lo2))))
    return out


def rank(cells: pd.DataFrame, surveys: pd.DataFrame, bins: dict) -> pd.DataFrame:
    regions = boundaries.region_table().set_index("region_id")
    d = cells[cells["adm2_id"].notna()].copy()
    d["_burden"] = d["pop_2020"] * d["interval_width"]
    d["_x"] = d["extrapolation_flag"].astype(float) * d["pop_2020"]
    agg = d.groupby("adm2_id").agg(population_2020=("pop_2020", "sum"), uncertainty_burden=("_burden", "sum"),
                                   extrapolated_population=("_x", "sum"),
                                   mean_estimate=("estimate", "mean"))
    agg["pop_weighted_interval_width"] = agg["uncertainty_burden"] / agg["population_2020"].replace(0, np.nan)
    sites = candidate_sites(cells)
    sites["expected_burden_reduction"] = expected_reductions(cells, sites, bins)
    out = agg.join(sites.set_index("region_id"), how="inner").reset_index().rename(columns={"adm2_id": "region_id"})
    s = surveys.groupby("adm2_id").agg(n_surveys=("survey_id", "size"), last_survey_year=("year", "max"))
    out = out.join(s, on="region_id")
    out["n_surveys"] = out["n_surveys"].fillna(0).astype(int)
    out["years_since_last_survey"] = config.prediction_year() - out["last_survey_year"]
    dist_now = d.groupby("adm2_id").apply(
        lambda x: np.average(x["nearest_survey_distance_km"], weights=x["pop_2020"] + 1e-9), include_groups=False)
    out["pop_weighted_distance_to_survey_km"] = out["region_id"].map(dist_now)
    out = out.join(regions[["country", "region_name", "parent_id"]], on="region_id")
    out["parent_name"] = out["parent_id"].map(regions["region_name"])
    out = out.sort_values("expected_burden_reduction", ascending=False).reset_index(drop=True)
    out["rank_overall"] = np.arange(1, len(out) + 1)
    out["rank_in_country"] = out.groupby("country")["expected_burden_reduction"].rank(
        ascending=False, method="first").astype(int)
    out["reason"] = out.apply(_reason, axis=1)
    out["year"] = config.prediction_year()
    out["model_version"] = config.ml()["model_version"]
    out["source_type"] = "modelled"
    out["data_classification"] = "modelled"
    out["evidence_ids"] = [[model_evidence_id()] + DATASET_EVIDENCE for _ in range(len(out))]
    out["note"] = ("Planning aid: ranks where one new survey would most reduce model uncertainty x people. "
                   "Ignores cost, access, seasonality and non-public programme data.")
    return out


def _reason(r) -> str:
    parts = [f"{r['population_2020'] / 1e6:.2f}M people" if r["population_2020"] >= 1e5
             else f"{r['population_2020']:,.0f} people",
             f"interval width {r['pop_weighted_interval_width']:.2f}",
             f"nearest survey {r['pop_weighted_distance_to_survey_km']:.0f} km (pop-weighted)"]
    if r["n_surveys"] == 0:
        parts.append("no open survey in district")
    else:
        parts.append(f"last open survey {int(r['last_survey_year'])}")
    if r["population_2020"] > 0 and r["extrapolated_population"] / r["population_2020"] > 0.5:
        parts.append("mostly extrapolated")
    return "; ".join(parts)


def run() -> pd.DataFrame:
    metrics = json.loads((config.processed_dir() / "metrics.json").read_text(encoding="utf-8"))
    bins = metrics["uncertainty"]["prevalence_interval"]["bins"]
    g = gpd.read_parquet(config.processed_dir() / "prevalence_grid.parquet")
    cells = pd.DataFrame(g.drop(columns="geometry"))
    cells["x_eqd"], cells["y_eqd"] = to_eqd(cells["lon"], cells["lat"])
    surveys = pd.read_parquet(config.interim_dir() / "survey_features.parquet")
    pr = rank(cells, surveys, bins)
    io.write_parquet(pr, "survey_priority.parquet",
                     {"units": {"uncertainty_burden": "person x PfPR interval width",
                                "expected_burden_reduction": "person x PfPR interval width"}})
    polys = boundaries.level("ADM2")[["region_id", "geometry"]]
    geo = polys.merge(pr.drop(columns=["evidence_ids"]), on="region_id")
    geo["geometry"] = geo.geometry.simplify(0.005, preserve_topology=True)
    geo.insert(0, "feature_id", geo["region_id"])
    geo["evidence_ids"] = ";".join([model_evidence_id()] + DATASET_EVIDENCE)
    geo["generated_at"] = io.run_timestamp()
    geo.to_file(config.processed_dir() / "survey_priority_adm2.geojson", driver="GeoJSON")
    return pr


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = run()
    with pd.option_context("display.width", 200, "display.max_colwidth", 120):
        print(p.groupby("country").head(5)[["rank_overall", "country", "region_name", "parent_name",
                                            "expected_burden_reduction", "reason"]].to_string(index=False))
