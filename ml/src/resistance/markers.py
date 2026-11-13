"""Resistance-marker observations from WHO Malaria Threats Map and MalariaGEN Pf7.

Markers
  pfk13_validated   any WHO-validated pfkelch13 mutation (config list, WHO 2020 Table 4)
  pfk13_candidate   any candidate/associated pfkelch13 mutation (reported separately)
  pfcrt_K76T        pfcrt K76T (mixed K/T infections counted as carrying the mutant)
  pfmdr1_CNV        pfmdr1 copy-number amplification

A marker frequency is the proportion of tested samples carrying the marker.
It is NOT a treatment-failure rate.

Output: data/processed/marker_observations.parquet  (API 4.6 /resistance/)
"""
from __future__ import annotations

import json
import logging
import re

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import norm

from ml.src import config
from ml.src.data import boundaries

log = logging.getLogger("ml.markers")

MARKERS = {
    "pfk13_validated": "pfkelch13 WHO-validated mutation (any)",
    "pfk13_candidate": "pfkelch13 candidate/associated mutation (any)",
    "pfcrt_K76T": "pfcrt K76T",
    "pfmdr1_CNV": "pfmdr1 copy-number amplification",
}


def wilson_ci(k, n, level: float = 0.95) -> tuple[np.ndarray, np.ndarray]:
    k = np.asarray(k, float)
    n = np.asarray(n, float)
    z = norm.ppf(0.5 + level / 2)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = k / n
        den = 1 + z ** 2 / n
        centre = (p + z ** 2 / (2 * n)) / den
        half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
        lo = np.where(n > 0, np.clip(centre - half, 0, 1), np.nan)
        hi = np.where(n > 0, np.clip(centre + half, 0, 1), np.nan)
    return lo, hi


_MUT = re.compile(r"([A-Z])(\d+)([A-Z])")


