"""Species records: GBIF Plasmodium occurrences + a manual MIS microscopy template.

- P. vivax survey points come from MAP PvPR (map_surveys.py).
- Country shares of Pf / Pv cases come from WHO GHO (who_gho.py).
- GBIF holds few Plasmodium records in these countries (dozens to a few
  hundred); every row keeps its own licence and dataset key.
- P. malariae / P. ovale shares: MIS microscopy tables are PDF reports, so
  they are entered by hand into data/raw/species/mis_microscopy_manual.csv.
"""
from __future__ import annotations

import csv

from mal.config import countries
from mal.fetch._common import get_json, log, raw_dir, record_existing, save_records

GBIF = "https://api.gbif.org/v1/occurrence/search"
PLASMODIUM_GENUS_KEY = 8364053  # GBIF backbone key for genus Plasmodium
PAGE = 300

MIS_COLUMNS = ["country", "survey", "year", "n_positive_microscopy",
               "pf_only", "pm_only", "po_only", "pv_only", "mixed",
               "source_title", "source_url", "page", "entered_by"]


def gbif_all(iso2: str) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        res = get_json(GBIF, {"taxonKey": PLASMODIUM_GENUS_KEY, "country": iso2,
                              "limit": PAGE, "offset": offset})
        rows.extend(res["results"])
        if res.get("endOfRecords", True):
            return rows
        offset += PAGE


def run(force: bool = False) -> None:
    out = raw_dir("species")
    for iso3, iso2 in countries().items():
        url = f"{GBIF}?taxonKey={PLASMODIUM_GENUS_KEY}&country={iso2}"
        save_records(lambda c=iso2: gbif_all(c), out / f"gbif_plasmodium_{iso3}.json",
                     f"gbif_plasmodium_{iso3}".lower(), url,
                     "Per record (CC0 / CC BY / CC BY-NC) - see 'license' field",
                     force=force)

    tpl = out / "mis_microscopy_manual.csv"
    if not tpl.exists():
        with open(tpl, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(MIS_COLUMNS)
        log.info("created %s - fill from MIS/DHS final reports (manual step)", tpl.name)
    with open(tpl, encoding="utf-8") as f:
        n = sum(1 for _ in f) - 1
    record_existing(tpl, "mis_microscopy_manual",
                    "manual entry from national MIS/DHS final reports",
                    "Per report (DHS Program / national statistics office)", n)
