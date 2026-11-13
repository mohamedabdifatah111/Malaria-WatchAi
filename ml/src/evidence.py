"""Evidence registry: every evidence_id used in an output resolves to a row here.

Dataset-level entries are built from data/manifest.csv (access date, licence,
URL). Record-level entries (MAP source, WHO study, Pf7 study, model) are built
from the outputs themselves. ``check_integrity`` fails the pipeline if any
output cites an id that is not in the registry.

Outputs: data/processed/evidence.parquet, evidence.json
"""
from __future__ import annotations

import logging

import geopandas as gpd
import pandas as pd

from ml.src import config, io

log = logging.getLogger("ml.evidence")

DATASETS = {
    "MAP-PR-SURVEYS": ("Malaria Atlas Project parasite rate surveys (202406)", ("map_pfpr_", "map_pvpr_"), "survey",
                       ["Only records released by MAP; ~2/3 of points withheld.", "Mixed ages and diagnostics."]),
    "WORLDCLIM-2.1": ("WorldClim 2.1 bioclim + elevation, 30 arc-s", ("worldclim_",), "covariate",
                      ["1970-2000 climatology, not 2020 weather."]),
    "MODIS-NDVI-2020": ("MODIS MOD13A1 NDVI 2020 annual median", ("modis_ndvi_2020",), "covariate",
                        ["Single year applied to surveys from all years."]),
    "WORLDPOP-2020": ("WorldPop 2020 UN-adjusted population, 1 km", ("worldpop_",), "population",
                      ["Modelled population, not a census count."]),
    "GHSL-SMOD-2020": ("GHSL SMOD 2020 degree of urbanisation (R2023A)", ("ghsl_smod_2020",), "covariate", []),
    "HYDRORIVERS-AF": ("HydroRIVERS v1.0 Africa", ("hydrorivers_af",), "covariate",
                       ["Strahler order >= 3 only; small streams and seasonal pools excluded."]),
    "NE-LAKES": ("Natural Earth 10 m lakes", ("naturalearth_lakes_10m",), "covariate", []),
    "GEOBOUNDARIES": ("geoBoundaries gbOpen ADM0-ADM2", ("geoboundaries_",), "boundary",
                      ["ADM1 and ADM2 layers do not always nest."]),
    "WHO-MTM": ("WHO Malaria Threats Map (TES + molecular markers)", ("who_mtm_",), "study_collection",
                ["Purposive study sites; not nationally representative."]),
    "PF7": ("MalariaGEN Pf7 open release", ("pf7_",), "genomic",
            ["Samples cluster in few sites and years; located to ADM1 centroid."]),
    "GBIF-PLASMODIUM": ("GBIF Plasmodium occurrence records", ("gbif_plasmodium_",), "presence_only",
                        ["Presence-only; cannot give prevalence or shares."]),
    "WHO-GHO": ("WHO Global Health Observatory malaria indicators", ("gho_malaria_",), "country_report",
                ["Routine reported cases depend on testing and reporting."]),
    "MIS-REPORTS": ("National Malaria Indicator Survey final reports (microscopy species tables, hand-entered)",
                    ("mis_microscopy_manual",), "survey_report",
                    ["National values transcribed from report tables; not applicable to districts."]),
    "WHO-REPORT-2020": ("WHO Report on antimalarial drug efficacy, resistance and response (2020)",
                        ("who_drug_efficacy_report_2020",), "report", []),
}


# DATA.md section 4: observed / modelled / synthetic (no synthetic data is used).
CLASSIFICATION = {
    "MAP-PR-SURVEYS": "observed", "WORLDCLIM-2.1": "modelled", "MODIS-NDVI-2020": "observed",
    "WORLDPOP-2020": "modelled", "GHSL-SMOD-2020": "modelled", "HYDRORIVERS-AF": "modelled",
    "NE-LAKES": "observed", "GEOBOUNDARIES": "observed", "WHO-MTM": "observed", "PF7": "observed",
    "GBIF-PLASMODIUM": "observed", "WHO-GHO": "observed", "MIS-REPORTS": "observed",
    "WHO-REPORT-2020": "observed",
}
CLASSIFICATION_NOTE = {
    "WORLDCLIM-2.1": "interpolated climatology from station data",
    "WORLDPOP-2020": "modelled population distribution, not a census count",
    "GHSL-SMOD-2020": "model-derived settlement classification",
    "HYDRORIVERS-AF": "river network derived from elevation models",
    "MODIS-NDVI-2020": "satellite measurement, aggregated (annual median)",
    "WHO-GHO": "routinely reported cases",
}


PROVIDERS = {
    "MAP-PR-SURVEYS": "Malaria Atlas Project", "WORLDCLIM-2.1": "WorldClim", "MODIS-NDVI-2020": "NASA (MODIS)",
    "WORLDPOP-2020": "WorldPop", "GHSL-SMOD-2020": "European Commission JRC (GHSL)",
    "HYDRORIVERS-AF": "HydroSHEDS", "NE-LAKES": "Natural Earth", "GEOBOUNDARIES": "geoBoundaries (William & Mary)",
    "WHO-MTM": "World Health Organization", "PF7": "MalariaGEN", "GBIF-PLASMODIUM": "GBIF",
    "WHO-GHO": "World Health Organization", "MIS-REPORTS": "National malaria programmes / DHS Program",
    "WHO-REPORT-2020": "World Health Organization",
}

