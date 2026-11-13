"""Antimalarial therapeutic efficacy from WHO Malaria Threats Map TES records.

Uses P. falciparum therapeutic efficacy studies (DimensionID 256) with a known
follow-up (28 or 42 days), a patient count and a reported treatment-failure
proportion. Day-28 and day-42 studies are never pooled together.

Assumption to verify: TREATMENT_FAILURE_PP is the per-protocol treatment
failure proportion as published by the Threats Map, which reports PCR-corrected
outcomes for P. falciparum TES. Failure counts are reconstructed as
round(proportion x N) because the API gives N and a proportion, not counts.

Outputs: data/processed/efficacy_studies.parquet, efficacy_pooled.parquet
"""
from __future__ import annotations

import json
import logging

import geopandas as gpd
import numpy as np
import pandas as pd

from ml.src import config, io
from ml.src.data import boundaries
from ml.src.drug_efficacy.meta import dersimonian_laird, inv_logit, logit_transform
from ml.src.resistance.markers import _country_from_name, wilson_ci

log = logging.getLogger("ml.efficacy")

LIMITS = ["Trial efficacy under supervised dosing is not real-world effectiveness.",
          "Failure counts reconstructed from reported proportion x N.",
          "Study sites are purposively selected; pooled values describe these sites, not every district."]


def load_tes() -> tuple[pd.DataFrame, dict]:
    raw = config.raw_dir() / "who_mtm" / "FACT_TREATMENT_VIEW.json"
    t = pd.DataFrame(json.loads(raw.read_text(encoding="utf-8")))
    t["country"] = t["COUNTRY_NAME"].map(_country_from_name)
    tes = t[(t["DimensionID"] == 256) & t["country"].notna() & (t["PLASMODIUM_SPECIES"] == "P._FALCIPARUM")]
    code_to_drug = {code: drug for drug, codes in config.ml()["efficacy"]["drugs"].items() for code in codes}
    tes = tes.assign(drug=tes["DRUG_NAME"].map(code_to_drug))
    tes = tes[tes["drug"].notna()].copy()
    qa = {"tes_rows_in_scope": int(len(tes))}
    excl = {
        "followup_missing": tes["FOLLOW_UP"].isna(),
        "n_missing": tes["N"].isna() | (tes["N"] <= 0),
        "failure_missing": tes["TREATMENT_FAILURE_PP"].isna(),
    }
    reason = pd.Series(None, index=tes.index, dtype=object)
    for k, m in excl.items():
        reason[m & reason.isna()] = k
    tes["exclusion_reason"] = reason
    qa["excluded"] = reason.value_counts().to_dict()
    return tes, qa


def study_table(tes: pd.DataFrame) -> pd.DataFrame:
    s = tes.copy()
    pts = gpd.GeoDataFrame(s, geometry=gpd.points_from_xy(s["Longitude"], s["Latitude"]), crs="EPSG:4326")
    reg = boundaries.assign_regions(pts, buffer_km=10)
    s["region_id"] = reg["adm1_id"].values
    s["adm2_id"] = reg["adm2_id"].values
    n = s["N"].astype(float)
    p = s["TREATMENT_FAILURE_PP"].astype(float)
    fails = np.round(p * n)
    lo, hi = wilson_ci(fails, n)
    out = pd.DataFrame({
        "record_type": "study",
        "study_id": "WHO-MTM-TES-" + s["Code"].astype(str),
        "country": s["country"], "region_id": s["region_id"], "adm2_id": s["adm2_id"],
        "site_name": s["SITE_NAME"], "drug": s["drug"],
        "followup_days": pd.to_numeric(s["FOLLOW_UP"], errors="coerce").astype("Int64"),
        "year_start": s["YEAR_START"], "year_end": s["YEAR_END"],
        "n_patients": n, "n_failures": fails,
        "failure_percent": 100 * p, "acpr_percent": 100 * (1 - p),
        "confidence_interval_lower": 100 * (1 - hi), "confidence_interval_upper": 100 * (1 - lo),
        "source_id": "WHO-MTM-TES-" + s["Code"].astype(str),
        "exclusion_reason": s["exclusion_reason"],
    })
    out["status"] = np.where(out["exclusion_reason"].isna(), "ok", "excluded_from_pooling")
    # Same shape as pooled rows (API 4.5): pooled-only statistics are null for a single study.
    out["study_count"] = 1
    out["year_range"] = s["YEAR_START"].astype("Int64").astype(str) + "-" + s["YEAR_END"].astype("Int64").astype(str)
    for c in ("prediction_interval_lower", "prediction_interval_upper", "heterogeneity_i2"):
        out[c] = np.nan
    out["evidence_ids"] = [["WHO-MTM", sid] for sid in out["study_id"]]
    out["data_classification"] = "observed"
    return out


