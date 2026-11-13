import pytest
from django.db import IntegrityError, transaction

from apps.prevalence.models import PrevalenceObservation
from apps.geography.models import Country
from tests.factories import (
    make_efficacy, make_marker, make_population, make_prevalence, make_region,
    make_resistance, make_source, make_species, make_trend,
)


# ---------- prevalence ----------

@pytest.mark.django_db
def test_prevalence_list_and_filters(client):
    source, region = make_source(), make_region()
    make_prevalence(region, source)

    body = client.get("/api/v1/prevalence/?country=KEN&year=2020").json()
    row = body["data"][0]
    assert body["meta"]["data_status"] == "available"
    assert row["country"] == "KEN"
    assert row["region_name"] == "Nairobi"
    assert row["evidence_ids"] == ["E001"]
    assert row["source_type"] == "modelled"
    assert row["status"] == "available"


@pytest.mark.django_db
def test_prevalence_no_data_is_explicit(client):
    body = client.get("/api/v1/prevalence/?country=KEN&year=2019").json()
    assert body["data"] == []
    assert body["meta"]["data_status"] == "no_data"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query", ["year=abc", "year=2020.5", "year=1800", "region_id=0", "country=USA", "source_type=guess"]
)
def test_prevalence_invalid_params(client, query):
    response = client.get(f"/api/v1/prevalence/?{query}")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.django_db
def test_prevalence_uncertainty(client):
    source, region = make_source(), make_region()
    make_prevalence(
        region, source, nearest_survey_distance_km=12.5, survey_density=0.4,
        extrapolation_flag=False, reliability_status="adequate",
    )
    row = client.get("/api/v1/prevalence/uncertainty/").json()["data"][0]
    assert row["interval_width"] == pytest.approx(0.09)
    assert row["nearest_survey_distance_km"] == 12.5
    assert row["extrapolation_flag"] is False


@pytest.mark.django_db
def test_estimate_bounds_enforced():
    source, region = make_source(), make_region()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_prevalence(region, source, estimate=0.1, lower=0.2, upper=0.3)


@pytest.mark.django_db
def test_observation_positive_cannot_exceed_examined():
    source = make_source()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PrevalenceObservation.objects.create(
                survey_id="S1", country=Country.objects.get(code="KEN"), longitude=36.8,
                latitude=-1.3, survey_year=2020, n_examined=10, n_positive=11, source=source,
            )


@pytest.mark.django_db
def test_observation_invalid_coordinates_rejected():
    source = make_source()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PrevalenceObservation.objects.create(
                survey_id="S2", country=Country.objects.get(code="KEN"), longitude=36.8,
                latitude=95.0, survey_year=2020, n_examined=10, n_positive=1, source=source,
            )


# ---------- population at risk ----------

@pytest.mark.django_db
def test_population_at_risk_list(client):
    source, region = make_source(), make_region()
    make_population(region, source, risk_class="high", population=250000)
    body = client.get("/api/v1/population-at-risk/?country=KEN&year=2020").json()
    row = body["data"][0]
    assert row["risk_class"] == "high"
    assert row["population"] == 250000
    assert row["evidence_ids"] == ["E001"]


# ---------- species ----------

@pytest.mark.django_db
def test_species_filter_accepts_full_and_short_names(client):
    source, region = make_source(), make_region()
    make_species(region, source, species="P. vivax")
    make_species(region, source, species="P. falciparum")
    for value in ("Plasmodium vivax", "P. vivax", "plasmodium VIVAX"):
        body = client.get("/api/v1/species/", {"species": value}).json()
        assert [r["species"] for r in body["data"]] == ["P. vivax"]


@pytest.mark.django_db
def test_species_unknown_name_rejected(client):
    assert client.get("/api/v1/species/", {"species": "Plasmodium foo"}).status_code == 400