# Backend EvidenceSource.evidence_type choices (backend/apps/evidence/models.py).
BACKEND_EVIDENCE_TYPE = {
    "survey": "survey", "survey_source": "survey", "survey_report": "survey", "national_survey_report": "survey",
    "therapeutic_efficacy_study": "survey", "marker_study": "survey", "study_collection": "survey",
    "model_output": "model_output", "report": "publication", "country_report": "other",
    "country_indicator": "other", "covariate": "other", "population": "other", "boundary": "other",
    "genomic": "survey", "presence_only": "other",
}

# Stable backend ids: the backend requires evidence ids of the form E001
# (EvidenceSource.evidence_id regex ^E\d{3,}$). ML ids are mapped once and the
# mapping is committed, so an id never changes between runs. ML ids start at
# E10001 to stay clear of hand-entered backend ids (E001...).
EVIDENCE_MAP_FILE = config.ML_ROOT / "config" / "evidence_id_map.json"
BACKEND_ID_START = 10001


def efficacy_pool_evidence_id() -> str:
    return f"ML-EFFICACY-POOL-{config.ml()['model_version']}"


def marker_trend_evidence_id() -> str:
    return f"ML-MARKER-TRENDS-{config.ml()['model_version']}"


def assign_backend_ids(ml_ids, path=None) -> dict:
    """Return {ml_id: 'E1xxxx'}, extending and saving the committed map for new ids."""
    import json

    path = path or EVIDENCE_MAP_FILE
    mapping = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    used = [int(v[1:]) for v in mapping.values()]
    nxt = max(used + [BACKEND_ID_START - 1]) + 1
    changed = False
    for mid in sorted(set(ml_ids)):
        if mid not in mapping:
            mapping[mid] = f"E{nxt}"
            nxt += 1
            changed = True
    if changed:
        path.write_text(json.dumps(dict(sorted(mapping.items())), indent=1) + "\n", encoding="utf-8")
    return mapping


def license_status(text) -> str:
    """DATA.md section 10: flag anything that is not clearly open for redistribution."""
    t = str(text or "").lower().replace("-", " ").replace("_", " ")
    if not t or "verify" in t:
        return "unverified - check before release"
    if "nc" in t.replace("-", " ").split() or "non-commercial" in t or "non commercial" in t             or "noncommercial" in t or "by-nc" in str(text).lower():
        return "restricted - non-commercial terms; check before redistribution"
    if "open database license" in t or "odbl" in t:
        return "open - attribution + share-alike (ODbL) for derived databases"
    if "per record" in t or "per report" in t or "per map record" in t or "permissions" in t:
        return "mixed - per-record terms; check before redistribution"
    return "open - attribution required"


def _manifest() -> pd.DataFrame:
    return pd.read_csv(config.manifest_path())


def dataset_rows() -> list[dict]:
    m = _manifest()
    rows = []
    for eid, (name, prefixes, etype, lims) in DATASETS.items():
        sub = m[m["source_id"].astype(str).str.startswith(prefixes)]
        rows.append({
            "evidence_id": eid, "source_name": name, "evidence_type": etype,
            "source_url": sub["url"].iloc[0] if len(sub) == 1 else (sub["url"].iloc[0] if len(sub) else None),
            "manifest_source_ids": sorted(sub["source_id"].astype(str)),
            "accessed_at": sub["accessed_utc"].max() if len(sub) else None,
            "license": "; ".join(sorted(set(sub["licence"].dropna().astype(str)))) or "VERIFY_LICENSE",
            "publication_year": None, "country": None, "citation": None, "limitations": lims,
            "status": "available" if len(sub) else "missing_from_manifest",
        })
    return rows