def k13_mutations(text) -> set[str]:
    """Parse genotype strings such as 'R539T/C580Y', 'Y493H&C580Y', 'a578s,v445i*'."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return set()
    return {"".join(m) for m in _MUT.findall(str(text).upper())}


def classify_k13(text) -> tuple[bool, bool]:
    r = config.ml()["resistance"]
    muts = k13_mutations(text)
    return bool(muts & set(r["k13_validated"])), bool(muts & set(r["k13_candidate"]))


def _country_from_name(name: str) -> str | None:
    for iso3, aliases in config.ml()["country_aliases"].items():
        if name in aliases:
            return iso3
    return None


# ----------------------------------------------------------------------------- Pf7
def pf7_samples() -> pd.DataFrame:
    raw = config.raw_dir() / "pf7"
    s = pd.read_csv(raw / "Pf7_samples.txt", sep="\t")
    g = pd.read_csv(raw / "Pf7_drug_resistance_marker_genotypes.txt", sep="\t", dtype=str)
    g = g.rename(columns={g.columns[0]: "Sample"})
    s["country"] = s["Country"].map(_country_from_name)
    s = s[s["country"].notna() & (s["QC pass"] == True) & s["Year"].notna()]  # noqa: E712
    return s.merge(g, on="Sample", how="inner")


def pf7_marker_calls(df: pd.DataFrame) -> pd.DataFrame:
    """Long table: one row per sample x marker with carries in {0,1}; untyped rows dropped."""
    rows = []
    k13 = df["kelch13_349-726_ns_changes"]
    # NaN = no non-synonymous change (wild type); '-' = missing call; '*' alone = undetermined
    k13_typed = k13.isna() | ~k13.astype(str).str.strip().isin(["-", "*", ""])
    cls = k13.where(k13_typed).map(lambda t: classify_k13(t) if isinstance(t, str) else (False, False))
    for marker, idx in (("pfk13_validated", 0), ("pfk13_candidate", 1)):
        rows.append(pd.DataFrame({"Sample": df.loc[k13_typed, "Sample"], "marker": marker,
                                  "carries": cls[k13_typed].map(lambda t: int(t[idx]))}))
    crt = df["crt_76[K]"].astype(str).str.upper()
    crt_typed = crt.str.fullmatch(r"[KT](,[KT])*")
    rows.append(pd.DataFrame({"Sample": df.loc[crt_typed, "Sample"], "marker": "pfcrt_K76T",
                              "carries": crt[crt_typed].str.contains("T").astype(int)}))
    mdr = pd.to_numeric(df["mdr1_dup_call"], errors="coerce")
    mdr_typed = mdr.isin([0, 1])
    rows.append(pd.DataFrame({"Sample": df.loc[mdr_typed, "Sample"], "marker": "pfmdr1_CNV",
                              "carries": mdr[mdr_typed].astype(int)}))
    long = pd.concat(rows, ignore_index=True)
    return long.merge(df[["Sample", "Study", "country", "Admin level 1", "Admin level 1 latitude",
                          "Admin level 1 longitude", "Year"]], on="Sample")


def pf7_observations() -> pd.DataFrame:
    df = pf7_samples()
    calls = pf7_marker_calls(df)
    sites = calls.drop_duplicates(["country", "Admin level 1"]).copy()
    pts = gpd.GeoDataFrame(sites, geometry=gpd.points_from_xy(sites["Admin level 1 longitude"],
                                                              sites["Admin level 1 latitude"]), crs="EPSG:4326")
    reg = boundaries.assign_regions(pts, buffer_km=25)
    sites["region_id"] = reg["adm1_id"].values
    calls = calls.merge(sites[["country", "Admin level 1", "region_id"]], on=["country", "Admin level 1"])
    g = calls.groupby(["country", "region_id", "Admin level 1", "marker", "Year", "Study"]).agg(
        n_tested=("carries", "size"), n_mutant=("carries", "sum")).reset_index()
    return pd.DataFrame({
        "country": g["country"], "region_id": g["region_id"], "admin_level": "ADM1",
        "site_name": g["Admin level 1"], "marker": g["marker"], "year": g["Year"].astype(int),
        "n_tested": g["n_tested"].astype(int), "n_mutant": g["n_mutant"].astype(int),
        "source": "MalariaGEN Pf7", "source_id": "PF7-" + g["Study"],
        "evidence_ids": [["PF7", f"PF7-{s}"] for s in g["Study"]],
        "location_precision": "admin1 centroid",
    })


# ------------------------------------------------------------------- WHO Threats Map
def who_mtm_observations() -> tuple[pd.DataFrame, dict]:
    raw = config.raw_dir() / "who_mtm"
    mm = pd.DataFrame(json.loads((raw / "FACT_AMDER_MM_VIEW.json").read_text(encoding="utf-8")))
    geno = pd.DataFrame(json.loads((raw / "FACT_AMDER_GENO_VIEW.json").read_text(encoding="utf-8")))
    mm["country"] = mm["COUNTRY_NAME"].map(_country_from_name)
    mm = mm[mm["country"].notna() & (mm["PLASMODIUM_SPECIES"] == "P._FALCIPARUM")]
    # Only rows whose genotypes are pfkelch13 alleles are usable here.
    k13_rows = mm[mm["MM_TYPE"].isin(["1", "3"])].copy()
    has_geno = k13_rows["Code"].isin(geno["CODE"])
    qa = {"who_mtm_k13_studies_in_scope": int(len(k13_rows)),
          "who_mtm_k13_studies_without_genotype_detail": int((~has_geno).sum()),
          "note": "studies without genotype rows are excluded: absence of a genotype row is not "
                  "evidence of zero mutants"}
    k13_rows = k13_rows[has_geno & k13_rows["N"].notna() & (k13_rows["N"] > 0)]
    out = []
    for _, r in k13_rows.iterrows():
        g = geno[geno["CODE"] == r["Code"]]
        flags = g["GENOTYPE"].map(classify_k13)
        n = int(r["N"])
        for marker, idx in (("pfk13_validated", 0), ("pfk13_candidate", 1)):
            prop = float(g.loc[flags.map(lambda t: t[idx]), "PROPORTION"].fillna(0).sum())
            prop = min(prop, 1.0)
            out.append({"country": r["country"], "site_name": r["SITE_NAME"], "marker": marker,
                        "year": int(r["YEAR_START"]), "n_tested": n, "n_mutant": int(round(prop * n)),
                        "lon": r["Longitude"], "lat": r["Latitude"],
                        "source": "WHO Malaria Threats Map", "source_id": f"WHO-MTM-MM-{r['Code']}",
                        "citation_url": r.get("CITATION_URL")})
    o = pd.DataFrame(out)
    if o.empty:
        return o, qa
    pts = gpd.GeoDataFrame(o, geometry=gpd.points_from_xy(o["lon"], o["lat"]), crs="EPSG:4326")
    reg = boundaries.assign_regions(pts, buffer_km=10)
    o["region_id"] = reg["adm1_id"].values
    o["admin_level"] = "ADM1"
    o["evidence_ids"] = [["WHO-MTM", s] for s in o["source_id"]]
    o["location_precision"] = "study site"
    return o.drop(columns=["lon", "lat", "citation_url"]), qa


def observations() -> tuple[pd.DataFrame, dict]:
    who, qa = who_mtm_observations()
    pf7 = pf7_observations()
    obs = pd.concat([who, pf7], ignore_index=True)
    obs["frequency"] = obs["n_mutant"] / obs["n_tested"]
    obs["confidence_interval_lower"], obs["confidence_interval_upper"] = wilson_ci(obs["n_mutant"], obs["n_tested"])
    obs["marker_label"] = obs["marker"].map(MARKERS)
    obs["data_status"] = "observed"
    obs["data_classification"] = "observed"
    qa["rows_by_source_marker"] = obs.groupby(["source", "marker"]).size().to_dict()
    qa["rows_by_source_marker"] = {f"{a}|{b}": int(v) for (a, b), v in qa["rows_by_source_marker"].items()}
    return obs, qa


def check_marker_list_against_report() -> dict:
    """Confirm every configured validated marker appears in the WHO 2020 report text."""
    from pypdf import PdfReader

    p = config.raw_dir().parent / "guidelines" / "who_drug_efficacy_report_2020.pdf"
    if not p.exists():
        return {"checked": False, "reason": f"{p.name} not found"}
    text = " ".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    missing = [m for m in config.ml()["resistance"]["k13_validated"] if m not in text]
    return {"checked": True, "missing_from_report": missing}
