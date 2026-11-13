"""Distance-stratified split-conformal prediction intervals.

Calibration residuals are the spatial-block out-of-fold logit residuals
(observed empirical logit - predicted logit). Each residual is tagged with the
distance from its survey to the nearest *training* survey in that fold, so
residuals far from data come from genuinely held-out space.

For a distance bin with lower edge e, the interval half-width q(e) is the
conformal (1 - alpha) quantile of |residual| among calibration points with
distance in that bin; sparse bins borrow from all points at >= e. Widths are
made non-decreasing with distance. Intervals are formed on the logit scale
and back-transformed, so they are asymmetric on the prevalence scale.

Because the observed target includes binomial sampling noise, these are
intervals for a new survey's prevalence - conservative for true prevalence.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ml.src.data.surveys import inv_logit


def nearest_distance_km(train_xy: np.ndarray, query_xy: np.ndarray) -> np.ndarray:
    d, _ = cKDTree(np.asarray(train_xy, float) / 1000.0).query(np.asarray(query_xy, float) / 1000.0, k=1)
    return d


def count_within_km(train_xy: np.ndarray, query_xy: np.ndarray, radius_km: float) -> np.ndarray:
    tree = cKDTree(np.asarray(train_xy, float) / 1000.0)
    return tree.query_ball_point(np.asarray(query_xy, float) / 1000.0, r=radius_km, return_length=True)


def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    s = np.sort(np.asarray(scores, float))
    n = len(s)
    if n == 0:
        return float("inf")
    k = int(np.ceil((n + 1) * (1 - alpha)))
    return float(s[min(k, n) - 1]) if k <= n else float(s[-1])


def bin_index(dist: np.ndarray, edges: list[float]) -> np.ndarray:
    return np.clip(np.searchsorted(np.asarray(edges, float), np.asarray(dist, float), side="right") - 1,
                   0, len(edges) - 1)


def fit_bins(abs_resid, dist, edges: list[float], alpha: float, min_n: int) -> dict:
    abs_resid = np.asarray(abs_resid, float)
    dist = np.asarray(dist, float)
    b = bin_index(dist, edges)
    q, n_used, n_in_bin = [], [], []
    for i, e in enumerate(edges):
        sel = b == i
        n_in_bin.append(int(sel.sum()))
        if sel.sum() < min_n:
            sel = dist >= e
        if sel.sum() < min_n:  # take the min_n farthest points
            order = np.argsort(-dist)[:min_n]
            sel = np.zeros(len(dist), bool)
            sel[order] = True
        q.append(conformal_quantile(abs_resid[sel], alpha))
        n_used.append(int(sel.sum()))
    q = np.maximum.accumulate(np.asarray(q))
    return {"edges_km": list(map(float, edges)), "halfwidth_logit": q.tolist(), "alpha": alpha,
            "n_in_bin": n_in_bin, "n_used": n_used}


def binomial_logit_var(pos, n) -> np.ndarray:
    """Approximate sampling variance of the empirical logit of one survey."""
    pos = np.asarray(pos, float)
    n = np.asarray(n, float)
    return 1.0 / (pos + 0.5) + 1.0 / (n - pos + 0.5)


def _bin_select(b, dist, i, e, min_n):
    sel = b == i
    if sel.sum() < min_n:
        sel = dist >= e
    if sel.sum() < min_n:
        order = np.argsort(-dist)[:min_n]
        sel = np.zeros(len(dist), bool)
        sel[order] = True
    return sel


def fit_decomposed(resid, v_binom, dist, edges: list[float], alpha: float, min_n: int,
                   floor_sd: float = 0.05, examined=None, large_n: int = 500,
                   min_large: int = 30) -> dict:
    """Separate model error from survey sampling noise, then calibrate.

    Per distance bin, model variance = mean(resid^2) - mean(binomial variance)
    (method of moments, floored, non-decreasing with distance). A conformal
    multiplier q is then calibrated on normalised scores
        |resid| / sqrt(sigma_model^2 + v_binom),
    so that  pred +/- q * sqrt(sigma^2 + v)  covers a new survey, and
             pred +/- q * sigma              is the interval for true prevalence.
    """
    resid = np.asarray(resid, float)
    v = np.asarray(v_binom, float)
    dist = np.asarray(dist, float)
    b = bin_index(dist, edges)
    s2, share = [], []
    for i, e in enumerate(edges):
        sel = _bin_select(b, dist, i, e, min_n)
        tot = float(np.mean(resid[sel] ** 2))
        s2.append(max(tot - float(np.mean(v[sel])), floor_sd ** 2))
        share.append(float(np.mean(v[sel]) / tot) if tot > 0 else None)
    s2 = np.maximum.accumulate(np.asarray(s2))
    scores = np.abs(resid) / np.sqrt(s2[b] + v)
    q_all = conformal_quantile(scores, alpha)
    q, q_large, n_large = q_all, None, 0
    # Guard: large surveys (little sampling noise) directly test the interval for
    # true prevalence. If they need a wider multiplier, use it.
    if examined is not None:
        large = np.asarray(examined, float) >= large_n
        n_large = int(large.sum())
        if n_large >= min_large:
            q_large = conformal_quantile(np.abs(resid[large]) / np.sqrt(s2[b[large]]), alpha)
            q = max(q_all, q_large)
    sd = np.sqrt(s2)
    return {"edges_km": list(map(float, edges)), "alpha": alpha, "q_multiplier": q,
            "q_all_surveys": q_all, "q_large_surveys": q_large, "n_large_surveys": n_large,
            "sigma_model_logit": sd.tolist(), "halfwidth_logit": (q * sd).tolist(),
            "sampling_noise_share_of_residual_variance": share}


def intervals(pred_logit, dist, bins: dict) -> tuple[np.ndarray, np.ndarray]:
    q = np.asarray(bins["halfwidth_logit"])[bin_index(dist, bins["edges_km"])]
    pl = np.asarray(pred_logit, float)
    return inv_logit(pl - q), inv_logit(pl + q)


def cross_coverage_decomposed(oof: pd.DataFrame, edges, alpha, min_n, large_n: int = 500) -> dict:
    """Fold-wise coverage of the decomposed intervals (calibrated on other folds only).

    survey_level        |r| <= q*sqrt(sigma^2 + v)  for every survey (target: nominal)
    prevalence_interval |r| <= q*sigma  for surveys with examined >= large_n, where
                        sampling noise is small - a slightly conservative check of
                        the interval used for maps, districts and population at risk.
    """
    r = (oof["emp_logit"] - oof["pred_logit"]).to_numpy()
    v = binomial_logit_var(oof["positive"], oof["examined"])
    dist = oof["oof_dist_km"].to_numpy()
    surv = np.zeros(len(oof), bool)
    prev = np.zeros(len(oof), bool)
    width = np.zeros(len(oof))
    for f in sorted(oof["fold"].unique()):
        cal = (oof["fold"] != f).to_numpy()
        fit = fit_decomposed(r[cal], v[cal], dist[cal], edges, alpha, min_n,
                             examined=oof["examined"].to_numpy()[cal], large_n=large_n)
        t = ~cal
        b = bin_index(dist[t], edges)
        sd = np.asarray(fit["sigma_model_logit"])[b]
        q = fit["q_multiplier"]
        surv[t] = np.abs(r[t]) <= q * np.sqrt(sd ** 2 + v[t])
        prev[t] = np.abs(r[t]) <= q * sd
        pl = oof["pred_logit"].to_numpy()[t]
        width[t] = inv_logit(pl + q * sd) - inv_logit(pl - q * sd)
    large = (oof["examined"] >= large_n).to_numpy()
    d = oof.assign(_s=surv, _p=prev, _w=width, _large=large)
    return {
        "nominal": 1 - alpha,
        "survey_level_coverage": float(surv.mean()),
        "survey_level_by_country": d.groupby("country")["_s"].mean().round(4).to_dict(),
        "prevalence_interval_coverage_large_surveys": float(prev[large].mean()) if large.any() else None,
        "large_survey_threshold_examined": large_n,
        "n_large_surveys": int(large.sum()),
        "prevalence_interval_coverage_large_by_country":
            d[d["_large"]].groupby("country")["_p"].mean().round(4).to_dict(),
        "prevalence_interval_mean_width": float(width.mean()),
    }


def cross_conformal_coverage(oof: pd.DataFrame, edges, alpha, min_n) -> dict:
    """Coverage of fold k when calibrated on the other folds' residuals only."""
    # Primary coverage is checked on the scale the conformal score uses: the
    # continuity-corrected prevalence inv_logit(emp_logit). Raw prevalence of
    # 0 can never fall inside a logit-scale interval, so raw-scale coverage is
    # reported separately and is mechanically lower where zeros are common.
    cov = np.zeros(len(oof), bool)
    cov_raw = np.zeros(len(oof), bool)
    width = np.zeros(len(oof))
    for f in sorted(oof["fold"].unique()):
        cal = oof["fold"] != f
        bins = fit_bins(oof.loc[cal, "abs_resid"], oof.loc[cal, "oof_dist_km"], edges, alpha, min_n)
        t = (~cal).to_numpy()
        lo, hi = intervals(oof.loc[t, "pred_logit"], oof.loc[t, "oof_dist_km"], bins)
        obs_cc = inv_logit(oof.loc[t, "emp_logit"].to_numpy())
        obs = oof.loc[t, "prevalence"].to_numpy()
        cov[t] = (obs_cc >= lo) & (obs_cc <= hi)
        cov_raw[t] = (obs >= lo) & (obs <= hi)
        width[t] = hi - lo
    d = oof.assign(_cov=cov, _w=width, _bin=bin_index(oof["oof_dist_km"], edges))
    res = {"nominal": 1 - alpha, "overall": float(cov.mean()),
           "overall_raw_prevalence_scale": float(cov_raw.mean()),
           "share_zero_positive_surveys": float((oof["prevalence"] == 0).mean()),
           "mean_width": float(width.mean()),
           "by_country": d.groupby("country")["_cov"].mean().round(4).to_dict(),
           "by_distance_bin": {f">={edges[int(k)]:g}km": {"coverage": float(g["_cov"].mean()), "n": int(len(g)),
                                                           "mean_width": float(g["_w"].mean())}
                               for k, g in d.groupby("_bin")}}
    return res
