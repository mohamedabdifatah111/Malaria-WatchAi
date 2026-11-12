"""WHO guidance PDFs for the agent's guideline_search tool.

Resolved through the WHO IRIS (DSpace 7) REST API from a stable handle:
handle -> item -> ORIGINAL bundle -> first PDF bitstream. Chunking into
data/guidelines/chunks.parquet is P3's job (agent side).
"""
from __future__ import annotations

from mal.config import path
from mal.fetch._common import download, get_json, log, session, timeout

IRIS = "https://iris.who.int/server/api"
LICENCE = "CC BY-NC-SA 3.0 IGO (WHO)"

DOCS = {
    # source_id: (IRIS handle, short title / version)
    "who_guidelines_malaria_2025": ("10665/382254", "WHO guidelines for malaria, 13 August 2025"),
    "who_drug_efficacy_report_2020": ("10665/336692", "Report on antimalarial drug efficacy, resistance and response: 10 years of surveillance (2010-2019)"),
    "who_strategy_drug_resistance_africa_2022": ("10665/364221", "Strategy to respond to antimalarial drug resistance in Africa (2022)"),
}


def resolve_pdf(handle: str) -> tuple[str, str]:
    """Return (download URL, filename) of the first PDF in an IRIS item."""
    r = session().get(f"{IRIS}/pid/find", params={"id": f"hdl:{handle}"},
                      allow_redirects=False, timeout=timeout())
    item_url = r.headers.get("Location") or r.json()["_links"]["self"]["href"]
    bundles = get_json(f"{item_url}/bundles")["_embedded"]["bundles"]
    original = next(b for b in bundles if b["name"] == "ORIGINAL")
    bits = get_json(original["_links"]["bitstreams"]["href"])["_embedded"]["bitstreams"]
    pdf = next(b for b in bits if b["name"].lower().endswith(".pdf"))
    return f"{IRIS}/core/bitstreams/{pdf['uuid']}/content", pdf["name"]


def run(force: bool = False) -> None:
    out = path("guidelines")
    out.mkdir(parents=True, exist_ok=True)
    for sid, (handle, title) in DOCS.items():
        try:
            url, name = resolve_pdf(handle)
        except Exception as e:  # keep going; one missing PDF must not stop the fetch
            log.warning("could not resolve %s (hdl:%s): %s", title, handle, e)
            continue
        download(url, out / f"{sid}.pdf", sid, LICENCE, force=force)
        log.info("        %s <- %s", title, name)
