"""Read-only lookups over the ML outputs, for the backend's agent tools.

The assistant must not compute scientific numbers itself: the backend wraps
these functions (or reads the same Parquet files) and passes the returned dicts
through. Every result carries value, unit, region, year, evidence ids, source,
sample size / study count, interval where applicable, data status and
limitations. Missing evidence returns status 'insufficient_data' - never a
filled-in value.

    from ml.src.lookup import prevalence_lookup
    prevalence_lookup("Kisumu")
"""
from __future__ import annotations

import math
from functools import lru_cache

import pandas as pd

from ml.src import config

COUNTRY_NAMES = {"KEN": ["kenya"], "TZA": ["tanzania", "united republic of tanzania"], "ETH": ["ethiopia"]}


@lru_cache(maxsize=None)
def _load(name: str) -> pd.DataFrame:
    return pd.read_parquet(config.processed_dir() / name)


def _clean(v):
    if v is None:
        return None
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if hasattr(v, "tolist"):
        return v.tolist()
    return v


def _records(df: pd.DataFrame) -> list[dict]:
    return [{k: _clean(v) for k, v in r.items()} for r in df.to_dict("records")]


def resolve_place(place: str) -> dict | None:
    """Match an ISO3 code, country name, or ADM1/ADM2 name (case-insensitive)."""
    q = place.strip().lower()
    for iso3, names in COUNTRY_NAMES.items():
        if q == iso3.lower() or q in names:
            d = _load("prevalence_district.parquet")
            r = d[(d["country"] == iso3) & (d["admin_level"] == "ADM0")].iloc[0]
            return {"country": iso3, "region_id": r["region_id"], "region_name": r["region_name"],
                    "admin_level": "ADM0"}
    d = _load("prevalence_district.parquet").drop_duplicates("region_id")
    hit = d[d["region_name"].str.lower() == q]
    if hit.empty:
        hit = d[d["region_name"].str.lower().str.startswith(q)]
    if hit.empty:
        return None
    hit = hit.sort_values("admin_level")  # prefer ADM1 over ADM2 on ties
    r = hit.iloc[0]
    out = {"country": r["country"], "region_id": r["region_id"], "region_name": r["region_name"],
           "admin_level": r["admin_level"]}
    if len(hit) > 1:
        out["ambiguous_matches"] = _records(hit[["region_id", "region_name", "admin_level", "country"]])
    return out


def _not_found(place):
    return {"status": "not_found", "place": place, "results": [],
            "limitations": ["Place not recognised; use a country, ADM1 or ADM2 name or region_id."]}


def prevalence_lookup(place: str, year: int = 2020) -> dict:
    loc = resolve_place(place)
    if not loc:
        return _not_found(place)
    d = _load("prevalence_district.parquet")
    m = d[(d["region_id"] == loc["region_id"]) & (d["source_type"] == "modelled") & (d["year"] == year)]
    o = d[(d["region_id"] == loc["region_id"]) & (d["source_type"] == "observed")].sort_values("year")
    res = []
    for _, r in m.iterrows():
        res.append({"value": r["estimate"], "unit": "PfPR 2-10, proportion", "lower": r["lower_interval"],
                    "upper": r["upper_interval"], "interval_level": r["interval_level"], "year": year,
                    "source_type": "modelled", "model_version": r["model_version"],
                    "reliability_status": r["reliability_status"],
                    "nearest_survey_distance_km": r["nearest_survey_distance_km"],
                    "evidence_ids": r["evidence_ids"], "data_status": r["status"]})
    obs = [{"value": r["estimate"], "unit": "pooled survey prevalence, proportion (mixed ages/methods)",
            "lower": r["lower_interval"], "upper": r["upper_interval"], "year": r["year"],
            "source_type": "observed", "n_surveys": r["n_surveys"], "n_examined": r["n_examined"],
            "evidence_ids": r["evidence_ids"]} for _, r in o.iterrows()]
    return {"status": "ok" if res else "insufficient_data", "place": loc,
            "results": [{k: _clean(v) for k, v in x.items()} for x in res],
            "observed_surveys": [{k: _clean(v) for k, v in x.items()} for x in obs],
            "limitations": ["Modelled values are estimates, not observed measurements.",
                            "Latest open surveys: Kenya/Tanzania 2016; 2020 values carry that forward.",
                            "Interval is a model-based 90% interval for true prevalence."]}


