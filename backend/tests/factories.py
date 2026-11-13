from django.contrib.gis.geos import MultiPolygon, Polygon
from apps.drug_efficacy.models import DrugEfficacyRecord
from apps.evidence.models import EvidenceSource
from apps.geography.models import Country, Region
from apps.population.models import PopulationAtRisk
from apps.prevalence.models import PrevalenceEstimate
from apps.resistance.models import Marker, MarkerTrend, ResistanceObservation
from apps.species.models import SpeciesRecord


def make_source(evidence_id="E001", **kw):
    data = dict(
        evidence_id=evidence_id, provider="Test provider",
        source_name="Synthetic test dataset", evidence_type="synthetic",
    )
    data.update(kw)
    return EvidenceSource.objects.create(**data)


def make_region(code="KEN", name="Nairobi", level="ADM1", external_id="X1", parent=None, boundary=None):
    return Region.objects.create(
        country=Country.objects.get(code=code), name=name, admin_level=level,
        external_id=external_id, parent=parent, boundary=boundary,
    )


def make_boundary(west=36.7, south=-1.4, east=36.9, north=-1.2, clockwise=False):
    ring = [(west, south), (east, south), (east, north), (west, north), (west, south)]
    if clockwise:
        ring = list(reversed(ring))
    return MultiPolygon(Polygon(ring), srid=4326)


def make_prevalence(region, source, year=2020, estimate=0.12, lower=0.08, upper=0.17,
                    source_type="modelled", model_version="v1", **kw):
    return PrevalenceEstimate.objects.create(
        country=region.country, region=region, year=year, indicator="PfPR",
        estimate=estimate, lower_interval=lower, upper_interval=upper,
        source_type=source_type, model_version=model_version, source=source, **kw,
    )


def make_population(region, source, year=2020, risk_class="low", population=1000, **kw):
    return PopulationAtRisk.objects.create(
        country=region.country, region=region, year=year, risk_class=risk_class,
        population=population, population_source="Test population layer",
        prevalence_model_version="v1", source=source, **kw,
    )


def make_species(region, source, species="P. vivax", record_type="survey", year=2019,
                 positive=10, examined=100, **kw):
    return SpeciesRecord.objects.create(
        country=region.country, region=region, species=species, record_type=record_type,
        year=year, positive=positive, examined=examined, source=source, **kw,
    )


def make_efficacy(region, source, record_type="pooled", drug="AL", followup_days=28, **kw):
    data = dict(
        record_type=record_type, country=region.country, region=region, drug=drug,
        followup_days=followup_days, n_patients=500, acpr_percent=97.5, failure_percent=2.5,
        study_year_start=2015, study_year_end=2019, source=source,
    )
    if record_type == "study":
        data.update(study_id="S1", study_count=None)
    else:
        data.update(
            study_id="", study_count=4, confidence_interval_lower=95.0,
            confidence_interval_upper=99.0, prediction_interval_lower=90.0,
            prediction_interval_upper=99.5, heterogeneity_i2=40.0,
        )
    data.update(kw)
    return DrugEfficacyRecord.objects.create(**data)


def make_marker(name="TEST_MARKER_1"):
    return Marker.objects.create(name=name)


def make_resistance(region, source, marker, year=2019, n_tested=20, n_mutant=5):
    return ResistanceObservation.objects.create(
        country=region.country, region=region, marker=marker, year=year,
        n_tested=n_tested, n_mutant=n_mutant, source=source,
    )


def make_trend(region, source, marker, year=2019, **kw):
    data = dict(
        country=region.country, region=region, marker=marker, year=year,
        observed_frequency=0.2, predicted_frequency=0.22, n_tested=100,
        confidence_interval_lower=0.15, confidence_interval_upper=0.3,
        validation_method="test holdout", model_version="v1", source=source,
    )
    data.update(kw)
    return MarkerTrend.objects.create(**data)