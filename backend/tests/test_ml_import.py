"""ML-output import. Uses the real ML outputs in <repo>/data/processed when present.

The mapping tests need no database and also run without Django/PostGIS:
    cd backend && python -m pytest --noconftest -p no:django tests/test_ml_import.py -k "not db"
"""
import re
from pathlib import Path

import pytest

from apps.core.ml_import import RISK_CLASSES, SPECIES, Mapper

PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"
needs_outputs = pytest.mark.skipif(not (PROCESSED / "evidence.parquet").exists(),
                                   reason="ML outputs not built (python -m ml.src.pipeline)")


@pytest.fixture(scope="module")
def built():
    m = Mapper(PROCESSED)
    return m, m.build()


def _ordered(lo, hi):
    return lo is None or hi is None or lo <= hi


@needs_outputs
def test_evidence_ids_match_backend_format(built):
    _, b = built
    ids = [r["evidence_id"] for r in b["evidence"]]
    assert ids and all(re.fullmatch(r"E\d{3,}", i) for i in ids) and len(ids) == len(set(ids))
    assert all(int(i[1:]) >= 10001 for i in ids)  # never collides with hand-entered E001...
    assert all(len(r["source_name"]) <= 300 and len(r["license"]) <= 200 for r in b["evidence"])
    assert {r["evidence_type"] for r in b["evidence"]} <= {
        "survey", "model_output", "publication", "guideline", "weather", "synthetic", "other"}


@needs_outputs
def test_rows_cite_known_evidence(built):
    _, b = built
    known = {r["evidence_id"] for r in b["evidence"]}
    for table, rows in b.items():
        if table not in ("evidence", "marker"):
            assert all(r["source"] in known for r in rows), table


@needs_outputs
def test_prevalence_estimate_constraints(built):
    _, b = built
    for r in b["prevalence_estimate"]:
        assert 0 <= r["estimate"] <= 1 and r["region"][1] in ("ADM1", "ADM2")
        assert r["lower_interval"] is None or r["lower_interval"] <= r["estimate"]
        assert r["upper_interval"] is None or r["upper_interval"] >= r["estimate"]
    keys = [(r["region"], r["year"], r["indicator"], r["source_type"], r["model_version"])
            for r in b["prevalence_estimate"]]
    assert len(keys) == len(set(keys))  # prev_est_unique


@needs_outputs
def test_species_and_population_constraints(built):
    _, b = built
    for r in b["species"]:
        assert r["species"] in SPECIES and r["record_type"] in ("survey", "presence_only")
        if r["record_type"] == "survey":
            assert r["positive"] is not None and r["positive"] <= r["examined"]
        else:
            assert r["positive"] is None and r["examined"] is None
    for r in b["population_at_risk"]:
        assert r["risk_class"] in RISK_CLASSES and r["population"] >= 0 and len(r["uncertainty_status"]) <= 50


@needs_outputs
def test_efficacy_constraints(built):
    _, b = built
    for r in b["drug_efficacy"]:
        assert 0 <= r["acpr_percent"] <= 100 and r["n_patients"] >= 1 and r["followup_days"] >= 1
        assert _ordered(r["confidence_interval_lower"], r["confidence_interval_upper"])
        assert _ordered(r["prediction_interval_lower"], r["prediction_interval_upper"])
        assert r["study_year_start"] <= r["study_year_end"]
        if r["record_type"] == "study":
            assert r["study_count"] is None and r["study_id"]
        else:
            assert r["study_count"] >= 1
    studies = [(r["source"], r["study_id"], r["drug"], r["followup_days"])
               for r in b["drug_efficacy"] if r["record_type"] == "study"]
    assert len(studies) == len(set(studies))  # eff_unique_study


@needs_outputs
def test_resistance_constraints(built):
    _, b = built
    for r in b["resistance_observation"]:
        assert 1 <= r["n_tested"] and r["n_mutant"] <= r["n_tested"]
    for r in b["marker_trend"]:
        assert r["observed_frequency"] is not None or r["predicted_frequency"] is not None
        assert _ordered(r["confidence_interval_lower"], r["confidence_interval_upper"])


@needs_outputs
def test_every_skip_has_a_reason(built):
    m, b = built
    rep = m.report(b)
    assert rep["evidence"]["rows"] > 0 and rep["prevalence_estimate"]["rows"] > 0
    assert "interval_does_not_contain_estimate" not in rep["prevalence_estimate"]["skipped"]


# ---------- database ----------

@needs_outputs
@pytest.mark.django_db
def test_db_import_is_idempotent_and_skips_unknown_regions():
    from django.core.management import call_command

    from apps.drug_efficacy.models import DrugEfficacyRecord
    from apps.evidence.models import EvidenceSource
    from apps.prevalence.models import PrevalenceEstimate

    call_command("import_ml_outputs", "--processed-dir", str(PROCESSED))
    n_ev, n_eff = EvidenceSource.objects.count(), DrugEfficacyRecord.objects.count()
    assert n_ev > 0
    # no boundaries imported in this test: region-linked rows are skipped, pooled rows (no region) load
    assert PrevalenceEstimate.objects.count() == 0
    assert DrugEfficacyRecord.objects.filter(record_type="pooled").exists()
    call_command("import_ml_outputs", "--processed-dir", str(PROCESSED))
    assert EvidenceSource.objects.count() == n_ev and DrugEfficacyRecord.objects.count() == n_eff
