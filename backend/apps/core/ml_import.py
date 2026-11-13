"""Map ML pipeline outputs (data/processed/*.parquet) onto backend model rows.

Pure Python + pandas, no Django imports, so it is testable without a database.
The `import_ml_outputs` management command resolves the references these rows
carry (country code, region external_id, evidence id, marker name) and writes
them. Every row is checked here against the database constraints in
apps/*/models.py; rows that cannot satisfy them are skipped and counted with a
reason - never altered to fit and never invented.

Reference conventions
  region      ("KEN", "ADM1", "<geoBoundaries shapeID>")  - Region.external_id
  evidence    backend id from evidence.parquet `backend_evidence_id` (E10001...)
  ADM0 rows   skipped: the backend stores country-level values via Country, and
              the Region model holds ADM1/ADM2 only.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

SPECIES = {"P. falciparum", "P. vivax", "P. malariae", "P. ovale", "P. knowlesi"}
RISK_CLASSES = {"very_low", "low", "moderate", "high"}
COUNTRIES = {"KEN", "TZA", "ETH"}
MARKER_INFO = {
    "pfk13_validated": ("pfkelch13", "Any WHO-validated pfkelch13 mutation (WHO 2020 report, Table 4)"),
    "pfk13_candidate": ("pfkelch13", "Any candidate/associated pfkelch13 mutation (WHO 2020 report, Table 4)"),
    "pfcrt_K76T": ("pfcrt", "pfcrt K76T (mixed K/T infections count as carrying the mutant)"),
    "pfmdr1_CNV": ("pfmdr1", "pfmdr1 copy-number amplification"),
}
TABLES = ["evidence", "prevalence_estimate", "prevalence_observation", "population_at_risk", "species",
          "drug_efficacy", "marker", "resistance_observation", "marker_trend"]


def _none(v):
    """NaN / NA -> None; numpy scalars -> python."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v.item() if hasattr(v, "item") else v


def _int_or_none(v):
    v = _none(v)
    if v is None:
        return None
    f = float(v)
    return int(f) if f.is_integer() else None


def _region(country, level, rid):
    rid = _none(rid)
    return None if rid is None else (country, level, str(rid))


