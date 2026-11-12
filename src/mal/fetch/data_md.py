"""Render DATA.md from data/manifest.csv (never edit DATA.md by hand)."""
from __future__ import annotations

from collections import defaultdict

from mal.config import ROOT
from mal.fetch._common import read_manifest

# source_id prefix -> (family title, what it is used for, fallback if access fails)
FAMILIES = [
    ("map_pfpr", "MAP PfPR survey points", "Pf prevalence target (notebook 01)",
     "Manual CSV export from data.malariaatlas.org; DHS/MIS needs registration (last resort)"),
    ("map_pvpr", "MAP PvPR survey points", "P. vivax presence (notebook 02 A)",
     "Literature and MIS reports only"),
    ("map_duffy", "MAP Duffy-negativity phenotype frequency (2011)", "P. vivax covariate / explanation",
     "Cite the published map (Howes et al. 2011)"),
    ("geoboundaries", "geoBoundaries gbOpen ADM0-ADM2", "District polygons, gazetteer for the agent",
     "GADM (check licence)"),
    ("worldclim_bio", "WorldClim 2.1 bioclim 30 s (bio1 mean temp, bio12 annual rain)", "Rainfall, temperature",
     "CHIRPS annual rainfall"),
    ("worldclim_elev", "WorldClim 2.1 elevation 30 s (SRTM-based)", "Elevation",
     "SRTM via USGS EarthExplorer"),
    ("modis_ndvi", "MODIS MOD13A1 v061 NDVI, annual median (computed)", "Vegetation index",
     "Earth Engine export; else ship without NDVI and list the gap in ASSUMPTIONS.md"),
    ("worldpop", "WorldPop 2020 UN-adjusted 1 km (counts + density)", "Population density, population at risk",
     "WorldPop 100 m aggregated"),
    ("ghsl", "GHSL SMOD 2020 degree of urbanisation (R2023A, 1 km)", "Urban/rural class",
     "WorldPop density >= 300/km2 rule, documented"),
    ("hydrorivers", "HydroRIVERS v1.0 Africa", "Distance to water", "Natural Earth 10 m rivers"),
    ("hydrolakes", "HydroLAKES v1.0 (optional, --full)", "Distance to water", "Natural Earth 10 m lakes"),
    ("naturalearth", "Natural Earth 10 m lakes / rivers", "Distance to water (lakes)", "-"),
    ("who_mtm", "WHO Malaria Threats Map (xMart public API)", "TES efficacy + molecular markers (notebook 02 B/C)",
     "Manual Excel download from the Threats Map site; WWARN only if approved in time"),
    ("pf7", "MalariaGEN Pf7", "pfkelch13 / pfmdr1 / pfcrt genotypes by admin-1 x year",
     "Threats Map markers only"),
    ("gho", "WHO GHO / World Malaria Report country estimates", "Burden cross-check; Pf vs Pv case share", "None needed"),
    ("gbif", "GBIF Plasmodium occurrences", "Species records", "Country-level reports only"),
    ("mis_microscopy", "MIS/DHS microscopy tables (manual entry)", "P. malariae / P. ovale shares", "Country-level reports only"),
    ("who_", "WHO guidance PDFs (IRIS)", "Agent guideline_search", "National guidelines (e.g. Kenya MoH)"),
]

MANUAL_STEPS = [
    "`data/raw/species/mis_microscopy_manual.csv` is typed in by hand from MIS/DHS final "
    "report microscopy tables. Record the report title, URL and page per row.",
    "If any automated source fails at the venue, the manual export used instead must be "
    "logged here with the date and the person who downloaded it.",
]


def family_of(sid: str) -> int:
    for i, (prefix, *_rest) in enumerate(FAMILIES):
        if sid.startswith(prefix):
            return i
    return len(FAMILIES)


def write_data_md() -> None:
    rows = read_manifest()
    groups: dict[int, list[dict]] = defaultdict(list)
    for sid, row in rows.items():
        groups[family_of(sid)].append(row)

    out = [
        "# DATA",
        "",
        "Generated from `data/manifest.csv` by `python -m mal.fetch` - do not edit by hand.",
        "All inputs are open and aggregate; no patient-level records. Raw files live in",
        "`data/raw/` (gitignored); only the manifest is committed. Licences are as stated",
        "by each provider at access time - check before redistributing any file.",
        "",
        "## Sources",
        "",
        "| Source | Used for | Files | Rows | Last accessed (UTC) | Licence | Fallback |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, (prefix, title, use, fallback) in enumerate(FAMILIES):
        g = groups.get(i)
        if not g:
            continue
        n_rows = sum(int(r["rows"]) for r in g if r["rows"])
        last = max(r["accessed_utc"] for r in g)
        lic = "; ".join(sorted({r["licence"] for r in g}))
        out.append(f"| {title} | {use} | {len(g)} | {n_rows or '-'} | {last} | {lic} | {fallback} |")

    out += ["", "## Manual steps", ""] + [f"- {s}" for s in MANUAL_STEPS]
    out += ["", "## File manifest", "",
            "| source_id | rows | accessed_utc | sha256 (first 12) | url |", "|---|---|---|---|---|"]
    for sid in sorted(rows):
        r = rows[sid]
        out.append(f"| {sid} | {r['rows'] or '-'} | {r['accessed_utc']} | `{r['sha256'][:12]}` | {r['url']} |")
    (ROOT / "DATA.md").write_text("\n".join(out) + "\n", encoding="utf-8")
