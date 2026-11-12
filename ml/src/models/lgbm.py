"""LightGBM prevalence model on the empirical-logit scale.

Target   emp_logit = log((y + 0.5) / (n - y + 0.5))
Weights  min(examined, weight_cap)
Output   inverse-logit of the predicted logit, i.e. a PfPR proportion.
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

from ml.src import config
from ml.src.data.surveys import inv_logit


def feature_list() -> list[str]:
    f = list(config.ml()["features"])
    if config.ml().get("include_coordinates"):
        f += ["x", "y"]
    return f


class LGBMPrevalence:
    name = "lightgbm"

    def __init__(self, features: list[str] | None = None, params: dict | None = None, seed: int | None = None):
        self.features = features or feature_list()
        p = dict(config.ml()["lightgbm"])
        p.update(params or {})
        p.update({"random_state": config.seed() if seed is None else seed,
                  "deterministic": True, "force_row_wise": True, "n_jobs": 1})
        self.params = p

    def fit(self, df: pd.DataFrame) -> "LGBMPrevalence":
        self.model = lgb.LGBMRegressor(**self.params)
        self.model.fit(df[self.features].astype(float), df["emp_logit"].astype(float),
                       sample_weight=df["weight"].astype(float))
        return self

    def predict_logit(self, df: pd.DataFrame) -> np.ndarray:
        return self.model.predict(df[self.features].astype(float))

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return inv_logit(self.predict_logit(df))

    def importance(self) -> dict:
        gain = self.model.booster_.feature_importance(importance_type="gain")
        tot = gain.sum() or 1.0
        return {f: float(g / tot) for f, g in sorted(zip(self.features, gain), key=lambda t: -t[1])}
