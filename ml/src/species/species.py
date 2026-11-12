"""Plasmodium species evidence summary (no species distribution model).

Record types
  survey          MAP PfPR / PvPR surveys: positives AND examined (denominator-bearing)
  country_report  WHO GHO reported indigenous cases by species (country-year)
  presence_only   GBIF occurrence records: presence only - NEVER a case share
  no_evidence     species with no usable record in the downloaded sources

A species model is not fitted: the open P. vivax survey data (158 points,
mostly Ethiopia) and the absent P. malariae / P. ovale denominators do not
justify one. District-level species shares are never derived from
country-level or presence-only evidence.

Output: data/processed/species.parquet
"""
from __future__ import annotations

import json
import logging

import geopandas as gpd
import pandas as pd

from ml.src import config, io

log = logging.getLogger("ml.species")

SPECIES = ["P. falciparum", "P. vivax", "P. malariae", "P. ovale", "P. knowlesi"]
GBIF_NAME = {"Plasmodium falciparum": "P. falciparum", "Plasmodium vivax": "P. vivax",
             "Plasmodium malariae": "P. malariae", "Plasmodium ovale": "P. ovale",
             "Plasmodium knowlesi": "P. knowlesi"}
ISO2 = {"KEN": "KE", "TZA": "TZ", "ETH": "ET"}

COLUMNS = ["country", "region_id", "admin_level", "species", "record_type", "year", "year_start", "year_end",
           "positive", "examined", "n_surveys", "n_records", "value", "value_unit", "share",
           "share_definition", "source", "source_id", "evidence_ids", "status", "limitations"]

LIM_MICRO = ("Microscopy under-detects low-density and mixed infections and can misclassify "
             "P. ovale / P. malariae / P. knowlesi.")


def survey_records() -> pd.DataFrame:
    frames = []
    for f in ("surveys.parquet", "surveys_pv.parquet"):
        s = gpd.read_parquet(config.processed_dir() / f)
        g = s.groupby(["country", "adm1_id", "species", "year"]).agg(
            positive=("positive", "sum"), examined=("examined", "sum"), n_surveys=("survey_id", "size"),
            evidence_ids=("evidence_ids", lambda x: sorted({e for l in x for e in l}))).reset_index()
        frames.append(g)
    o = pd.concat(frames, ignore_index=True).rename(columns={"adm1_id": "region_id"})
    o["admin_level"] = "ADM1"
    o["record_type"] = "survey"
    o["value"] = o["positive"] / o["examined"]
    o["value_unit"] = "parasite rate (proportion of examined, all ages/methods as surveyed)"
    o["year_start"] = o["year_end"] = o["year"]
    o["source"] = "Malaria Atlas Project parasite rate surveys (202406)"
    o["source_id"] = "MAP-PR-SURVEYS"
    o["evidence_ids"] = [["MAP-PR-SURVEYS"] + e for e in o["evidence_ids"]]
    o["status"] = "ok"
    o["limitations"] = [[LIM_MICRO, "Only surveys released by MAP; withheld points are absent."]] * len(o)
    return o


def who_reported_cases() -> pd.DataFrame:
    rows = []
    raw = config.raw_dir() / "who_gho"
    for ind, sp in (("MALARIA_PF_INDIG", "P. falciparum"), ("MALARIA_PV_INDIG", "P. vivax")):
        p = raw / f"{ind}.json"
        if not p.exists():
            continue
        j = json.loads(p.read_text(encoding="utf-8"))
        for r in (j["value"] if isinstance(j, dict) else j):
            if r.get("SpatialDim") in config.countries() and r.get("NumericValue") is not None:
                rows.append({"country": r["SpatialDim"], "species": sp, "year": int(r["TimeDim"]),
                             "value": float(r["NumericValue"]), "indicator": ind})
    o = pd.DataFrame(rows)
    if o.empty:
        return o
    piv = o.pivot_table(index=["country", "year"], columns="species", values="value")
    if {"P. falciparum", "P. vivax"} <= set(piv.columns):
        share = (piv["P. vivax"] / (piv["P. falciparum"] + piv["P. vivax"])).rename("pv_share")
        o = o.join(share, on=["country", "year"])
        o["share"] = o["pv_share"].where(o["species"] == "P. vivax",
                                         1 - o["pv_share"]).where(o["pv_share"].notna())
        o = o.drop(columns="pv_share")
    o["share_definition"] = "share of reported indigenous Pf+Pv cases in that country-year"
    o["region_id"] = None
    o["admin_level"] = "ADM0"
    o["record_type"] = "country_report"
    o["value_unit"] = "reported indigenous cases"
    o["year_start"] = o["year_end"] = o["year"]
    o["source"] = "WHO Global Health Observatory"
    o["source_id"] = "WHO-GHO-" + o["indicator"]
    o["evidence_ids"] = [["WHO-GHO", s] for s in o["source_id"]]
    o["status"] = "ok"
    o["limitations"] = [["Routine reported cases depend on testing and reporting completeness; "
                         "mixed and non-Pf/Pv infections are not separated."]] * len(o)
    return o.drop(columns="indicator")