def record_rows() -> list[dict]:
    p = config.processed_dir()
    rows = []
    mv = config.ml()["model_version"]
    rows.append({"evidence_id": f"MODEL-PFPR-{mv}", "source_name": f"Malaria WatchAI PfPR model v{mv}",
                 "evidence_type": "model_output", "source_url": None,
                 "accessed_at": io.run_timestamp(), "license": "project output",
                 "citation": "See MODEL_CARD.md and data/processed/model_metadata.json",
                 "limitations": ["Model-based estimate, not an observed measurement.",
                                 "2020 values reflect latest survey years (KEN/TZA 2016)."]})
    rows.append({"evidence_id": efficacy_pool_evidence_id(),
                 "source_name": f"Malaria WatchAI random-effects pooling of WHO TES studies v{mv}",
                 "evidence_type": "model_output", "accessed_at": io.run_timestamp(), "license": "project output",
                 "citation": "ml/src/drug_efficacy/efficacy.py; study records cite WHO-MTM",
                 "limitations": ["Statistical pooling of purposive study sites; not a national survey."]})
    rows.append({"evidence_id": marker_trend_evidence_id(),
                 "source_name": f"Malaria WatchAI resistance-marker trend model v{mv}",
                 "evidence_type": "model_output", "accessed_at": io.run_timestamp(), "license": "project output",
                 "citation": "ml/src/resistance/trends.py; observations cite WHO-MTM and PF7",
                 "limitations": ["Binomial GLM did not beat simple baselines in validation; "
                                 "predictions are not recommended for decisions."]})
    s = pd.concat([gpd.read_parquet(p / f).drop(columns="geometry") for f in ("surveys.parquet", "surveys_pv.parquet")])
    src = s.dropna(subset=["source_id"]).groupby("source_id").agg(
        title=("source_title", "first"), citation=("citation", "first"), country=("country", "first"),
        y0=("year", "min")).reset_index()
    for _, r in src.iterrows():
        rows.append({"evidence_id": f"MAP-SRC-{int(r['source_id'])}", "source_name": r["title"] or "MAP source",
                     "evidence_type": "survey_source", "citation": r["citation"], "country": r["country"],
                     "publication_year": None, "parent_evidence_id": "MAP-PR-SURVEYS",
                     "license": "per MAP record permissions", "limitations": []})
    parents = (("PF7-", "PF7", "marker_study"), ("WHO-MTM-TES-", "WHO-MTM", "therapeutic_efficacy_study"),
               ("WHO-MTM-MM-", "WHO-MTM", "marker_study"), ("WHO-GHO-", "WHO-GHO", "country_indicator"),
               ("MIS-", "MIS-REPORTS", "national_survey_report"))
    seen = {r["evidence_id"] for r in rows}
    for f in ("efficacy_studies.parquet", "marker_observations.parquet", "species.parquet"):
        d = pd.read_parquet(p / f)
        ids = sorted({e for l in d["evidence_ids"] if l is not None for e in l} - set(DATASETS) - seen)
        for e in ids:
            par, kind = next(((pp, k) for pre, pp, k in parents if e.startswith(pre)), (None, "record"))
            if par is None:
                continue  # left for check_integrity to report
            rows.append({"evidence_id": e, "source_name": f"{par} record {e}", "evidence_type": kind,
                         "parent_evidence_id": par, "license": "see parent", "limitations": []})
            seen.add(e)
    return rows


def build() -> pd.DataFrame:
    reg = pd.DataFrame(dataset_rows() + record_rows()).drop_duplicates("evidence_id")
    for c in ("manifest_source_ids", "limitations"):
        reg[c] = reg[c].apply(lambda v: v if isinstance(v, list) else [])
    parent = reg.get("parent_evidence_id", pd.Series(None, index=reg.index))
    key = reg["evidence_id"].where(reg["evidence_id"].isin(CLASSIFICATION.keys()), parent)
    reg["data_classification"] = key.map(CLASSIFICATION)
    reg.loc[reg["evidence_id"].str.startswith("MODEL-"), "data_classification"] = "modelled"
    reg["classification_note"] = key.map(CLASSIFICATION_NOTE)
    lic = reg["license"].where(~reg["license"].isin(["see parent"]), parent.map(
        reg.set_index("evidence_id")["license"]))
    reg["license_status"] = lic.map(license_status)
    is_ml = reg["evidence_id"].str.startswith(("MODEL-", "ML-"))
    reg.loc[is_ml, "data_classification"] = "modelled"
    reg.loc[is_ml, "license_status"] = "project output"
    reg["provider"] = key.map(PROVIDERS)
    reg.loc[is_ml, "provider"] = "Malaria WatchAI ML pipeline"
    reg["provider"] = reg["provider"].fillna("Unknown - verify")
    reg["backend_evidence_type"] = reg["evidence_type"].map(BACKEND_EVIDENCE_TYPE).fillna("other")
    reg["backend_evidence_id"] = reg["evidence_id"].map(assign_backend_ids(reg["evidence_id"]))
    return reg


def check_integrity(registry: pd.DataFrame) -> dict:
    known = set(registry["evidence_id"])
    p = config.processed_dir()
    missing = {}
    for f in ("prevalence_district.parquet", "pop_at_risk.parquet", "species.parquet", "efficacy_studies.parquet",
              "efficacy_pooled.parquet", "marker_observations.parquet", "marker_trends.parquet",
              "survey_priority.parquet"):
        if not (p / f).exists():
            continue
        d = pd.read_parquet(p / f)
        used = {e for l in d["evidence_ids"] if l is not None for e in l}
        bad = sorted(used - known)
        if bad:
            missing[f] = bad[:20]
    return {"ok": not missing, "unknown_ids": missing}


def run() -> dict:
    reg = build()
    io.write_parquet(reg, "evidence.parquet")
    io.write_json({"evidence": reg.to_dict("records")}, "evidence.json")
    res = check_integrity(reg)
    if not res["ok"]:
        raise RuntimeError(f"evidence ids missing from registry: {res['unknown_ids']}")
    return {"entries": int(len(reg)), **res}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(run())
