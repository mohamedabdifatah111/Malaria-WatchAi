"""Demo-readiness check: run before any demo or after pulling.

    python -m ml.src.smoke

Verifies, without retraining anything, that every output the backend and
frontend use exists, loads, is non-empty, has its key columns, that GeoJSON is
valid EPSG:4326, that the agent lookups answer for the demo places, that the
grounding check runs, and that evidence ids resolve. Exits non-zero on any
failure so it can gate a demo or CI job.
"""
from __future__ import annotations

import json
import sys
import time

import pandas as pd

from ml.src import config

CHECKS: list[tuple[str, bool, str]] = []

PARQUET = {
    "surveys.parquet": ["survey_id", "prevalence", "examined", "evidence_ids"],
    "prevalence_grid.parquet": ["cell_id", "estimate", "lower_interval", "upper_interval", "reliability_status"],
    "prevalence_district.parquet": ["region_id", "estimate", "source_type", "status", "evidence_ids"],
    "prevalence_uncertainty.parquet": ["region_id", "interval_width", "extrapolation_flag"],
    "pop_at_risk.parquet": ["region_id", "risk_class", "population"],
    "species.parquet": ["species", "record_type", "status"],
    "efficacy_studies.parquet": ["study_id", "acpr_percent", "followup_days"],
    "efficacy_pooled.parquet": ["drug", "followup_days", "study_count", "status"],
    "marker_observations.parquet": ["marker", "n_tested", "n_mutant", "frequency"],
    "marker_trends.parquet": ["marker", "observed_frequency", "status"],
    "marker_predictions.parquet": ["marker", "held_out_type"],
    "survey_priority.parquet": ["region_id", "rank_overall", "expected_burden_reduction", "reason"],
    "evidence.parquet": ["evidence_id", "source_name"],
}
GEOJSON = ["prevalence_adm1.geojson", "prevalence_adm2.geojson", "survey_priority_adm2.geojson"]
JSONS = ["metrics.json", "model_metadata.json", "validation_summary.json"]


def check(name: str, fn):
    t = time.time()
    try:
        msg = fn() or ""
        CHECKS.append((name, True, f"{msg} ({time.time() - t:.1f}s)"))
    except Exception as e:  # noqa: BLE001 - report every failure, keep going
        CHECKS.append((name, False, f"{type(e).__name__}: {e}"))


def main() -> int:
    P = config.processed_dir()
    for f, cols in PARQUET.items():
        def _p(f=f, cols=cols):
            if f.endswith("grid.parquet") or f == "surveys.parquet":
                import geopandas as gpd
                d = gpd.read_parquet(P / f)
                assert d.crs is not None and d.crs.to_epsg() == 4326, f"CRS {d.crs}"
            else:
                d = pd.read_parquet(P / f)
            assert len(d) > 0, "empty"
            miss = [c for c in cols if c not in d.columns]
            assert not miss, f"missing columns {miss}"
            return f"{len(d)} rows"
        check(f"parquet {f}", _p)
    for f in GEOJSON:
        def _g(f=f):
            j = json.loads((P / f).read_text(encoding="utf-8"))
            assert j["type"] == "FeatureCollection" and j["features"], "no features"
            crs = j.get("crs", {}).get("properties", {}).get("name", "EPSG:4326")
            assert "4326" in crs or "CRS84" in crs, crs
            return f"{len(j['features'])} features"
        check(f"geojson {f}", _g)
    for f in JSONS:
        check(f"json {f}", lambda f=f: f"{len(json.loads((P / f).read_text(encoding='utf-8')))} keys")

    from ml.src import lookup
    from ml.src.dossier import DEMO_PLACES, build
    for place in DEMO_PLACES:
        def _l(place=place):
            r = lookup.prevalence_lookup(place)
            assert r["status"] == "ok", r["status"]
            d = build(place)
            assert d["grounding"]["grounded"], f"ungrounded numbers {d['grounding']['unsupported']}"
            return f"{d['place']['region_name']}: PfPR {r['results'][0]['value']:.3f}, grounded"
        check(f"lookup+dossier {place}", _l)
    check("lookup unknown place returns not_found",
          lambda: (lookup.prevalence_lookup("Atlantis")["status"] == "not_found") or (_ for _ in ()).throw(
              AssertionError("expected not_found")))

    def _ev():
        from ml.src import evidence
        r = evidence.check_integrity(pd.read_parquet(P / "evidence.parquet"))
        assert r["ok"], r["unknown_ids"]
        return "all evidence ids resolve"
    check("evidence integrity", _ev)

    w = max(len(n) for n, _, _ in CHECKS)
    for n, ok, msg in CHECKS:
        print(f"{'PASS' if ok else 'FAIL'}  {n.ljust(w)}  {msg}")
    failed = [n for n, ok, _ in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
