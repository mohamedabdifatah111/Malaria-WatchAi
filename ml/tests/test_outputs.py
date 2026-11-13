"""Contract tests on pipeline outputs. Skipped until the pipeline has run."""
import json

import numpy as np
import pandas as pd
import pytest

from ml.src import config

P = config.processed_dir()
REQUIRED = ["surveys.parquet", "grid_2020.parquet", "prevalence_grid.parquet", "prevalence_district.parquet",
            "prevalence_uncertainty.parquet", "pop_at_risk.parquet", "species.parquet",
            "efficacy_studies.parquet", "efficacy_pooled.parquet", "marker_observations.parquet",
            "marker_trends.parquet", "marker_predictions.parquet", "evidence.parquet", "metrics.json",
            "model_metadata.json"]

pytestmark = pytest.mark.skipif(not all((P / f).exists() for f in REQUIRED),
                                reason="pipeline outputs not built (python -m ml.src.pipeline)")


def test_surveys_valid():
    s = pd.read_parquet(P / "surveys.parquet")
    assert (s["examined"] > 0).all()
    assert (s["positive"] <= s["examined"]).all() and (s["positive"] >= 0).all()
    assert s["country"].isin(config.countries()).all()
    y0, y1 = config.survey_years()
    assert s["year"].between(y0, y1).all()
    assert not s["survey_id"].duplicated().any()


def test_prevalence_district_contract():
    d = pd.read_parquet(P / "prevalence_district.parquet")
    for c in ["country", "region_id", "year", "indicator", "estimate", "lower_interval", "upper_interval",
              "source_type", "model_version", "evidence_ids", "status"]:
        assert c in d.columns
    m = d[d["source_type"] == "modelled"]
    assert m["estimate"].between(0, 1).all()
    assert (m["lower_interval"] <= m["estimate"]).all() and (m["estimate"] <= m["upper_interval"]).all()
    assert set(d["source_type"]) <= {"modelled", "observed"}
    assert (m["year"] == config.prediction_year()).all()
    # every ADM2 polygon has a modelled row
    from ml.src.data import boundaries
    assert set(boundaries.level("ADM2")["region_id"]) <= set(m["region_id"])


def test_population_at_risk_sums_to_region_population():
    p = pd.read_parquet(P / "pop_at_risk.parquet")
    g = p.groupby("region_id").agg(tot=("population", "sum"), reg=("region_population_2020", "first"),
                                   lo=("population_if_lower_bound", "sum"))
    assert np.allclose(g["tot"], g["reg"], rtol=1e-6)
    assert np.allclose(g["lo"], g["reg"], rtol=1e-6)


def test_population_conserved_per_country():
    qa = json.loads((config.outputs_dir() / "feature_qa.json").read_text())
    for c, v in qa["population_conservation"].items():
        assert qa["grid_population_by_country"][c] == pytest.approx(v["raster_total"], rel=1e-4)


def test_efficacy_followups_never_mixed_and_counts_reported():
    p = pd.read_parquet(P / "efficacy_pooled.parquet")
    assert set(p["followup_days"]) <= {28, 42}
    ok = p[p["status"] == "ok"]
    assert (ok["study_count"] >= config.ml()["efficacy"]["min_studies_for_pooling"]).all()
    assert (ok["n_patients"] > 0).all()
    s = pd.read_parquet(P / "efficacy_studies.parquet")
    for _, r in ok.iterrows():
        used = s[(s["country"] == r["country"]) & (s["drug"] == r["drug"]) & (s["status"] == "ok")]
        assert (used[used["study_id"].isin(r["evidence_ids"])]["followup_days"] == r["followup_days"]).all()


def test_marker_frequencies_have_denominators_and_sources():
    o = pd.read_parquet(P / "marker_observations.parquet")
    assert (o["n_tested"] > 0).all() and (o["n_mutant"] <= o["n_tested"]).all()
    assert o["source"].notna().all() and o["evidence_ids"].map(len).gt(0).all()


def test_species_presence_only_has_no_share():
    s = pd.read_parquet(P / "species.parquet")
    po = s[s["record_type"] == "presence_only"]
    assert po["share"].isna().all() and po["examined"].isna().all()
    assert {"P. falciparum", "P. vivax", "P. malariae", "P. ovale", "P. knowlesi"} <= set(s["species"])
    rep = s[s["record_type"] == "survey_report"]
    assert rep["examined"].gt(0).all() and rep["region_id"].isna().all()  # national only, with denominator


def test_every_evidence_id_resolves():
    from ml.src import evidence
    reg = pd.read_parquet(P / "evidence.parquet")
    assert evidence.check_integrity(reg)["ok"]


def test_metrics_report_all_schemes_and_models():
    m = json.loads((P / "metrics.json").read_text())
    assert set(m["schemes"]) == {"spatial_block_5fold", "leave_one_adm1_out", "random_5fold"}
    for s in m["schemes"].values():
        assert set(s["models"]) == {"idw", "adm1_mean", "lightgbm"}


