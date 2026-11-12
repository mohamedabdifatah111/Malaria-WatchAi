"""Tests for the grounding check and survey prioritisation. Inputs are TEST FIXTURES."""
import numpy as np
import pandas as pd
import pytest

from ml.src import config
from ml.src.grounding import check_brief, extract_numbers

TOOLS = [{"results": [{"value": 0.19564, "lower": 0.0302, "upper": 0.6286, "year": 2020,
                       "evidence_ids": ["MODEL-PFPR-0.1.0"]}]},
         {"pooled_country": [{"acpr_percent": 96.8632, "study_count": 8, "n_patients": 927.0,
                              "evidence_ids": ["WHO-MTM"]}]}]


def test_extract_handles_percent_millions_commas_and_ids():
    n = extract_numbers("PfPR 19.6% in 2020; 1.2 million people; 42,529,336 total; see WHO-MTM-TES-578.")
    vals = [x["value"] for x in n]
    assert 19.6 in vals and 2020 in vals and 1.2e6 in vals and 42529336 in vals
    assert 578 not in vals  # digits inside an evidence id are not claims


def test_grounded_brief_passes_with_evidence():
    r = check_brief("Modelled PfPR in 2020 was 19.6% (3% to 63%). AL efficacy 96.9% from 8 studies, "
                    "927 patients.", TOOLS)
    assert r["grounded"], r["unsupported"]
    ev = {e for s in r["supported"] for e in s["evidence_ids"]}
    assert {"MODEL-PFPR-0.1.0", "WHO-MTM"} <= ev


def test_invented_number_is_blocked():
    r = check_brief("PfPR was 19.6% and 1.2 million children are infected.", TOOLS)
    assert not r["grounded"]
    assert [u["text"] for u in r["unsupported"]] == ["1.2 million"]


def test_agent_arithmetic_is_blocked():
    # 96.9 - 19.6 = 77.3 is not in any tool result
    r = check_brief("The gap is 77.3 points.", TOOLS)
    assert not r["grounded"]


def test_precision_tolerance():
    assert check_brief("19.56%", TOOLS)["grounded"]
    assert check_brief("20%", TOOLS)["grounded"]          # rounds from 19.56
    assert not check_brief("19.4%", TOOLS)["grounded"]     # wrong at stated precision


def test_list_numbering_ignored_and_weak_labelled():
    r = check_brief("1. AL efficacy 96.9%\n2. Studies: 8", TOOLS)
    assert r["grounded"]
    weak = [s for s in r["supported"] if s["strength"] == "weak"]
    assert any(s["text"] == "8" for s in weak)


# ----------------------------------------------------------------- survey priority
def test_expected_reduction_is_positive_near_unsurveyed_people():
    from ml.src.models.survey_priority import expected_reductions
    bins = {"edges_km": [0, 10, 25, 50, 100], "halfwidth_logit": [1.0, 1.5, 1.5, 1.5, 2.5]}
    cells = pd.DataFrame({"x_eqd": [0.0, 200_000.0], "y_eqd": [0.0, 0.0], "estimate": [0.1, 0.1],
                          "nearest_survey_distance_km": [150.0, 1.0], "pop_2020": [1000.0, 1000.0]})
    sites = pd.DataFrame({"site_x_eqd": [0.0, 200_000.0], "site_y_eqd": [0.0, 0.0]})
    red = expected_reductions(cells, sites, bins)
    assert red[0] > 0            # survey where people are 150 km from data helps
    assert red[1] == pytest.approx(0.0)  # survey where data already exists changes nothing


P = config.processed_dir()


@pytest.mark.skipif(not (P / "survey_priority.parquet").exists(), reason="pipeline outputs not built")
def test_survey_priority_output():
    p = pd.read_parquet(P / "survey_priority.parquet")
    assert (p["expected_burden_reduction"] >= -1e-6).all()
    assert p["rank_overall"].is_monotonic_increasing
    assert np.all(np.diff(p["expected_burden_reduction"].to_numpy()) <= 1e-6)
    assert p["reason"].str.len().gt(0).all()


@pytest.mark.skipif(not (P / "survey_priority.parquet").exists(), reason="pipeline outputs not built")
def test_demo_dossiers_are_grounded():
    from ml.src.dossier import DEMO_PLACES, build
    for place in DEMO_PLACES:
        d = build(place)
        assert d["status"] == "ok" and d["grounding"]["grounded"], (place, d["grounding"]["unsupported"])