@pytest.mark.django_db
def test_presence_only_has_no_counts(client):
    source, region = make_source(), make_region()
    make_species(region, source, record_type="presence_only", positive=None, examined=None)
    row = client.get("/api/v1/species/").json()["data"][0]
    assert row["record_type"] == "presence_only"
    assert row["positive"] is None and row["examined"] is None


@pytest.mark.django_db
def test_presence_only_with_counts_rejected():
    source, region = make_source(), make_region()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_species(region, source, record_type="presence_only", positive=1, examined=5)


@pytest.mark.django_db
def test_survey_requires_denominator():
    source, region = make_source(), make_region()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_species(region, source, record_type="survey", positive=None, examined=None)


# ---------- drug efficacy ----------

@pytest.mark.django_db
def test_efficacy_keeps_study_and_pooled_separate(client):
    source, region = make_source(), make_region()
    make_efficacy(region, source, record_type="study")
    make_efficacy(region, source, record_type="pooled")

    pooled = client.get("/api/v1/drugs/efficacy/?record_type=pooled").json()["data"]
    assert len(pooled) == 1
    assert pooled[0]["study_count"] == 4
    assert pooled[0]["study_id"] is None
    assert pooled[0]["year_range"] == "2015-2019"

    study = client.get("/api/v1/drugs/efficacy/?record_type=study").json()["data"]
    assert study[0]["study_id"] == "S1"
    assert study[0]["study_count"] is None


@pytest.mark.django_db
def test_efficacy_followup_not_mixed(client):
    source, region = make_source(), make_region()
    make_efficacy(region, source, followup_days=28)
    make_efficacy(region, source, followup_days=42, study_year_start=2016)
    body = client.get("/api/v1/drugs/efficacy/?drug=al&followup_days=42").json()
    assert [r["followup_days"] for r in body["data"]] == [42]


@pytest.mark.django_db
@pytest.mark.parametrize("query", ["drug=AL;DROP", "followup_days=0", "followup_days=x", "record_type=other"])
def test_efficacy_invalid_params(client, query):
    assert client.get(f"/api/v1/drugs/efficacy/?{query}").status_code == 400


@pytest.mark.django_db
def test_study_requires_id_and_pooled_requires_count():
    source, region = make_source(), make_region()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_efficacy(region, source, record_type="study", study_id="")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_efficacy(region, source, record_type="pooled", study_count=None)


# ---------- resistance ----------

@pytest.mark.django_db
def test_resistance_frequency_computed_from_counts(client):
    source, region = make_source(), make_region()
    make_resistance(region, source, make_marker(), n_tested=20, n_mutant=5)
    row = client.get("/api/v1/resistance/?marker=test_marker_1").json()["data"][0]
    assert row["frequency"] == 0.25
    assert row["confidence_interval_lower"] < 0.25 < row["confidence_interval_upper"]
    assert row["evidence_ids"] == ["E001"]


@pytest.mark.django_db
def test_resistance_unsupported_marker_rejected(client):
    assert client.get("/api/v1/resistance/?marker=NOT_A_MARKER").status_code == 400


@pytest.mark.django_db
def test_resistance_mutant_cannot_exceed_tested():
    source, region = make_source(), make_region()
    marker = make_marker()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_resistance(region, source, marker, n_tested=5, n_mutant=6)


@pytest.mark.django_db
def test_resistance_trends(client):
    source, region = make_source(), make_region()
    make_trend(region, source, make_marker())
    row = client.get("/api/v1/resistance/trends/?country=KEN").json()["data"][0]
    assert row["observed_frequency"] == 0.2
    assert row["predicted_frequency"] == 0.22
    assert row["validation_method"] == "test holdout"


@pytest.mark.django_db
def test_trend_needs_at_least_one_frequency():
    source, region = make_source(), make_region()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_trend(region, source, make_marker(), observed_frequency=None, predicted_frequency=None)


# ---------- docs ----------

@pytest.mark.django_db
def test_openapi_schema_generates(client):
    assert client.get("/api/v1/schema/").status_code == 200