class Mapper:
    def __init__(self, processed_dir: Path):
        self.dir = Path(processed_dir)
        self.skipped: dict[str, Counter] = {t: Counter() for t in TABLES}
        reg = pd.read_parquet(self.dir / "evidence.parquet")
        self.registry = reg
        self.backend_id = dict(zip(reg["evidence_id"], reg["backend_evidence_id"]))

    def _skip(self, table, reason):
        self.skipped[table][reason] += 1

    def _ev(self, ml_id):
        return self.backend_id.get(ml_id)

    # ------------------------------------------------------------------ evidence
    def evidence(self) -> list[dict]:
        rows = []
        for _, r in self.registry.iterrows():
            url = _none(r.get("source_url")) or ""
            if not str(url).startswith("http") or len(url) > 500 or " " in url:
                url = ""  # URLField: API query URLs with spaces are kept in DATA_MANIFEST.md instead
            acc = _none(r.get("accessed_at"))
            try:
                acc = date.fromisoformat(str(acc)[:10]) if acc else None
            except ValueError:
                acc = None
            country = _none(r.get("country"))
            lim = r.get("limitations")
            lim = list(lim) if lim is not None and not isinstance(lim, str) else []
            if _none(r.get("license_status")):
                lim = lim + [f"Licence status: {r['license_status']}"]
            if _none(r.get("data_classification")):
                lim = lim + [f"Data classification: {r['data_classification']}"]
            rows.append({
                "evidence_id": r["backend_evidence_id"],
                "provider": str(r.get("provider") or "Unknown - verify")[:200],
                # keep the ML id visible so outputs and the registry can be cross-referenced
                "source_name": f"{r['source_name']} [{r['evidence_id']}]"[:300],
                "source_url": url,
                "publication_year": _int_or_none(r.get("publication_year")),
                "accessed_at": acc,
                "license": str(_none(r.get("license")) or "VERIFY_LICENSE")[:200],
                "evidence_type": r.get("backend_evidence_type") or "other",
                "country_code": country if country in COUNTRIES else "",
                "limitations": lim,
            })
        return rows

    # ---------------------------------------------------------------- prevalence
    def prevalence_estimate(self) -> list[dict]:
        d = pd.read_parquet(self.dir / "prevalence_district.parquet")
        rows = []
        for _, r in d.iterrows():
            t = "prevalence_estimate"
            if r["admin_level"] not in ("ADM1", "ADM2"):
                self._skip(t, "country_level_row")
                continue
            est = _none(r["estimate"])
            lo, hi = _none(r["lower_interval"]), _none(r["upper_interval"])
            if est is None or not 0 <= est <= 1:
                self._skip(t, "estimate_missing_or_out_of_range")
                continue
            if (lo is not None and lo > est) or (hi is not None and hi < est):
                self._skip(t, "interval_does_not_contain_estimate")
                continue
            modelled = r["source_type"] == "modelled"
            ev = r["evidence_ids"][0] if modelled else "MAP-PR-SURVEYS"
            dist = _none(r.get("nearest_survey_distance_km"))
            dens = _none(r.get("survey_density"))
            rows.append({
                "country": r["country"], "region": _region(r["country"], r["admin_level"], r["region_id"]),
                "year": int(r["year"]), "indicator": r["indicator"], "estimate": float(est),
                "lower_interval": lo, "upper_interval": hi, "source_type": r["source_type"],
                "model_version": (r["model_version"] or "") if modelled else "",
                "nearest_survey_distance_km": float(dist) if modelled and dist is not None else None,
                "survey_density": float(dens) if modelled and dens is not None else None,
                "extrapolation_flag": bool(r["extrapolation_flag"]) if modelled else None,
                "reliability_status": (r["reliability_status"] or "") if modelled else "",
                "source": self._ev(ev),
            })
        return rows

    def prevalence_observation(self) -> list[dict]:
        s = pd.read_parquet(self.dir / "surveys.parquet")
        rows = []
        for _, r in s.iterrows():
            t = "prevalence_observation"
            ex, pos = _int_or_none(r["examined"]), _int_or_none(r["positive"])
            if ex is None or pos is None:
                self._skip(t, "non_integer_counts_in_source")
                continue
            lo, hi = _none(r["lower_age"]), _none(r["upper_age"])
            if lo is not None and hi is not None and lo > hi:
                lo = hi = None
                self._skip(t, "age_bounds_reversed_set_null")  # row kept, ages dropped
            src = _none(r["source_id"])
            ev = f"MAP-SRC-{int(src)}" if src is not None else "MAP-PR-SURVEYS"
            rows.append({
                "survey_id": r["survey_id"], "country": r["country"],
                "region": _region(r["country"], "ADM2", r["adm2_id"]),
                "longitude": float(r["longitude"]), "latitude": float(r["latitude"]),
                "survey_year": int(r["year"]), "n_examined": ex, "n_positive": pos,
                "lower_age": lo, "upper_age": hi, "diagnostic_method": str(r["diag_method"])[:100],
                "source": self._ev(ev) or self._ev("MAP-PR-SURVEYS"),
            })
        return rows

    # -------------------------------------------------------- population at risk
    def population_at_risk(self) -> list[dict]:
        p = pd.read_parquet(self.dir / "pop_at_risk.parquet")
        rows = []
        for _, r in p.iterrows():
            t = "population_at_risk"
            if r["admin_level"] not in ("ADM1", "ADM2"):
                self._skip(t, "country_level_row")
                continue
            if r["risk_class"] not in RISK_CLASSES:
                self._skip(t, "unknown_risk_class")
                continue
            rows.append({
                "country": r["country"], "region": _region(r["country"], r["admin_level"], r["region_id"]),
                "year": int(r["year"]), "risk_class": r["risk_class"],
                # modelled estimate rounded to whole persons
                "population": int(round(max(float(r["population"]), 0.0))),
                "population_source": str(r["population_source"])[:200],
                "prevalence_model_version": str(r["prevalence_model_version"])[:100],
                "uncertainty_status": "bounds_scenarios_in_ml_output",
                "source": self._ev(r["evidence_ids"][0]),
            })
        return rows

    # ------------------------------------------------------------------- species
    def species(self) -> list[dict]:
        s = pd.read_parquet(self.dir / "species.parquet")
        rows = []
        for _, r in s.iterrows():
            t = "species"
            if r["species"] not in SPECIES:
                self._skip(t, f"species_not_in_backend_list:{r['species']}")
                continue
            rt = r["record_type"]
            if rt == "survey":
                pos, ex = _int_or_none(r["positive"]), _int_or_none(r["examined"])
                if pos is None or ex is None or pos > ex:
                    self._skip(t, "survey_counts_not_whole_numbers")
                    continue
                year, region, ev = _int_or_none(r["year"]), _region(r["country"], "ADM1", r["region_id"]), \
                    "MAP-PR-SURVEYS"
            elif rt == "presence_only":
                pos = ex = None
                year = _int_or_none(r["year_end"]) or _int_or_none(r["year"])
                region, ev = None, "GBIF-PLASMODIUM"
            else:
                # country_report / survey_report (shares, no case counts) and no_evidence rows have no
                # backend record type; the backend returns insufficient_data when a species has no rows.
                self._skip(t, f"record_type_not_in_backend:{rt}")
                continue
            if year is None:
                self._skip(t, "year_missing")
                continue
            rows.append({"country": r["country"], "region": region, "species": r["species"], "record_type": rt,
                         "year": year, "positive": pos, "examined": ex, "source": self._ev(ev)})
        return rows

    # ------------------------------------------------------------- drug efficacy
    def drug_efficacy(self) -> list[dict]:
        rows = []
        st = pd.read_parquet(self.dir / "efficacy_studies.parquet")
        for _, r in st.iterrows():
            t = "drug_efficacy"
            fu, n = _int_or_none(r["followup_days"]), _int_or_none(r["n_patients"])
            if r["status"] != "ok" or fu is None or not n:
                self._skip(t, "study_excluded_from_pooling")
                continue
            y0, y1 = _int_or_none(r["year_start"]), _int_or_none(r["year_end"])
            if y0 is None or y1 is None or y0 > y1:
                self._skip(t, "study_years_invalid")
                continue
            rows.append(self._eff(r, "study", r["study_id"], _region(r["country"], "ADM1", r["region_id"]),
                                  fu, n, y0, y1, None, self._ev(r["study_id"]),
                                  site=str(_none(r["site_name"]) or "")[:200]))
        po = pd.read_parquet(self.dir / "efficacy_pooled.parquet")
        for _, r in po.iterrows():
            if r["status"] != "ok":
                self._skip("drug_efficacy", "pool_insufficient_studies")
                continue
            y0, y1 = (int(x) for x in str(r["year_range"]).split("-")[:2])
            rows.append(self._eff(r, "pooled", r["study_id"], None, int(r["followup_days"]),
                                  int(round(r["n_patients"])), y0, y1, int(r["study_count"]),
                                  self._ev(r["evidence_ids"][0])))
        return rows

    @staticmethod
    def _eff(r, rtype, study_id, region, fu, n, y0, y1, count, source, site=""):
        def pct(c):  # percent fields must lie in [0, 100] (eff_*_range constraints)
            v = _none(r.get(c))
            return float(v) if v is not None and 0 <= v <= 100 else None
        return {"record_type": rtype, "study_id": study_id, "country": r["country"], "region": region,
                "site": site, "drug": r["drug"], "followup_days": fu, "n_patients": n,
                "acpr_percent": pct("acpr_percent"), "failure_percent": pct("failure_percent"),
                "confidence_interval_lower": pct("confidence_interval_lower"),
                "confidence_interval_upper": pct("confidence_interval_upper"),
                "prediction_interval_lower": pct("prediction_interval_lower"),
                "prediction_interval_upper": pct("prediction_interval_upper"),
                "heterogeneity_i2": pct("heterogeneity_i2"), "study_count": count,
                "study_year_start": y0, "study_year_end": y1, "source": source}

    # ---------------------------------------------------------------- resistance
    def marker(self) -> list[dict]:
        return [{"name": k, "gene": g, "description": d} for k, (g, d) in MARKER_INFO.items()]

    def resistance_observation(self) -> list[dict]:
        o = pd.read_parquet(self.dir / "marker_observations.parquet")
        rows, seen = [], set()
        for _, r in o.iterrows():
            t = "resistance_observation"
            n, k = _int_or_none(r["n_tested"]), _int_or_none(r["n_mutant"])
            if not n or k is None or k > n:
                self._skip(t, "counts_invalid")
                continue
            region = _region(r["country"], "ADM1", r["region_id"])
            key = (r["country"], region, r["marker"], int(r["year"]), r["source_id"])
            if key in seen:
                self._skip(t, "duplicate_country_region_marker_year_source")
                continue
            seen.add(key)
            rows.append({"country": r["country"], "region": region, "marker": r["marker"], "year": int(r["year"]),
                         "n_tested": n, "n_mutant": k, "source": self._ev(r["source_id"])})
        return rows

    def marker_trend(self) -> list[dict]:
        tr = pd.read_parquet(self.dir / "marker_trends.parquet")
        rows = []
        for _, r in tr.iterrows():
            obs, pred = _none(r["observed_frequency"]), _none(r.get("predicted_frequency"))
            if obs is None and pred is None:
                self._skip("marker_trend", "no_value")
                continue
            lo, hi = _none(r["observed_ci_lower"]), _none(r["observed_ci_upper"])
            rows.append({"country": r["country"], "region": None, "marker": r["marker"], "year": int(r["year"]),
                         "observed_frequency": obs, "predicted_frequency": pred,
                         "n_tested": _int_or_none(r["n_tested"]), "confidence_interval_lower": lo,
                         "confidence_interval_upper": hi,
                         "validation_method": str(_none(r.get("validation_method")) or "")[:200],
                         "model_version": "", "source": self._ev(r["evidence_ids"][0])})
        return rows

    # -------------------------------------------------------------------- all
    def build(self) -> dict[str, list[dict]]:
        out = {t: getattr(self, t)() for t in TABLES}
        for t, rows in out.items():
            missing = [r for r in rows if t != "evidence" and t != "marker" and not r.get("source")]
            if missing:
                raise ValueError(f"{t}: {len(missing)} rows cite an evidence id without a backend id")
        return out

    def report(self, built: dict) -> dict:
        return {t: {"rows": len(built[t]), "skipped": dict(self.skipped[t])} for t in TABLES}