def population_at_risk(place: str, year: int = 2020) -> dict:
    loc = resolve_place(place)
    if not loc:
        return _not_found(place)
    p = _load("pop_at_risk.parquet")
    r = p[(p["region_id"] == loc["region_id"]) & (p["year"] == year)]
    cols = ["risk_class", "risk_class_label", "population", "population_if_lower_bound",
            "population_if_upper_bound", "share_of_region_population", "population_source",
            "prevalence_model_version", "evidence_ids"]
    return {"status": "ok" if len(r) else "insufficient_data", "place": loc, "unit": "persons",
            "results": _records(r[cols]),
            "limitations": ["Model-based estimate of people living in each PfPR class; not infections.",
                            "Lower/upper columns reclassify the same people using interval bounds."]}


def species_lookup(place: str) -> dict:
    loc = resolve_place(place)
    if not loc:
        return _not_found(place)
    s = _load("species.parquet")
    if loc["admin_level"] == "ADM0":
        r = s[s["country"] == loc["country"]]
    else:
        r = s[(s["region_id"] == loc["region_id"]) | ((s["country"] == loc["country"]) & s["region_id"].isna())]
    return {"status": "ok" if (r["status"] == "ok").any() else "insufficient_data", "place": loc,
            "results": _records(r),
            "limitations": ["Presence-only records never give case shares.",
                            "Country-level reports are not applied to districts."]}


def drug_evidence_lookup(place: str, drug: str = "AL") -> dict:
    loc = resolve_place(place)
    if not loc:
        return _not_found(place)
    pooled = _load("efficacy_pooled.parquet")
    studies = _load("efficacy_studies.parquet")
    pr = pooled[(pooled["country"] == loc["country"]) & (pooled["drug"] == drug)]
    st = studies[(studies["country"] == loc["country"]) & (studies["drug"] == drug)]
    if loc["admin_level"] == "ADM1":
        st = st[st["region_id"] == loc["region_id"]]
    elif loc["admin_level"] == "ADM2":
        st = st[st["adm2_id"] == loc["region_id"]]
    return {"status": "ok" if (pr["status"] == "ok").any() or len(st) else "insufficient_data",
            "place": loc, "drug": drug, "unit": "PCR-corrected ACPR, %",
            "pooled_country": _records(pr), "studies_in_place": _records(st),
            "limitations": ["Day-28 and day-42 results are separate and never pooled together.",
                            "WHO 10% failure threshold is a signal for policy review, not a recommendation.",
                            "Trial efficacy is not real-world effectiveness."]}


def resistance_lookup(place: str, marker: str | None = None, year: int | None = None) -> dict:
    loc = resolve_place(place)
    if not loc:
        return _not_found(place)
    o = _load("marker_observations.parquet")
    r = o[o["country"] == loc["country"]]
    if loc["admin_level"] == "ADM1":
        r = r[r["region_id"] == loc["region_id"]]
    if marker:
        r = r[r["marker"] == marker]
    if year:
        r = r[r["year"] == year]
    from ml.src.resistance.markers import wilson_ci
    summary = []
    for m, g in r.groupby("marker"):
        k, n = int(g["n_mutant"].sum()), int(g["n_tested"].sum())
        lo, hi = wilson_ci([k], [n])
        summary.append({"marker": m, "n_tested": n, "n_mutant": k, "pooled_frequency": k / n if n else None,
                        "confidence_interval_lower": float(lo[0]), "confidence_interval_upper": float(hi[0]),
                        "year_min": int(g["year"].min()), "year_max": int(g["year"].max()),
                        "n_study_years": int(len(g)), "sources": sorted(g["source"].unique()),
                        "evidence_ids": sorted({e for l in g["evidence_ids"] for e in l}),
                        "note": "Crude pooled across sites and years; sites are not representative."})
    return {"status": "ok" if len(r) else "insufficient_data", "place": loc, "unit": "proportion of samples",
            "summary": summary,
            "results": _records(r.sort_values(["marker", "year"])),
            "limitations": ["A resistance-marker frequency is not a treatment-failure rate.",
                            "Samples come from few sites; do not generalise one study to a country."]}
