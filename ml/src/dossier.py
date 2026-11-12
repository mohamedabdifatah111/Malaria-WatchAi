"""One-call evidence dossier for a place - the backbone of the demo story.

    python -m ml.src.dossier Kisumu            # print + save data/processed/dossiers/kisumu.json
    python -m ml.src.dossier --demo            # build dossiers for the configured demo places

A dossier gathers every lookup for one place (prevalence, population at risk,
species, AL efficacy, resistance markers, survey priority) and adds plain
"key facts". Every key fact is generated from tool values only, carries its
evidence_ids, and the whole fact list is passed through the grounding check -
so a dossier is also a worked example of a grounded briefing input.
"""
from __future__ import annotations

import argparse
import json
import re

import pandas as pd

from ml.src import config, io
from ml.src.grounding import check_brief
from ml.src.lookup import (drug_evidence_lookup, population_at_risk, prevalence_lookup, resistance_lookup,
                           resolve_place, species_lookup, _load, _records)

DEMO_PLACES = ["Kisumu", "Kenya", "Tanzania", "Ethiopia", "Kigoma", "Oromia"]


def _pct(x, d=1):
    return None if x is None else f"{100 * x:.{d}f}%"


def priority_lookup(place: str) -> dict:
    loc = resolve_place(place)
    if not loc:
        return {"status": "not_found", "results": []}
    p = _load("survey_priority.parquet")
    if loc["admin_level"] == "ADM2":
        r = p[p["region_id"] == loc["region_id"]]
    elif loc["admin_level"] == "ADM1":
        r = p[p["parent_id"] == loc["region_id"]].head(5)
    else:
        r = p[p["country"] == loc["country"]].head(5)
    cols = ["region_id", "region_name", "rank_overall", "rank_in_country", "expected_burden_reduction",
            "reason", "evidence_ids"]
    return {"status": "ok" if len(r) else "insufficient_data", "place": loc, "results": _records(r[cols])}


def key_facts(t: dict) -> list[dict]:
    facts = []
    prev = t["prevalence"]
    if prev["status"] == "ok":
        v = prev["results"][0]
        facts.append({"topic": "prevalence", "evidence_ids": v["evidence_ids"],
                      "text": f"Modelled PfPR (ages 2-10) for {v['year']}: {_pct(v['value'])} "
                              f"(90% interval {_pct(v['lower'])} to {_pct(v['upper'])}); "
                              f"reliability: {v['reliability_status']}."})
        obs = prev.get("observed_surveys") or []
        if obs:
            last = obs[-1]
            facts.append({"topic": "observed", "evidence_ids": last["evidence_ids"],
                          "text": f"Most recent open survey data: {last['year']}, {int(last['n_surveys'])} survey(s), "
                                  f"pooled prevalence {_pct(last['value'])}."})
        else:
            facts.append({"topic": "observed", "evidence_ids": [],
                          "text": "No open survey data inside this area."})
    par = t["population_at_risk"]
    if par["status"] == "ok":
        top = sorted(par["results"], key=lambda r: -(r["population"] or 0))[0]
        facts.append({"topic": "population_at_risk", "evidence_ids": top["evidence_ids"],
                      "text": f"Largest PfPR class by population: {top['risk_class_label']} "
                              f"({top['population']:,.0f} people; model-based, not infections)."})
    eff = t["drug_efficacy_AL"]
    pooled = [p for p in eff.get("pooled_country", []) if p["status"] == "ok"]
    for p in pooled:
        facts.append({"topic": "efficacy", "evidence_ids": p["evidence_ids"][:5],
                      "text": f"AL day-{p['followup_days']} PCR-corrected efficacy ({p['country']}): "
                              f"{p['acpr_percent']:.1f}% (95% CI {p['confidence_interval_lower']:.1f} to "
                              f"{p['confidence_interval_upper']:.1f}), {p['study_count']} studies, "
                              f"{p['n_patients']:,.0f} patients, {p['year_range']}."})
    res = t["resistance_pfk13_validated"]
    if res["status"] == "ok" and res["summary"]:
        s = res["summary"][0]
        facts.append({"topic": "resistance", "evidence_ids": s["evidence_ids"][:5],
                      "text": f"WHO-validated pfkelch13 markers: {s['n_mutant']} of {s['n_tested']} samples tested "
                              f"({s['year_min']}-{s['year_max']}), from {s['n_study_years']} study-years. "
                              f"A marker is not treatment failure."})
    else:
        facts.append({"topic": "resistance", "evidence_ids": [],
                      "text": "No pfkelch13 marker data for this area."})
    pri = t["survey_priority"]
    if pri["status"] == "ok" and pri["results"]:
        r = pri["results"][0]
        facts.append({"topic": "survey_priority", "evidence_ids": r["evidence_ids"],
                      "text": f"Survey priority: {r['region_name']} ranks {r['rank_in_country']} in-country "
                              f"({r['reason']})."})
    return facts


def build(place: str) -> dict:
    loc = resolve_place(place)
    if not loc:
        return {"status": "not_found", "place": place}
    tools = {
        "prevalence": prevalence_lookup(place),
        "population_at_risk": population_at_risk(place),
        "species": species_lookup(place),
        "drug_efficacy_AL": drug_evidence_lookup(place, "AL"),
        "resistance_pfk13_validated": resistance_lookup(place, "pfk13_validated"),
        "survey_priority": priority_lookup(place),
    }
    facts = key_facts(tools)
    text = "\n".join(f["text"] for f in facts)
    # Ignore numbers in the fixed wording ("ages 2-10", "90%", "95%", "day-28").
    grounding = check_brief(text, list(tools.values()) + [{"fixed_labels": "2-10 90% 95% day-28 day-42"}])
    return {"status": "ok", "place": loc, "generated_at": io.run_timestamp(),
            "model_version": config.ml()["model_version"], "key_facts": facts,
            "grounding": {k: grounding[k] for k in ("grounded", "n_numbers", "n_weak_matches", "unsupported")},
            "tools": tools,
            "disclaimer": "Research and programme-planning evidence; not for diagnosis or treatment."}


def save(d: dict) -> str:
    out = config.processed_dir() / "dossiers"
    out.mkdir(exist_ok=True)
    name = re.sub(r"[^a-z0-9]+", "_", d["place"]["region_name"].lower()).strip("_")
    io.write_json(d, f"{name}.json", directory=out)
    return str(out / f"{name}.json")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("place", nargs="?")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args(argv)
    places = DEMO_PLACES if a.demo or not a.place else [a.place]
    for p in places:
        d = build(p)
        if d["status"] != "ok":
            print(f"{p}: not found")
            continue
        path = save(d)
        print(f"\n== {d['place']['region_name']} ({d['place']['admin_level']}, {d['place']['country']})"
              f"  grounded={d['grounding']['grounded']}  -> {path}")
        for f in d["key_facts"]:
            print(" -", f["text"])


if __name__ == "__main__":
    main()
