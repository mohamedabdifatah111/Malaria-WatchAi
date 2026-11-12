"""Population at risk by PfPR class (model-based estimate, NOT infected people).

Each 5 km cell's WorldPop 2020 population is assigned to the risk class of the
cell's central PfPR estimate; the lower/upper-bound scenarios reclassify the
same population using the cell's interval bounds, to show how sensitive the
class totals are to model uncertainty.

Output: data/processed/pop_at_risk.parquet
Run:    python -m ml.src.models.pop_at_risk   (after predict)
"""
from __future__ import annotations

import logging

import geopandas as gpd
import pandas as pd

from ml.src import config, io
from ml.src.data import boundaries
from ml.src.evaluation.metrics import risk_class
from ml.src.models.predict import DATASET_EVIDENCE, model_evidence_id

log = logging.getLogger("ml.par")

POP_SOURCE = "WorldPop 2020 UN-adjusted 1 km (aggregated to 5 km cells)"


def classify(cells: pd.DataFrame) -> pd.DataFrame:
    c = cells.copy()
    c["rc_central"] = risk_class(c["estimate"])
    c["rc_lower"] = risk_class(c["lower_interval"])
    c["rc_upper"] = risk_class(c["upper_interval"])
    return c


def tabulate(cells: pd.DataFrame) -> pd.DataFrame:
    classes = config.ml()["risk_classes"]
    regions = boundaries.region_table().set_index("region_id")
    c = classify(cells)
    frames = []
    for lvl, col in (("ADM0", "adm0_id"), ("ADM1", "adm1_id"), ("ADM2", "adm2_id")):
        d = c[c[col].notna()]
        parts = {}
        for scen in ("central", "lower", "upper"):
            parts[scen] = d.groupby([col, f"rc_{scen}"])["pop_2020"].sum()
        ids = d[col].unique()
        idx = pd.MultiIndex.from_product([ids, [rc["key"] for rc in classes]], names=["region_id", "risk_class"])
        t = pd.DataFrame({f"population{'' if s == 'central' else '_if_' + s + '_bound'}":
                          p.rename_axis(["region_id", "risk_class"]).reindex(idx, fill_value=0.0)
                          for s, p in parts.items()}).reset_index()
        tot = d.groupby(col)["pop_2020"].sum()
        t["region_population_2020"] = t["region_id"].map(tot)
        t["admin_level"] = lvl
        frames.append(t)
    out = pd.concat(frames, ignore_index=True)
    out = out.join(regions[["country", "region_name", "parent_id"]], on="region_id")
    meta = {rc["key"]: rc for rc in classes}
    out["risk_class_label"] = out["risk_class"].map(lambda k: meta[k]["label"])
    out["pfpr_lower_bound"] = out["risk_class"].map(lambda k: meta[k]["lower"])
    out["pfpr_upper_bound"] = out["risk_class"].map(lambda k: min(meta[k]["upper"], 1.0))
    out["share_of_region_population"] = out["population"] / out["region_population_2020"]
    out["year"] = config.prediction_year()
    out["population_source"] = POP_SOURCE
    out["prevalence_model_version"] = config.ml()["model_version"]
    out["source_type"] = "modelled"
    out["uncertainty_status"] = "class totals under interval lower/upper bounds provided"
    out["evidence_ids"] = [[model_evidence_id()] + DATASET_EVIDENCE for _ in range(len(out))]
    out["note"] = "Model-based estimate of people living where modelled PfPR falls in this class; not infections."
    cols = ["country", "region_id", "region_name", "admin_level", "parent_id", "year", "risk_class",
            "risk_class_label", "pfpr_lower_bound", "pfpr_upper_bound", "population",
            "population_if_lower_bound", "population_if_upper_bound", "region_population_2020",
            "share_of_region_population", "population_source", "prevalence_model_version",
            "source_type", "uncertainty_status", "evidence_ids", "note"]
    return out[cols]


def run() -> pd.DataFrame:
    cells = gpd.read_parquet(config.processed_dir() / "prevalence_grid.parquet")
    par = tabulate(pd.DataFrame(cells.drop(columns="geometry")))
    io.write_parquet(par, "pop_at_risk.parquet", {"units": {"population": "persons"}})
    return par


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = run()
    print(p[p["admin_level"] == "ADM0"][["country", "risk_class", "population", "population_if_lower_bound",
                                         "population_if_upper_bound"]].to_string(index=False))
