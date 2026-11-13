from django.conf import settings
from django.db import transaction

from apps.assistant.models import AssistantBrief, AssistantRun
from apps.core.errors import GuardrailRefusal

from .gemini import GeminiConfig, summarise
from .guardrails import check_question
from .tools import execute_tool

PLAN = [
    ("prevalence_lookup", "prevalence"),
    ("species_lookup", "parasite species"),
    ("drug_evidence_lookup", "antimalarial efficacy"),
    ("population_at_risk", "population at risk"),
    ("resistance_lookup", "resistance marker"),
]
MAX_FINDINGS_PER_TOOL = 5
BASE_LIMITATIONS = [
    "This brief only compiles stored, validated records; it does not compute new values.",
    "Modelled estimates are not observed measurements.",
    "This is surveillance decision support, not individual diagnosis, dosing or treatment advice.",
    "Prevalence and population-at-risk lookups use the year 2020.",
]


def _gemini_config():
    return GeminiConfig(
        api_key=getattr(settings, "GEMINI_API_KEY", ""),
        model=getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash"),
        timeout_s=float(getattr(settings, "GEMINI_TIMEOUT_S", 20)),
        enabled=bool(getattr(settings, "ASSISTANT_LLM_ENABLED", True)),
    )


def _where(r):
    return r.get("region_name") or "Country level"


def _statement(tool, r):
    if tool == "prevalence_lookup":
        text = f"{_where(r)} ({r['year']}): {r['source_type']} {r['indicator']} estimate {r['estimate']:.3f}"
        if r["lower_interval"] is not None and r["upper_interval"] is not None:
            text += f" (interval {r['lower_interval']:.3f} to {r['upper_interval']:.3f})"
        return text
    if tool == "species_lookup":
        text = f"{_where(r)}: {r['species']} {r['record_type']} record ({r['year']})"
        if r["positive"] is not None and r["examined"] is not None:
            text += f", {r['positive']} positive of {r['examined']} examined"
        return text
    if tool == "drug_evidence_lookup":
        text = (
            f"{_where(r)}: {r['drug']} {r['record_type']} estimate, {r['followup_days']}-day "
            f"follow-up, PCR-corrected ACPR {r['acpr_percent']:.1f}% ({r['n_patients']} patients"
        )
        if r["study_count"]:
            text += f", {r['study_count']} studies"
        return text + f", {r['year_range']})"
    if tool == "population_at_risk":
        return f"{_where(r)} ({r['year']}): {r['population']:,} people in the {r['risk_class']} risk class"
    return (
        f"{_where(r)}: marker {r['marker']} ({r['year']}), {r['n_mutant']} mutant of "
        f"{r['n_tested']} tested, frequency {r['frequency']:.3f}"
    )


def build_brief(*, country, region, question):
    allowed, reason = check_question(question)
    run = AssistantRun.objects.create(
        question=question,
        guardrail_decision="allowed" if allowed else "refused",
        guardrail_reason=reason,
        country=country.code,
        region=region,
    )
    if not allowed:
        raise GuardrailRefusal(run_id=run.run_id)

    common = {
        "place": region.name if region else country.code,
        "country": country.code,
        "region_id": region.id if region else None,
    }
    findings, uncertainties = [], []
    limitations = list(BASE_LIMITATIONS)
    evidence_ids = set()

    for tool, label in PLAN:
        result = execute_tool(run, tool, **common)
        if result["status"] != "ok":
            if result["status"] == "insufficient_data":
                uncertainties.append(f"No validated {label} evidence is available for this area.")
            else:
                uncertainties.append(f"The {label} lookup could not be completed.")
            continue
        evidence_ids.update(result["evidence_ids"])
        shown = result["records"][:MAX_FINDINGS_PER_TOOL]
        for record in shown:
            findings.append(
                {"topic": label, "statement": _statement(tool, record), "evidence_ids": [record["evidence_id"]]}
            )
        if result["record_count"] > len(shown):
            uncertainties.append(f"Showing {len(shown)} of {result['record_count']} {label} records.")
        for note in result["notes"]:
            if note not in limitations:
                limitations.append(note)

    place_label = region.name if region else country.name
    if findings:
        summary = (
            f"Validated evidence was retrieved for {place_label}. Every statement below is taken "
            "directly from a stored record and cites its evidence identifier."
        )
    else:
        summary = f"There is insufficient validated evidence for {place_label}."

    # Optional Gemini summary: written from the findings only (never the user's
    # question), number-checked, and replaced by the template summary on any failure.
    llm = summarise(_gemini_config(), place_label, findings, uncertainties)
    if llm["used"]:
        summary = llm["summary"]
        limitations.append(
            f"The summary was drafted by Google Gemini ({llm['model']}) from the findings below; every number "
            "in it was checked against the findings. It requires human review."
        )

    grounded = sum(1 for f in findings if f["evidence_ids"])
    grounding = {
        "claims": len(findings),
        "claims_with_evidence": grounded,
        "all_claims_grounded": grounded == len(findings),
        "summary_generation": {k: llm[k] for k in ("provider", "model", "used", "reason", "grounding")},
    }
    content = {
        "summary": summary,
        "findings": findings,
        "evidence_ids": sorted(evidence_ids),
        "uncertainties": uncertainties,
        "limitations": limitations,
    }

    with transaction.atomic():
        brief = AssistantBrief.objects.create(
            run=run, status=AssistantBrief.Status.DRAFT, country=country.code, region=region,
            original_draft=content, **content,
        )
        run.draft_output = content
        run.grounding_result = grounding
        run.save(update_fields=["draft_output", "grounding_result"])
    return brief