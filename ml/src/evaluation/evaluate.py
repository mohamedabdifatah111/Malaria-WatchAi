"""Cross-validated comparison of baseline and ML prevalence models.

Schemes
  spatial_block_5fold    primary: 100 km blocks, whole blocks held out
  leave_one_adm1_out     each ADM1 region held out in turn
  random_5fold           comparison only - optimistic under spatial autocorrelation

Also calibrates the conformal intervals on spatial-block residuals and reports
cross-conformal coverage.

Outputs
  data/processed/metrics.json
  ml/outputs/oof_predictions.parquet
Run:  python -m ml.src.evaluation.evaluate
"""
from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd

from ml.src import config, io
from ml.src.data.surveys import empirical_logit
from ml.src.evaluation import metrics, spatial_cv
from ml.src.models import uncertainty
from ml.src.models.baseline import IDW, AdminMean
from ml.src.models.lgbm import LGBMPrevalence, feature_list

log = logging.getLogger("ml.evaluate")

MODELS = {"idw": IDW, "adm1_mean": AdminMean, "lightgbm": LGBMPrevalence}


def load_training() -> pd.DataFrame:
    df = pd.read_parquet(config.interim_dir() / "survey_features.parquet")
    return df.reset_index(drop=True)


def oof_predictions(df: pd.DataFrame, folds: np.ndarray) -> pd.DataFrame:
    out = df[["survey_id", "country", "adm1_id", "decade", "year", "prevalence", "emp_logit",
              "examined", "positive", "x_eqd", "y_eqd"]].copy()
    out["fold"] = folds
    for m in MODELS:
        out[f"pred_{m}"] = np.nan
    out["pred_logit"] = np.nan
    out["oof_dist_km"] = np.nan
    for f in sorted(set(folds) - {-1}):
        te = folds == f
        tr = (folds != f) & (folds != -1) if (folds == -1).any() else folds != f
        train, test = df[tr], df[te]
        for name, cls in MODELS.items():
            m = cls().fit(train)
            out.loc[te, f"pred_{name}"] = m.predict(test)
            if name == "lightgbm":
                out.loc[te, "pred_logit"] = m.predict_logit(test)
        out.loc[te, "oof_dist_km"] = uncertainty.nearest_distance_km(
            train[["x_eqd", "y_eqd"]].to_numpy(), test[["x_eqd", "y_eqd"]].to_numpy())
    return out[out["fold"] != -1].copy()


def compare(scheme_metrics: dict) -> dict:
    o = {m: scheme_metrics[m]["overall"] for m in MODELS}
    best = {k: min(o, key=lambda m: o[m][k]) for k in ("mae", "rmse")}
    ml = o["lightgbm"]
    best_base = {k: min(o["idw"][k], o["adm1_mean"][k]) for k in ("mae", "rmse")}
    return {"best_by_mae": best["mae"], "best_by_rmse": best["rmse"],
            "lightgbm_beats_best_baseline_mae": bool(ml["mae"] < best_base["mae"]),
            "lightgbm_beats_best_baseline_rmse": bool(ml["rmse"] < best_base["rmse"]),
            "lightgbm_mae_change_vs_best_baseline": ml["mae"] - best_base["mae"],
            "lightgbm_rmse_change_vs_best_baseline": ml["rmse"] - best_base["rmse"]}