def gbif_presence() -> pd.DataFrame:
    rows = []
    for iso3 in config.countries():
        p = config.raw_dir() / "species" / f"gbif_plasmodium_{iso3}.json"
        if not p.exists():
            continue
        recs = json.loads(p.read_text(encoding="utf-8"))
        recs = recs.get("results", recs) if isinstance(recs, dict) else recs
        for r in recs:
            sp = GBIF_NAME.get(r.get("species"))
            if sp:
                rows.append({"country": iso3, "species": sp, "year": r.get("year")})
    o = pd.DataFrame(rows)
    if o.empty:
        return o
    g = o.groupby(["country", "species"]).agg(n_records=("species", "size"), year_start=("year", "min"),
                                              year_end=("year", "max")).reset_index()
    g["region_id"] = None
    g["admin_level"] = "ADM0"
    g["record_type"] = "presence_only"
    g["source"] = "GBIF occurrence records"
    g["source_id"] = "GBIF-" + g["country"]
    g["evidence_ids"] = [["GBIF-PLASMODIUM"]] * len(g)
    g["status"] = "presence_only"
    g["limitations"] = [["Presence-only records (mostly genomic samples); cannot establish prevalence "
                         "or case shares."]] * len(g)
    return g


MIS_SPECIES = {"pf_only": "P. falciparum", "pm_only": "P. malariae", "po_only": "P. ovale",
               "pv_only": "P. vivax", "mixed": "mixed infection"}


def mis_microscopy() -> pd.DataFrame:
    """National MIS/DHS microscopy species tables, hand-entered with report page.

    Convention for data/raw/species/mis_microscopy_manual.csv: species columns are
    the PERCENT of microscopy-positive people in the report table (mono-infections;
    'mixed' = all mixed combinations), n_positive_microscopy is the table's
    denominator. These are national values and are never applied to districts.
    """
    p = config.raw_dir() / "species" / "mis_microscopy_manual.csv"
    if not p.exists():
        return pd.DataFrame()
    m = pd.read_csv(p)
    m = m[m["country"].isin(config.countries())]
    rows = []
    for _, r in m.iterrows():
        sid = f"MIS-{r['country']}-{int(r['year'])}"
        for col, sp in MIS_SPECIES.items():
            if pd.isna(r.get(col)):
                continue
            rows.append({"country": r["country"], "region_id": None, "admin_level": "ADM0", "species": sp,
                         "record_type": "survey_report", "year": int(r["year"]), "year_start": int(r["year"]),
                         "year_end": int(r["year"]), "examined": float(r["n_positive_microscopy"]),
                         "value": float(r[col]), "share": float(r[col]) / 100.0,
                         "value_unit": "% of microscopy-positive people (mono-infection unless 'mixed')",
                         "share_definition": "share of microscopy-positive people in a national survey",
                         "source": f"{r['survey']} - {r['page']}", "source_id": sid,
                         "evidence_ids": ["MIS-REPORTS", sid], "status": "ok",
                         "limitations": [LIM_MICRO, "National survey value; not applicable to districts.",
                                         str(r["source_title"])]})
    return pd.DataFrame(rows)


RDT_ONLY_NOTES = {
    "TZA": "Tanzania MIS 2017 tested children by RDT only (SD Bioline Pf/Pan), which cannot identify "
           "P. malariae or P. ovale; no national microscopy species table was found in that report.",
}


def gaps(have: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in config.countries():
        for sp in SPECIES:
            if have.empty or not ((have["country"] == c) & (have["species"] == sp)
                                  & have["record_type"].isin(["survey", "country_report", "survey_report"])).any():
                lim = ["No denominator-bearing record for this species in the downloaded sources."]
                if sp == "P. knowlesi":
                    lim.append("P. knowlesi is a zoonotic species reported mainly from Southeast Asia; "
                               "no evidence was found for this country.")
                if sp in ("P. malariae", "P. ovale"):
                    lim.append(RDT_ONLY_NOTES.get(c, "Fill data/raw/species/mis_microscopy_manual.csv from "
                                                     "MIS/DHS report microscopy tables to add evidence."))
                rows.append({"country": c, "region_id": None, "admin_level": "ADM0", "species": sp,
                             "record_type": "no_evidence", "status": "insufficient_data",
                             "source": None, "source_id": None, "evidence_ids": [],
                             "limitations": lim})
    return pd.DataFrame(rows)


def run() -> pd.DataFrame:
    parts = [survey_records(), who_reported_cases(), gbif_presence(), mis_microscopy()]
    have = pd.concat([p for p in parts if len(p)], ignore_index=True)
    out = pd.concat([have, gaps(have)], ignore_index=True).reindex(columns=COLUMNS)
    io.write_parquet(out, "species.parquet", {"rules": "presence_only rows never carry shares"})
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    s = run()
    print(s.groupby(["country", "species", "record_type"]).size().unstack(fill_value=0))
