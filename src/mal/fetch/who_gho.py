"""WHO Global Health Observatory: World Malaria Report country estimates.

Used for the burden cross-check and for the P. falciparum / P. vivax share of
indigenous cases (species tab). P. malariae / P. ovale shares are NOT in GHO;
they come from MIS microscopy tables (manual, see species.py).
"""
from __future__ import annotations

from mal.config import countries
from mal.fetch._common import get_json, raw_dir, save_records

API = "https://ghoapi.azureedge.net/api"
LICENCE = "CC BY-NC-SA 3.0 IGO (WHO GHO)"
INDICATORS = {
    "MALARIA_EST_CASES": "Estimated number of malaria cases",
    "MALARIA_EST_DEATHS": "Estimated number of malaria deaths",
    "MALARIA_EST_INCIDENCE": "Estimated incidence per 1000 population at risk",
    "MALARIA_PF_INDIG": "Indigenous P. falciparum cases",
    "MALARIA_PV_INDIG": "Indigenous P. vivax cases",
    "MALARIA_CONF_CASES": "Confirmed malaria cases",
}


def run(force: bool = False) -> None:
    out = raw_dir("who_gho")
    iso3 = list(countries())
    filt = " or ".join(f"SpatialDim eq '{c}'" for c in iso3)
    for code in INDICATORS:
        url = f"{API}/{code}?$filter={filt}"
        save_records(lambda c=code: get_json(f"{API}/{c}", {"$filter": filt})["value"],
                     out / f"{code}.json", f"gho_{code}".lower(), url, LICENCE,
                     force=force)
