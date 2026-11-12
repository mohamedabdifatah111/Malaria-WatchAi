"""Resistance-marker trends (binomial GLM on year) with held-out validation.

For each marker x country with >= min_years distinct years and >= min_total
tested samples, fit  logit(p) = b0 + b1 * (year - 2010)  by binomial GLM.

Validation (marker_predictions.parquet, held_out_type column):
  recent_year  hold out the latest year; train on earlier years
  region       hold out each ADM1 region-year (other regions still in training)
Baselines: last observed frequency before the held-out point; country average.
Forecast for prediction_year is flagged as extrapolation beyond the data.

Outputs: marker_observations.parquet, marker_trends.parquet, marker_predictions.parquet
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import statsmodels.api as sm

from ml.src import config, io
from ml.src.resistance.markers import MARKERS, observations, wilson_ci

log = logging.getLogger("ml.trends")
YEAR0 = 2010


class UnstableFit(Exception):
    """GLM hit perfect separation or did not converge - slope not identified."""


def fit_glm(years, mutant, tested):
    import warnings

    from statsmodels.tools.sm_exceptions import ConvergenceWarning, PerfectSeparationWarning

    years = np.asarray(years, float)
    X = sm.add_constant(years - YEAR0, has_constant="add")
    y = np.c_[np.asarray(mutant, float), np.asarray(tested, float) - np.asarray(mutant, float)]
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with np.errstate(over="ignore"):
            res = sm.GLM(y, X, family=sm.families.Binomial()).fit()
    if any(issubclass(x.category, (PerfectSeparationWarning, ConvergenceWarning)) for x in w) \
            or not np.all(np.isfinite(res.bse)) or abs(res.params[1]) > 3:
        raise UnstableFit
    return res


def glm_predict(res, years) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = sm.add_constant(np.asarray(years, float) - YEAR0, has_constant="add")
    pr = res.get_prediction(X).summary_frame(alpha=0.05)
    return pr["mean"].to_numpy(), pr["mean_ci_lower"].to_numpy(), pr["mean_ci_upper"].to_numpy()


def _yearly(obs: pd.DataFrame) -> pd.DataFrame:
    return obs.groupby("year")[["n_mutant", "n_tested"]].sum().reset_index()


def trend_table(obs: pd.DataFrame) -> pd.DataFrame:
    r = config.ml()["resistance"]
    rows = []
    for (marker, country), g in obs.groupby(["marker", "country"]):
        yr = _yearly(g)
        lo, hi = wilson_ci(yr["n_mutant"], yr["n_tested"])
        base = pd.DataFrame({"marker": marker, "country": country, "year": yr["year"],
                             "n_tested": yr["n_tested"], "n_mutant": yr["n_mutant"],
                             "observed_frequency": yr["n_mutant"] / yr["n_tested"],
                             "observed_ci_lower": lo, "observed_ci_upper": hi,
                             "sources": "; ".join(sorted(g["source"].unique())),
                             "evidence_ids": [sorted({e for l in g["evidence_ids"] for e in l})] * len(yr)})
        enough = yr["year"].nunique() >= r["min_years_for_trend"] and yr["n_tested"].sum() >= r["min_total_tested_for_trend"]
        varied = 0 < yr["n_mutant"].sum() < yr["n_tested"].sum()
        res = None
        if enough and varied:
            try:
                res = fit_glm(yr["year"], yr["n_mutant"], yr["n_tested"])
            except UnstableFit:
                res = None
        if res is not None:
            m, plo, phi = glm_predict(res, yr["year"])
            base["predicted_frequency"], base["predicted_ci_lower"], base["predicted_ci_upper"] = m, plo, phi
            base["trend_log_odds_per_year"] = float(res.params[1])
            base["trend_p_value"] = float(res.pvalues[1])
            base["status"] = "ok"
            base["validation_method"] = "temporal (latest year held out) and held-out ADM1 region; see marker_predictions"
        else:
            base["status"] = "insufficient_data"
            base["validation_method"] = None
            base["note"] = ("fewer than required years/samples" if not enough
                            else "no variation (all wild type or all mutant) - trend not estimable" if not varied
                            else "unstable fit (perfect separation / implausible slope) - trend not reported")
        rows.append(base)
    t = pd.concat(rows, ignore_index=True)
    t["marker_label"] = t["marker"].map(MARKERS)
    t["interpretation_note"] = "Marker frequency is not a clinical treatment-failure rate."
    return t


def validate(obs: pd.DataFrame) -> pd.DataFrame:
    r = config.ml()["resistance"]
    rows = []
    for (marker, country), g in obs.groupby(["marker", "country"]):
        yr = _yearly(g)
        # recent-year hold-out
        if yr["year"].nunique() >= r["min_years_for_trend"] + 1:
            last = yr["year"].max()
            tr, te = yr[yr["year"] < last], yr[yr["year"] == last].iloc[0]
            res = None
            if 0 < tr["n_mutant"].sum() < tr["n_tested"].sum():
                try:
                    res = fit_glm(tr["year"], tr["n_mutant"], tr["n_tested"])
                except UnstableFit:
                    res = None
            if res is not None:
                pred = float(glm_predict(res, [last])[0][0])
                prev = tr.sort_values("year").iloc[-1]
                rows.append({"marker": marker, "country": country, "region_id": None, "year": int(last),
                             "held_out_type": "recent_year", "n_tested": int(te["n_tested"]),
                             "observed_frequency": te["n_mutant"] / te["n_tested"], "glm_prediction": pred,
                             "baseline_last_observed": prev["n_mutant"] / prev["n_tested"],
                             "baseline_country_average": tr["n_mutant"].sum() / tr["n_tested"].sum()})
        # held-out region-years
        for (reg, y), h in g.groupby(["region_id", "year"]):
            rest = g[g["region_id"] != reg]
            ry = _yearly(rest)
            if ry["year"].nunique() < r["min_years_for_trend"] or not (0 < ry["n_mutant"].sum() < ry["n_tested"].sum()):
                continue
            try:
                res = fit_glm(ry["year"], ry["n_mutant"], ry["n_tested"])
            except UnstableFit:
                continue
            before = ry[(ry["year"] <= y)].sort_values("year")
            rows.append({"marker": marker, "country": country, "region_id": reg, "year": int(y),
                         "held_out_type": "region", "n_tested": int(h["n_tested"].sum()),
                         "observed_frequency": h["n_mutant"].sum() / h["n_tested"].sum(),
                         "glm_prediction": float(glm_predict(res, [y])[0][0]),
                         "baseline_last_observed": (before.iloc[-1]["n_mutant"] / before.iloc[-1]["n_tested"])
                         if len(before) else np.nan,
                         "baseline_country_average": ry["n_mutant"].sum() / ry["n_tested"].sum()})
    v = pd.DataFrame(rows)
    if len(v):
        for c in ("glm_prediction", "baseline_last_observed", "baseline_country_average"):
            v[f"abs_error_{c}"] = (v[c] - v["observed_frequency"]).abs()
    return v


def forecast(trends: pd.DataFrame, obs: pd.DataFrame) -> pd.DataFrame:
    r = config.ml()["resistance"]
    year = r["prediction_year"]
    rows = []
    for (marker, country), g in trends[trends["status"] == "ok"].groupby(["marker", "country"]):
        res = fit_glm(g["year"], g["n_mutant"], g["n_tested"])
        m, lo, hi = glm_predict(res, [year])
        gap = year - int(g["year"].max())
        rows.append({"marker": marker, "country": country, "region_id": None, "year": year,
                     "held_out_type": "forecast", "glm_prediction": float(m[0]),
                     "prediction_ci_lower": float(lo[0]), "prediction_ci_upper": float(hi[0]),
                     "last_data_year": int(g["year"].max()), "extrapolation_years": gap,
                     "status": "extrapolated" if gap > r["max_extrapolation_years"] else "ok",
                     "evidence_ids": g["evidence_ids"].iloc[0]})
    return pd.DataFrame(rows)


def summarise(v: pd.DataFrame) -> dict:
    out = {}
    if v.empty:
        return out
    for kind, g in v.groupby("held_out_type"):
        w = g["n_tested"]
        out[kind] = {"n": int(len(g))}
        for c in ("glm_prediction", "baseline_last_observed", "baseline_country_average"):
            e = g[f"abs_error_{c}"]
            ok = e.notna()
            out[kind][f"mae_{c}"] = float(e[ok].mean()) if ok.any() else None
            out[kind][f"weighted_mae_{c}"] = float((e[ok] * w[ok]).sum() / w[ok].sum()) if ok.any() else None
    return out


def run() -> dict:
    obs, qa = observations()
    cols = ["country", "region_id", "admin_level", "site_name", "marker", "marker_label", "year", "n_tested",
            "n_mutant", "frequency", "confidence_interval_lower", "confidence_interval_upper", "source",
            "source_id", "location_precision", "data_status", "evidence_ids"]
    io.write_parquet(obs[cols], "marker_observations.parquet", {"units": {"frequency": "proportion 0-1"}})
    trends = trend_table(obs)
    io.write_parquet(trends, "marker_trends.parquet")
    val = validate(obs)
    fc = forecast(trends, obs)
    qa["validation"] = summarise(val)
    beats = {k: bool(v.get("mae_glm_prediction") is not None and
                     v["mae_glm_prediction"] < min(x for x in (v.get("mae_baseline_last_observed"),
                                                               v.get("mae_baseline_country_average"))
                                                   if x is not None))
             for k, v in qa["validation"].items()}
    qa["glm_beats_baselines"] = beats
    if len(fc):
        fc["glm_beats_baselines_in_validation"] = all(beats.values()) if beats else False
        fc["status"] = np.where(fc["glm_beats_baselines_in_validation"], fc["status"], "not_recommended")
        fc["note"] = ("GLM forecast shown for transparency; it did not beat the last-observed / "
                      "country-average baselines in validation, so prefer the latest observed frequency.")
    preds = pd.concat([val, fc], ignore_index=True)
    io.write_parquet(preds, "marker_predictions.parquet")
    qa["trend_status"] = trends.drop_duplicates(["marker", "country"]).groupby("status").size().to_dict()
    return qa


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(json.dumps(run(), indent=1, default=str))
