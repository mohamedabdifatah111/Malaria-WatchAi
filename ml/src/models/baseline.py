"""Baseline prevalence models.

IDW        inverse-distance weighting of survey prevalence (k nearest, km)
AdminMean  pooled prevalence (sum positive / sum examined) of training surveys
           in the same ADM1, falling back to country, then all surveys
Both ignore survey year, age band and covariates by design.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from ml.src import config


class IDW:
    name = "idw"

    def __init__(self, k: int | None = None, power: float | None = None):
        c = config.ml()["idw"]
        self.k = int(k or c["k_neighbours"])
        self.power = float(power or c["power"])

    def fit(self, df: pd.DataFrame) -> "IDW":
        xy = np.c_[df["x_eqd"], df["y_eqd"]] / 1000.0
        self.tree = cKDTree(xy)
        self.values = df["prevalence"].to_numpy(dtype=float)
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        q = np.c_[df["x_eqd"], df["y_eqd"]] / 1000.0
        k = min(self.k, len(self.values))
        d, i = self.tree.query(q, k=list(range(1, k + 1)))  # always (n, k)
        d = np.maximum(d, 1e-6)
        w = 1.0 / d ** self.power
        exact = d[:, 0] <= 1e-6
        pred = (w * self.values[i]).sum(axis=1) / w.sum(axis=1)
        # A query at a survey location returns the mean of co-located surveys.
        if exact.any():
            co = d <= 1e-6
            pred[exact] = (self.values[i] * co).sum(axis=1)[exact] / co.sum(axis=1)[exact]
        return pred


class AdminMean:
    name = "adm1_mean"

    def fit(self, df: pd.DataFrame) -> "AdminMean":
        g = df.groupby("adm1_id")[["positive", "examined"]].sum()
        self.adm1 = (g["positive"] / g["examined"]).to_dict()
        c = df.groupby("country")[["positive", "examined"]].sum()
        self.country = (c["positive"] / c["examined"]).to_dict()
        self.overall = float(df["positive"].sum() / df["examined"].sum())
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        a = df["adm1_id"].map(self.adm1)
        c = df["country"].map(self.country)
        return a.fillna(c).fillna(self.overall).to_numpy(dtype=float)
