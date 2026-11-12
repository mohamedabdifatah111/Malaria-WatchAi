"""WHO Malaria Threats Map: therapeutic efficacy studies + molecular markers.

Source is the public WHO xMart OData API that the Threats Map web app itself
calls (https://xmart-api-public.who.int/MAL_THREATS). Tables pulled:

- FACT_TREATMENT_VIEW  : TES rows (drug, follow-up, N, PCR-corrected failure)
- FACT_AMDER_MM_VIEW   : molecular-marker study sites (site, year, N, MM_TYPE)
- FACT_AMDER_GENO_VIEW : genotype proportions per marker study
                         (join GENO.K13_CODE -> MM.Code)
- TRANSLATIONS         : code -> label lookups (drug names, species, ...)

GENO_VIEW returns broken JSON when its DimensionID column is requested, so we
always $select an explicit column list for it.
"""
from __future__ import annotations

from mal.config import countries
from mal.fetch._common import get_json, raw_dir, save_records

BASE = "https://xmart-api-public.who.int/MAL_THREATS"
LICENCE = "CC BY-NC-SA 3.0 IGO (WHO Malaria Threats Map)"
PAGE = 1000

GENO_COLUMNS = "CODE,K13_CODE,PROPORTION,GENOTYPE"


def odata_all(entity: str, filt: str | None = None, select: str | None = None) -> list[dict]:
    rows: list[dict] = []
    skip = 0
    while True:
        params = {"$top": PAGE, "$skip": skip}
        if filt:
            params["$filter"] = filt
        if select:
            params["$select"] = select
        page = get_json(f"{BASE}/{entity}", params)["value"]
        rows.extend(page)
        if len(page) < PAGE:
            return rows
        skip += PAGE


def run(force: bool = False) -> None:
    out = raw_dir("who_mtm")
    iso2 = list(countries().values())
    cfilt = " or ".join(f"ISO2 eq '{c}'" for c in iso2)

    jobs = [
        ("FACT_TREATMENT_VIEW", "who_mtm_treatment", cfilt, None),
        ("FACT_AMDER_MM_VIEW", "who_mtm_markers_sites", cfilt, None),
        # GENO has no country column; pull all and join on K13_CODE -> MM.Code
        ("FACT_AMDER_GENO_VIEW", "who_mtm_markers_genotypes", None, GENO_COLUMNS),
        ("TRANSLATIONS", "who_mtm_translations", None, "FIELD,VALUE_,EN,DATASET"),
    ]
    for entity, sid, filt, select in jobs:
        url = f"{BASE}/{entity}" + (f"?$filter={filt}" if filt else "") \
            + (f"{'&' if filt else '?'}$select={select}" if select else "")
        save_records(lambda e=entity, f=filt, s=select: odata_all(e, f, s),
                     out / f"{entity}.json", sid, url, LICENCE, force=force)
