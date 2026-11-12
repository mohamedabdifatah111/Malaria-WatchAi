"""Clean and validate MAP parasite-rate survey points (PfPR and PvPR).

Every record removed is counted under exactly one reason (first failing rule,
in the order of ``DROP_RULES``) so the validation report adds up.

Run:  python -m ml.src.data.surveys
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from ml.src import config, io
from ml.src.data import boundaries

log = logging.getLogger("ml.surveys")

DROP_RULES = [
    "withheld_by_provider",       # location or metrics not released by MAP
    "missing_counts_or_coords",
    "examined_not_positive",      # examined <= 0
    "positives_invalid",          # positives < 0 or > examined
    "year_missing_or_out_of_period",
    "outside_study_country",      # > buffer outside the stated country
    "duplicate",
]

SPECIES_COLS = {"pf": ("pf_pos", "pf_pr"), "pv": ("pv_pos", "pv_pr")}


def load_raw(species: str = "pf", countries: list[str] | None = None) -> pd.DataFrame:
    rows = []
    for iso3 in countries or config.countries():
        p = config.raw_dir() / "map" / f"{species}pr_{iso3}.geojson"
        if not p.exists():
            raise FileNotFoundError(f"missing {p}; run `python -m mal.fetch`")
        with open(p, encoding="utf-8") as f:
            feats = json.load(f)["features"]
        rows += [ft["properties"] for ft in feats]
    return pd.DataFrame(rows)


def empirical_logit(pos, n):
    """log((y + 0.5) / (n - y + 0.5)) - finite at 0% and 100% prevalence."""
    pos = np.asarray(pos, dtype=float)
    n = np.asarray(n, dtype=float)
    return np.log((pos + 0.5) / (n - pos + 0.5))


def inv_logit(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=float)))


def normalise_method(m) -> str:
    if m is None or (isinstance(m, float) and np.isnan(m)):
        return "unknown"
    s = str(m).lower()
    if "pcr" in s:
        return "pcr"
    if "rdt" in s and "microscopy" in s:
        return "rdt_confirmed_microscopy"
    if "rdt" in s:
        return "rdt"
    if "microscopy" in s:
        return "microscopy"
    return "other"


def flag_drops(df: pd.DataFrame, species: str = "pf") -> pd.Series:
    """Return the drop reason per row (None = keep), excluding spatial and duplicate rules."""
    pos_col, _ = SPECIES_COLS[species]
    y0, y1 = config.survey_years()
    reason = pd.Series(None, index=df.index, dtype=object)

    def mark(mask, why):
        m = mask & reason.isna()
        reason[m] = why

    released = df["location_available"].fillna(False).astype(bool) & \
        df["malaria_metrics_available"].fillna(False).astype(bool)
    mark(~released, "withheld_by_provider")
    mark(df[[pos_col, "examined", "latitude", "longitude"]].isna().any(axis=1), "missing_counts_or_coords")
    ex = pd.to_numeric(df["examined"], errors="coerce")
    pos = pd.to_numeric(df[pos_col], errors="coerce")
    mark(ex <= 0, "examined_not_positive")
    mark((pos < 0) | (pos > ex), "positives_invalid")
    yr = pd.to_numeric(df["year_start"], errors="coerce")
    mark(yr.isna() | (yr < y0) | (yr > y1), "year_missing_or_out_of_period")
    return reason


def dedupe_key(df: pd.DataFrame, pos_col: str) -> pd.Series:
    cols = [df["country_id"].astype(str), df["latitude"].round(4).astype(str),
            df["longitude"].round(4).astype(str), df["year_start"].astype(str),
            df["month_start"].astype(str), df["lower_age"].astype(str),
            df["upper_age"].astype(str), df["examined"].astype(str), df[pos_col].astype(str)]
    key = cols[0]
    for c in cols[1:]:
        key = key + "|" + c
    return key


def clean(raw: pd.DataFrame, species: str = "pf") -> tuple[gpd.GeoDataFrame, dict]:
    pos_col, _ = SPECIES_COLS[species]
    cfg = config.ml()["surveys"]
    df = raw.copy()
    df["drop_reason"] = flag_drops(df, species)

    # Spatial rule: point must fall in (or within buffer of) its stated country.
    ok = df["drop_reason"].isna()
    pts = gpd.GeoDataFrame(df.loc[ok], geometry=gpd.points_from_xy(df.loc[ok, "longitude"],
                                                                   df.loc[ok, "latitude"]), crs="EPSG:4326")
    reg = boundaries.assign_regions(pts, buffer_km=cfg["coord_buffer_km"])
    bad_space = reg["adm0_country"].isna() | (reg["adm0_country"] != pts["country_id"])
    df.loc[bad_space[bad_space].index, "drop_reason"] = "outside_study_country"
    for c in ("adm0_id", "adm1_id", "adm2_id", "dist_outside_country_km"):
        df[c] = reg[c].reindex(df.index)

    # Duplicates among otherwise-valid rows: keep the first (lowest MAP id).
    df = df.sort_values("id")
    ok = df["drop_reason"].isna()
    key = dedupe_key(df, pos_col).where(ok)
    dup = ok & key.duplicated(keep="first")
    df.loc[dup, "drop_reason"] = "duplicate"

    report = _report(df, species)
    kept = df[df["drop_reason"].isna()].copy()

    ex = kept["examined"].astype(float)
    pos = kept[pos_col].astype(float)
    out = pd.DataFrame({
        "survey_id": f"MAP-{species.upper()}-" + kept["id"].astype(str),
        "map_id": kept["id"].astype("int64"),
        "species": "P. falciparum" if species == "pf" else "P. vivax",
        "country": kept["country_id"],
        "adm1_id": kept["adm1_id"],
        "adm2_id": kept["adm2_id"],
        "site_name": kept["site_name"],
        "longitude": kept["longitude"].astype(float),
        "latitude": kept["latitude"].astype(float),
        "rural_urban": kept["rural_urban"],
        "year": kept["year_start"].astype(int),
        "year_end": pd.to_numeric(kept["year_end"], errors="coerce").astype("Int64"),
        "month_start": pd.to_numeric(kept["month_start"], errors="coerce").astype("Int64"),
        "lower_age": pd.to_numeric(kept["lower_age"], errors="coerce").astype(float),
        "upper_age": pd.to_numeric(kept["upper_age"], errors="coerce").astype(float),
        "examined": ex,
        "positive": pos,
        "prevalence": pos / ex,
        "emp_logit": empirical_logit(pos, ex),
        "weight": np.minimum(ex, cfg["weight_cap"]),
        "diag_method": kept["method"].map(normalise_method),
        "positives_non_integer": (pos % 1 != 0),
        "dist_outside_country_km": kept["dist_outside_country_km"].astype(float),
        "source_id": pd.to_numeric(kept["source_id1"], errors="coerce").astype("Int64"),
        "source_title": kept["title1"],
        "citation": kept["citation1"],
    })
    out["diag_rdt"] = out["diag_method"].eq("rdt").astype(float)
    out.loc[out["diag_method"].eq("unknown"), "diag_rdt"] = np.nan
    out["decade"] = (out["year"] // 10 * 10).astype(int)
    out["evidence_ids"] = [[f"MAP-SRC-{s}"] if pd.notna(s) else ["MAP-PR-SURVEYS"]
                           for s in out["source_id"]]
    out["data_status"] = "observed"
    gdf = gpd.GeoDataFrame(out.reset_index(drop=True),
                           geometry=gpd.points_from_xy(out["longitude"], out["latitude"]), crs="EPSG:4326")
    return gdf, report


def _report(df: pd.DataFrame, species: str) -> dict:
    rep = {"species": species, "rules": DROP_RULES, "by_country": {}}
    for c, g in df.groupby("country_id"):
        counts = g["drop_reason"].value_counts().to_dict()
        kept = g[g["drop_reason"].isna()]
        rep["by_country"][c] = {
            "raw_records": int(len(g)),
            "dropped": {r: int(counts.get(r, 0)) for r in DROP_RULES},
            "kept": int(len(kept)),
            "kept_year_range": [int(kept["year_start"].min()), int(kept["year_start"].max())] if len(kept) else None,
            "kept_age_missing": int(kept[["lower_age", "upper_age"]].isna().any(axis=1).sum()),
            "kept_method": kept["method"].map(normalise_method).value_counts().to_dict(),
        }
    tot = {r: sum(v["dropped"][r] for v in rep["by_country"].values()) for r in DROP_RULES}
    rep["total"] = {"raw_records": int(len(df)), "dropped": tot,
                    "kept": int(df["drop_reason"].isna().sum())}
    assert rep["total"]["raw_records"] == rep["total"]["kept"] + sum(tot.values())
    return rep


def run() -> dict:
    results = {}
    for sp, name in (("pf", "surveys.parquet"), ("pv", "surveys_pv.parquet")):
        gdf, rep = clean(load_raw(sp), sp)
        io.write_geoparquet(gdf, name, {"source": "MAP 202406 parasite rate surveys",
                                       "units": {"prevalence": "proportion 0-1", "examined": "persons"}})
        results[sp] = rep
    io.write_json(results, "survey_validation.json", directory=config.outputs_dir())
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    r = run()
    for sp, rep in r.items():
        print(sp, json.dumps(rep["total"], indent=1))
