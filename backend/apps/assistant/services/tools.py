import logging
import re
import time

from apps.assistant.models import ToolCallLog
from apps.drug_efficacy.models import DrugEfficacyRecord
from apps.population.models import PopulationAtRisk
from apps.prevalence.models import PrevalenceEstimate
from apps.resistance.models import Marker, ResistanceObservation
from apps.species.models import SpeciesRecord

from .places import ToolArgumentError, resolve_scope

logger = logging.getLogger(__name__)

MAX_RECORDS = 50
DRUG_RE = re.compile(r"^[A-Za-z0-9+\-]{1,20}$")


class ToolNotAllowed(Exception):
    """Raised for any tool name outside the allowlist."""


# ---------- argument validation ----------

def _year(value, required=True):
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 1900 <= value <= 2100:
        raise ToolArgumentError("year must be an integer between 1900 and 2100.")
    return value


def _drug(value):
    if not isinstance(value, str) or not DRUG_RE.fullmatch(value):
        raise ToolArgumentError("drug must be a short code such as AL.")
    return value


def _marker(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 50:
        raise ToolArgumentError("marker is invalid.")
    marker = Marker.objects.filter(name__iexact=value).first()
    if marker is None:
        raise ToolArgumentError("Unsupported marker.")
    return marker


# ---------- result building ----------

def _evidence(source):
    return {
        "evidence_id": source.evidence_id,
        "source_name": source.source_name,
        "provider": source.provider,
        "source_url": source.source_url or None,
        "publication_year": source.publication_year,
        "accessed_at": source.accessed_at.isoformat() if source.accessed_at else None,
        "license": source.license,
        "evidence_type": source.evidence_type,
        "limitations": source.limitations,
    }


def _empty(tool, args, message, status="insufficient_data", place=None):
    return {
        "tool": tool, "status": status, "arguments": args, "place": place,
        "records": [], "record_count": 0, "truncated": False,
        "evidence": [], "evidence_ids": [], "notes": [], "message": message,
    }


def _not_found(tool, args):
    return _empty(tool, args, "Place not found within Kenya, Tanzania or Ethiopia.")


def _run_query(tool, args, scope, queryset, to_record, notes):
    total = queryset.count()
    rows = list(queryset[:MAX_RECORDS])
    if not rows:
        return _empty(
            tool, args, "No validated evidence is available for this place and these filters.",
            place=scope.describe(),
        )
    sources = {}
    for row in rows:
        sources[row.source.evidence_id] = row.source
    return {
        "tool": tool, "status": "ok", "arguments": args, "place": scope.describe(),
        "records": [to_record(row) for row in rows],
        "record_count": total, "truncated": total > len(rows),
        "evidence": [_evidence(s) for s in sources.values()],
        "evidence_ids": sorted(sources), "notes": notes, "message": "",
    }


def _region(row):
    return {"region_id": row.region_id, "region_name": row.region.name if row.region else None}


# ---------- tools ----------

def prevalence_lookup(place=None, year=2020, country=None, region_id=None):
    year = _year(year)
    args = {"place": place, "year": year, "country": country, "region_id": region_id}
    scope = resolve_scope(place, country, region_id)
    if scope is None:
        return _not_found("prevalence_lookup", args)
    qs = PrevalenceEstimate.objects.filter(year=year, **scope.filters()).select_related("region", "source")

    def record(r):
        return {
            **_region(r), "year": r.year, "indicator": r.indicator, "estimate": r.estimate,
            "lower_interval": r.lower_interval, "upper_interval": r.upper_interval,
            "source_type": r.source_type, "model_version": r.model_version,
            "evidence_id": r.source.evidence_id,
        }

    return _run_query(
        "prevalence_lookup", args, scope, qs, record,
        ["Modelled estimates are not observed measurements."],
    )


def species_lookup(place=None, country=None, region_id=None):
    args = {"place": place, "country": country, "region_id": region_id}
    scope = resolve_scope(place, country, region_id)
    if scope is None:
        return _not_found("species_lookup", args)
    qs = SpeciesRecord.objects.filter(**scope.filters()).select_related("region", "source")

    def record(r):
        return {
            **_region(r), "species": r.species, "record_type": r.record_type, "year": r.year,
            "positive": r.positive, "examined": r.examined, "evidence_id": r.source.evidence_id,
        }

    return _run_query(
        "species_lookup", args, scope, qs, record,
        ["Species shares are never derived from presence-only records."],
    )


def drug_evidence_lookup(place=None, drug="AL", country=None, region_id=None):
    drug = _drug(drug)
    args = {"place": place, "drug": drug, "country": country, "region_id": region_id}
    scope = resolve_scope(place, country, region_id)
    if scope is None:
        return _not_found("drug_evidence_lookup", args)
    qs = DrugEfficacyRecord.objects.filter(drug__iexact=drug, **scope.filters()).select_related("region", "source")

    def record(r):
        return {
            **_region(r), "record_type": r.record_type, "study_id": r.study_id or None,
            "drug": r.drug, "followup_days": r.followup_days, "n_patients": r.n_patients,
            "acpr_percent": r.acpr_percent, "failure_percent": r.failure_percent,
            "confidence_interval_lower": r.confidence_interval_lower,
            "confidence_interval_upper": r.confidence_interval_upper,
            "prediction_interval_lower": r.prediction_interval_lower,
            "prediction_interval_upper": r.prediction_interval_upper,
            "heterogeneity_i2": r.heterogeneity_i2, "study_count": r.study_count,
            "year_range": r.year_range, "evidence_id": r.source.evidence_id,
        }

    return _run_query(
        "drug_evidence_lookup", args, scope, qs, record,
        [
            "Trial efficacy is not guaranteed real-world effectiveness.",
            "The 10% failure threshold is an interpretation reference, not a treatment recommendation.",
        ],
    )


def population_at_risk(place=None, year=2020, country=None, region_id=None):
    year = _year(year)
    args = {"place": place, "year": year, "country": country, "region_id": region_id}
    scope = resolve_scope(place, country, region_id)
    if scope is None:
        return _not_found("population_at_risk", args)
    qs = PopulationAtRisk.objects.filter(year=year, **scope.filters()).select_related("region", "source")

    def record(r):
        return {
            **_region(r), "year": r.year, "risk_class": r.risk_class, "population": r.population,
            "population_source": r.population_source,
            "prevalence_model_version": r.prevalence_model_version,
            "uncertainty_status": r.uncertainty_status, "evidence_id": r.source.evidence_id,
        }

    return _run_query(
        "population_at_risk", args, scope, qs, record,
        ["Population figures are people living in a risk class, not infected counts."],
    )


def resistance_lookup(place=None, marker=None, year=None, country=None, region_id=None):
    marker_obj = _marker(marker)
    year = _year(year, required=False)
    args = {
        "place": place, "marker": marker_obj.name if marker_obj else None, "year": year,
        "country": country, "region_id": region_id,
    }
    scope = resolve_scope(place, country, region_id)
    if scope is None:
        return _not_found("resistance_lookup", args)
    qs = ResistanceObservation.objects.filter(**scope.filters()).select_related("region", "marker", "source")
    if marker_obj:
        qs = qs.filter(marker=marker_obj)
    if year is not None:
        qs = qs.filter(year=year)

    def record(r):
        low, high = r.confidence_interval()
        return {
            **_region(r), "marker": r.marker.name, "year": r.year, "n_tested": r.n_tested,
            "n_mutant": r.n_mutant, "frequency": r.frequency,
            "confidence_interval_lower": low, "confidence_interval_upper": high,
            "evidence_id": r.source.evidence_id,
        }

    return _run_query(
        "resistance_lookup", args, scope, qs, record,
        ["Marker frequency is not equivalent to clinical treatment failure."],
    )


def guideline_search(query, k=3):
    if not isinstance(query, str) or not 3 <= len(query.strip()) <= 300:
        raise ToolArgumentError("query must be 3 to 300 characters.")
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 10:
        raise ToolArgumentError("k must be an integer between 1 and 10.")
    return _empty(
        "guideline_search", {"query": query.strip(), "k": k},
        "No guideline corpus has been loaded, so no guideline evidence is available.",
    )


TOOL_REGISTRY = {
    "prevalence_lookup": prevalence_lookup,
    "species_lookup": species_lookup,
    "drug_evidence_lookup": drug_evidence_lookup,
    "population_at_risk": population_at_risk,
    "resistance_lookup": resistance_lookup,
    "guideline_search": guideline_search,
}


def execute_tool(run, tool_name, **kwargs):
    """Run an allowlisted tool, log the call, and never leak internal errors."""
    if tool_name not in TOOL_REGISTRY:
        raise ToolNotAllowed(tool_name)

    started = time.monotonic()
    try:
        result = TOOL_REGISTRY[tool_name](**kwargs)
    except ToolArgumentError as exc:
        result = _empty(tool_name, kwargs, str(exc), status="invalid_argument")
    except Exception:
        logger.exception("Assistant tool %s failed", tool_name)
        result = _empty(tool_name, kwargs, "The tool could not be completed.", status="error")
    duration_ms = int((time.monotonic() - started) * 1000)

    ToolCallLog.objects.create(
        run=run, tool_name=tool_name, arguments=kwargs, result=result,
        evidence_ids=result.get("evidence_ids", []), status=result["status"],
        duration_ms=duration_ms,
    )
    return result