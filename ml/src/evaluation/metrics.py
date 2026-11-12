"""Prevalence error metrics. All inputs and outputs are proportions (0-1)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from ml.src import config


def regression_metrics(obs, pred, weights=None) -> dict:
    obs = np.asarray(obs, dtype=float)
    pred = np.asarray(pred, dtype=float)
    ok = np.isfinite(obs) & np.isfinite(pred)
    obs, pred = obs[ok], pred[ok]
    n = int(len(obs))
    if n == 0:
        return {"n": 0, "mae": None, "rmse": None, "spearman": None, "bias": None, "mae_weighted": None}
    err = pred - obs
    rho = None
    if n >= 3 and np.ptp(obs) > 0 and np.ptp(pred) > 0:
        rho = float(spearmanr(obs, pred).statistic)
    out = {"n": n, "mae": float(np.mean(np.abs(err))), "rmse": float(np.sqrt(np.mean(err ** 2))),
           "spearman": rho, "bias": float(np.mean(err))}
    if weights is not None:
        w = np.asarray(weights, dtype=float)[ok]
        out["mae_weighted"] = float(np.sum(w * np.abs(err)) / np.sum(w))
    return out


def risk_class(p) -> np.ndarray:
    """Map PfPR proportions to risk-class keys (lower bound inclusive)."""
    p = np.asarray(p, dtype=float)
    out = np.full(p.shape, None, dtype=object)
    for rc in config.ml()["risk_classes"]:
        out[(p >= rc["lower"]) & (p < rc["upper"])] = rc["key"]
    return out


def breakdown(df: pd.DataFrame, obs: str, pred: str, by: str, weight: str | None = None) -> dict:
    res = {}
    for k, g in df.groupby(by, dropna=True):
        res[str(k)] = regression_metrics(g[obs], g[pred], g[weight] if weight else None)
    return res


def full_report(df: pd.DataFrame, obs: str, pred: str, weight: str = "examined") -> dict:
    d = df.copy()
    d["_band"] = risk_class(d[obs])
    return {
        "overall": regression_metrics(d[obs], d[pred], d[weight]),
        "by_country": breakdown(d, obs, pred, "country", weight),
        "by_decade": breakdown(d, obs, pred, "decade", weight),
        "by_prevalence_band": breakdown(d, obs, pred, "_band", weight),
    }