def run() -> dict:
    df = load_training()
    vcfg = config.ml()["validation"]
    ucfg = config.ml()["uncertainty"]
    seed = config.seed()
    schemes = {
        "spatial_block_5fold": spatial_cv.assign_group_folds(
            spatial_cv.block_ids(df["x"], df["y"], vcfg["block_size_km"] * 1000.0), vcfg["n_folds"], seed),
        "leave_one_adm1_out": spatial_cv.leave_one_group_out(df["adm1_id"]),
        "random_5fold": spatial_cv.random_folds(len(df), vcfg["random_split_folds"], seed),
    }
    result = {"description": {
        "target": "PfPR (proportion 0-1) of individual surveys; errors on the prevalence scale",
        "primary_scheme": "spatial_block_5fold",
        "block_size_km": vcfg["block_size_km"],
        "random_5fold_note": "comparison only; optimistic because nearby surveys share train/test",
        "leave_one_adm1_out_note": "adm1_mean degenerates to the country mean when its own ADM1 is held out",
        "n_surveys": int(len(df)), "features": feature_list(),
    }, "schemes": {}}
    oofs = {}
    for name, folds in schemes.items():
        log.info("CV scheme %s (%d folds)", name, len(set(folds) - {-1}))
        oof = oof_predictions(df, np.asarray(folds))
        oofs[name] = oof
        sm = {m: metrics.full_report(oof, "prevalence", f"pred_{m}") for m in MODELS}
        result["schemes"][name] = {"n_folds": int(len(set(folds) - {-1})), "n_tested": int(len(oof)),
                                   "median_oof_distance_km": float(oof["oof_dist_km"].median()),
                                   "models": sm, "comparison": compare(sm)}

    # Conformal calibration on spatial-block residuals.
    sp = oofs["spatial_block_5fold"].copy()
    sp["abs_resid"] = np.abs(sp["emp_logit"] - sp["pred_logit"])
    edges = ucfg["distance_bins_km"]
    survey_bins = uncertainty.fit_bins(sp["abs_resid"], sp["oof_dist_km"], edges, ucfg["alpha"],
                                       ucfg["min_residuals_per_bin"])
    prev_bins = uncertainty.fit_decomposed(
        sp["emp_logit"] - sp["pred_logit"], uncertainty.binomial_logit_var(sp["positive"], sp["examined"]),
        sp["oof_dist_km"], edges, ucfg["alpha"], ucfg["min_residuals_per_bin"],
        examined=sp["examined"].to_numpy())
    cov = uncertainty.cross_coverage_decomposed(sp, edges, ucfg["alpha"], ucfg["min_residuals_per_bin"])
    result["uncertainty"] = {
        "method": ("distance-stratified conformal on spatial-block OOF logit residuals, with survey "
                   "binomial sampling variance separated from model error (method of moments)"),
        "prevalence_interval": {
            "use": "maps, districts, population at risk",
            "bins": prev_bins,
            "coverage": cov,
        },
        "survey_prediction_interval": {
            "use": "range a NEW survey of typical size could show (includes sampling noise)",
            "bins": survey_bins,
            "coverage": uncertainty.cross_conformal_coverage(sp, edges, ucfg["alpha"],
                                                             ucfg["min_residuals_per_bin"]),
        },
    }
    all_oof = pd.concat([o.assign(scheme=k) for k, o in oofs.items()], ignore_index=True)
    io.write_parquet(all_oof, "oof_predictions.parquet", directory=config.outputs_dir())
    io.write_json(result, "metrics.json")
    return result


def summary_table(result: dict) -> pd.DataFrame:
    rows = []
    for s, v in result["schemes"].items():
        for m, r in v["models"].items():
            o = r["overall"]
            rows.append({"scheme": s, "model": m, "n": o["n"], "mae": o["mae"], "rmse": o["rmse"],
                         "spearman": o["spearman"], "bias": o["bias"]})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    r = run()
    with pd.option_context("display.width", 140, "display.precision", 4):
        print(summary_table(r).to_string(index=False))
    u = r["uncertainty"]
    print(json.dumps({"prevalence_bins": u["prevalence_interval"]["bins"],
                      "prevalence_coverage": u["prevalence_interval"]["coverage"],
                      "survey_pi_coverage": u["survey_prediction_interval"]["coverage"]["overall"],
                      "survey_pi_width": u["survey_prediction_interval"]["coverage"]["mean_width"]}, indent=1))
