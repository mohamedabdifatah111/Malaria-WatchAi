"""Fetch layer: manifest contract, hash-checked caching, DATA.md coverage."""
import csv
import time

import pytest

from mal.fetch import _common, data_md


@pytest.fixture
def tmp_manifest(tmp_path, monkeypatch):
    mp = tmp_path / "manifest.csv"
    monkeypatch.setattr(_common, "path", lambda key: mp if key == "manifest" else tmp_path)
    return mp


def test_manifest_has_contract_columns_and_upserts(tmp_manifest):
    _common.write_manifest_row("a", "http://x/a", "0" * 64, "CC BY 4.0", 3)
    _common.write_manifest_row("a", "http://x/a", "1" * 64, "CC BY 4.0", 5)
    _common.write_manifest_row("b", "http://x/b", "2" * 64, "CC0", None)
    with open(tmp_manifest, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["source_id", "url", "accessed_utc", "sha256", "licence", "rows"]
        rows = list(reader)
    assert [r["source_id"] for r in rows] == ["a", "b"]
    assert rows[0]["rows"] == "5" and rows[0]["sha256"] == "1" * 64
    assert rows[1]["rows"] == ""


def test_cache_detects_changed_file(tmp_manifest, tmp_path):
    f = tmp_path / "data.bin"
    f.write_bytes(b"hello")
    _common.record_existing(f, "src", "http://x", "CC0", 1)
    assert _common.is_cached("src", f)
    f.write_bytes(b"tampered")
    assert not _common.is_cached("src", f)
    assert not _common.is_cached("unknown", f)


def test_record_existing_keeps_access_time_when_unchanged(tmp_manifest, tmp_path):
    f = tmp_path / "manual.csv"
    f.write_text("a,b\n")
    _common.record_existing(f, "manual", "manual", "CC0", 0)
    first = _common.read_manifest()["manual"]["accessed_utc"]
    time.sleep(1.1)  # access time has 1 s resolution
    _common.record_existing(f, "manual", "manual", "CC0", 0)
    assert _common.read_manifest()["manual"]["accessed_utc"] == first
    f.write_text("a,b\n1,2\n")
    time.sleep(1.1)
    _common.record_existing(f, "manual", "manual", "CC0", 1)
    assert _common.read_manifest()["manual"]["accessed_utc"] != first


@pytest.mark.parametrize("sid", [
    "map_pfpr_ken", "map_pvpr_eth", "map_duffy_negativity", "geoboundaries_uga_adm2",
    "worldclim_bio_ken", "worldclim_elev_tza", "modis_ndvi_2020", "worldpop_ppp_2020_ken",
    "ghsl_smod_2020", "hydrorivers_af", "naturalearth_lakes_10m", "who_mtm_treatment",
    "pf7_samples", "gho_malaria_pv_indig", "gbif_plasmodium_ken", "mis_microscopy_manual",
    "who_guidelines_malaria_2025",
])
def test_every_source_id_has_a_data_md_family(sid):
    assert data_md.family_of(sid) < len(data_md.FAMILIES)


def test_who_mtm_ids_are_not_swallowed_by_guideline_prefix():
    titles = data_md.FAMILIES
    assert "Threats Map" in titles[data_md.family_of("who_mtm_treatment")][1]
    assert "guidance" in titles[data_md.family_of("who_drug_efficacy_report_2020")][1]