def pool(studies: pd.DataFrame) -> pd.DataFrame:
    cfg = config.ml()["efficacy"]
    thr = cfg["who_failure_threshold"]
    rows = []
    ok = studies[studies["status"] == "ok"]
    for c in config.countries():
        for drug in cfg["drugs"]:
            for fu in cfg["followup_days"]:
                g = ok[(ok["country"] == c) & (ok["drug"] == drug) & (ok["followup_days"] == fu)]
                base = {"record_type": "pooled", "study_id": f"POOLED-{c}-{drug}-D{fu}",
                        "country": c, "region_id": None, "drug": drug,
                        "followup_days": fu, "study_count": int(len(g)),
                        "n_patients": float(g["n_patients"].sum()) if len(g) else 0.0,
                        "year_range": f"{int(g['year_start'].min())}-{int(g['year_end'].max())}" if len(g) else None,
                        "n_sites": int(g["site_name"].nunique()), "n_adm1": int(g["region_id"].nunique()),
                        "source_id": "WHO-MTM",
                        "evidence_ids": ["WHO-MTM"] + sorted(g["study_id"].tolist())}
                if len(g) < cfg["min_studies_for_pooling"]:
                    rows.append({**base, "status": "insufficient_data",
                                 "method": f"not pooled (< {cfg['min_studies_for_pooling']} studies)"})
                    continue
                y, v = logit_transform(g["n_failures"], g["n_patients"])
                m = dersimonian_laird(y, v)
                f = inv_logit(m["mu"])
                flo, fhi = inv_logit(m["ci"][0]), inv_logit(m["ci"][1])
                plo, phi = (inv_logit(m["pi"][0]), inv_logit(m["pi"][1])) if m["pi"][0] is not None else (None, None)
                crude = float(g["n_failures"].sum() / g["n_patients"].sum())
                rows.append({**base, "status": "ok",
                             "method": "DerSimonian-Laird random effects, logit, 0.5 continuity correction",
                             "failure_percent": 100 * f, "acpr_percent": 100 * (1 - f),
                             "confidence_interval_lower": 100 * (1 - fhi), "confidence_interval_upper": 100 * (1 - flo),
                             "failure_ci_lower": 100 * flo, "failure_ci_upper": 100 * fhi,
                             "prediction_interval_lower": None if phi is None else 100 * (1 - phi),
                             "prediction_interval_upper": None if plo is None else 100 * (1 - plo),
                             "heterogeneity_i2": 100 * m["i2"], "tau2": m["tau2"], "cochran_q": m["q"],
                             "crude_pooled_failure_percent": 100 * crude,
                             "policy_review_signal": bool(f >= thr),
                             "policy_review_note": ("WHO 10% treatment-failure threshold is a signal for policy "
                                                    "review, not a treatment recommendation.")})
    p = pd.DataFrame(rows)
    p["data_classification"] = "modelled"  # statistical (meta-analysis) estimate
    p["geographic_note"] = np.where(p["n_adm1"] <= 2, "concentrated in <=2 ADM1 regions; not a national "
                                    "estimate without qualification", "multiple regions")
    return p


def run() -> dict:
    tes, qa = load_tes()
    studies = study_table(tes)
    studies["limitations"] = [LIMITS] * len(studies)
    pooled = pool(studies)
    pooled["limitations"] = [LIMITS] * len(pooled)
    io.write_parquet(studies, "efficacy_studies.parquet", {"units": {"acpr_percent": "%"}})
    io.write_parquet(pooled, "efficacy_pooled.parquet", {"units": {"acpr_percent": "%"}})
    qa["pooled"] = pooled[["country", "drug", "followup_days", "study_count", "status"]].to_dict("records")
    return qa


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
    p = pd.read_parquet(config.processed_dir() / "efficacy_pooled.parquet")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(p[["country", "drug", "followup_days", "study_count", "n_patients", "year_range", "acpr_percent",
                 "confidence_interval_lower", "confidence_interval_upper", "heterogeneity_i2", "status"]])