# docs/API.md field lists for the endpoints the ML outputs back. Keep in sync with the contract.
API_CONTRACT = {
    "prevalence_district.parquet": ["country", "region_id", "region_name", "year", "indicator", "estimate",
                                    "lower_interval", "upper_interval", "source_type", "model_version",
                                    "evidence_ids", "status"],
    "prevalence_grid.parquet": ["feature_id", "geometry", "estimate", "lower_interval", "upper_interval",
                                "source_type", "model_version", "evidence_ids"],
    "prevalence_adm2.geojson": ["feature_id", "geometry", "estimate", "lower_interval", "upper_interval",
                                "source_type", "model_version", "evidence_ids"],
    "prevalence_uncertainty.parquet": ["region_id", "estimate", "lower_interval", "upper_interval",
                                       "interval_width", "nearest_survey_distance_km", "survey_density",
                                       "extrapolation_flag", "reliability_status"],
    "pop_at_risk.parquet": ["country", "region_id", "year", "risk_class", "population", "population_source",
                            "prevalence_model_version", "uncertainty_status"],
    "species.parquet": ["country", "region_id", "species", "record_type", "positive", "examined", "year",
                        "source_id", "evidence_ids"],
    "efficacy_studies.parquet": ["study_id", "country", "region_id", "drug", "followup_days", "n_patients",
                                 "acpr_percent", "failure_percent", "confidence_interval_lower",
                                 "confidence_interval_upper", "prediction_interval_lower",
                                 "prediction_interval_upper", "heterogeneity_i2", "study_count", "year_range",
                                 "source_id", "evidence_ids"],
    "marker_observations.parquet": ["country", "region_id", "marker", "year", "n_tested", "n_mutant", "frequency",
                                    "confidence_interval_lower", "confidence_interval_upper", "source_id",
                                    "evidence_ids"],
    "marker_trends.parquet": ["marker", "country", "year", "observed_frequency", "predicted_frequency", "n_tested",
                              "observed_ci_lower", "observed_ci_upper", "validation_method", "source_id",
                              "evidence_ids"],
    "evidence.parquet": ["evidence_id", "source_name", "source_url", "publication_year", "accessed_at", "license",
                         "evidence_type", "country", "limitations"],
}
API_CONTRACT["efficacy_pooled.parquet"] = API_CONTRACT["efficacy_studies.parquet"]


@pytest.mark.parametrize("name", sorted(API_CONTRACT))
def test_api_contract_fields(name):
    import geopandas as gpd
    d = gpd.read_file(P / name) if name.endswith(".geojson") else pd.read_parquet(P / name)
    missing = [c for c in API_CONTRACT[name] if c not in d.columns]
    assert not missing, f"{name} missing API fields {missing}"


def test_model_outputs_carry_generation_time_and_methods():
    import pyarrow.parquet as pq
    for f in ("prevalence_district.parquet", "prevalence_uncertainty.parquet", "pop_at_risk.parquet"):
        meta = json.loads(pq.read_schema(P / f).metadata[b"malaria_watchai"])
        for k in ("model_name", "model_version", "prediction_year", "generated_at", "evaluation_method",
                  "uncertainty_method"):
            assert k in meta, (f, k)
        assert "generated_at" in pd.read_parquet(P / f).columns


CLASSIFIED = ["surveys.parquet", "prevalence_grid.parquet", "prevalence_district.parquet",
              "prevalence_uncertainty.parquet", "pop_at_risk.parquet", "species.parquet",
              "efficacy_studies.parquet", "efficacy_pooled.parquet", "marker_observations.parquet",
              "marker_trends.parquet", "marker_predictions.parquet", "survey_priority.parquet",
              "evidence.parquet"]


@pytest.mark.parametrize("name", CLASSIFIED)
def test_data_classification_present(name):
    """DATA.md section 4: every output says whether its data is observed or modelled."""
    d = pd.read_parquet(P / name)
    assert "data_classification" in d.columns
    vals = set(d["data_classification"].dropna())
    assert vals and all(v.split(" ")[0] in {"observed", "modelled"} for v in vals), vals
    assert not any("synthetic" in v for v in vals)


def test_prevalence_classification_matches_source_type():
    d = pd.read_parquet(P / "prevalence_district.parquet")
    assert (d["data_classification"] == d["source_type"]).all()


def test_licence_flags():
    from ml.src.evidence import license_status
    assert license_status("CC BY-NC-SA 3.0 IGO (WHO)").startswith("restricted")
    assert license_status("CC BY 4.0 (WorldPop)").startswith("open")
    assert license_status("VERIFY_LICENSE").startswith("unverified")
    assert license_status("CC BY 4.0; per-record permissions_info applies").startswith("mixed")
    reg = pd.read_parquet(P / "evidence.parquet")
    assert reg["license_status"].notna().all()
