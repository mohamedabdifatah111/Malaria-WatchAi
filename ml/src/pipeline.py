"""Single entry point for the ML pipeline.

    python -m ml.src.pipeline                 # all stages
    python -m ml.src.pipeline --from evaluate # resume from a stage
    python -m ml.src.pipeline --only species efficacy

Prerequisite: raw data from `python -m mal.fetch` (data/raw + data/manifest.csv).
"""
from __future__ import annotations

import argparse
import json
import logging
import time

from ml.src import config, io

log = logging.getLogger("ml.pipeline")


def _surveys():
    from ml.src.data import surveys
    return {k: v["total"] for k, v in surveys.run().items()}


def _features(refresh=False):
    from ml.src.features import build
    qa = build.run(refresh)
    return {"grid_cells": qa["grid_cells"], "population_by_country": qa["grid_population_by_country"]}


def _evaluate():
    from ml.src.evaluation import evaluate
    r = evaluate.run()
    return {s: v["comparison"] for s, v in r["schemes"].items()}


def _predict():
    from ml.src.models import predict
    return predict.run()


def _par():
    from ml.src.models import pop_at_risk
    return {"rows": len(pop_at_risk.run())}


def _priority():
    from ml.src.models import survey_priority
    p = survey_priority.run()
    return {"districts": len(p), "top_by_country": p.groupby("country").head(1)[
        ["country", "region_name"]].to_dict("records")}


def _report():
    from ml.src.evaluation import report
    return report.run()


def _dossiers():
    from ml.src import dossier
    out = {}
    for place in dossier.DEMO_PLACES:
        d = dossier.build(place)
        if d["status"] == "ok":
            dossier.save(d)
            out[place] = d["grounding"]["grounded"]
    if not all(out.values()):
        raise RuntimeError(f"dossier facts not grounded: {out}")
    return out


def _species():
    from ml.src.species import species
    return {"rows": len(species.run())}


def _efficacy():
    from ml.src.drug_efficacy import efficacy
    return efficacy.run()


def _resistance():
    from ml.src.resistance import trends
    return trends.run()


def _evidence():
    from ml.src import evidence
    return evidence.run()


STAGES = {"surveys": _surveys, "features": _features, "evaluate": _evaluate, "predict": _predict,
          "pop_at_risk": _par, "survey_priority": _priority, "species": _species, "efficacy": _efficacy,
          "resistance": _resistance, "evidence": _evidence, "report": _report, "dossiers": _dossiers}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start", choices=list(STAGES))
    ap.add_argument("--only", nargs="+", choices=list(STAGES))
    ap.add_argument("--refresh-covariates", action="store_true")
    a = ap.parse_args(argv)
    names = list(STAGES)
    if a.only:
        names = [n for n in names if n in a.only]
    elif a.start:
        names = names[names.index(a.start):]
    log.info("raw data: %s", config.raw_dir())
    summary = {"run": io.run_metadata(), "stages": {}}
    for n in names:
        t = time.time()
        log.info("== stage %s", n)
        res = STAGES[n](a.refresh_covariates) if n == "features" else STAGES[n]()
        summary["stages"][n] = {"seconds": round(time.time() - t, 1), "result": res}
    io.write_json(summary, "pipeline_run.json", directory=config.outputs_dir())
    print(json.dumps({k: v["seconds"] for k, v in summary["stages"].items()}, indent=1))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        datefmt="%H:%M:%S")
    main()
