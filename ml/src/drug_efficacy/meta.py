"""DerSimonian-Laird random-effects meta-analysis of proportions (logit scale)."""
from __future__ import annotations

import numpy as np
from scipy.stats import norm, t as student_t


def logit_transform(events, n, cc: float = 0.5):
    """Logit and its variance; continuity correction ``cc`` for 0 or n events."""
    e = np.asarray(events, float)
    n = np.asarray(n, float)
    zero = (e == 0) | (e == n)
    e2 = np.where(zero, e + cc, e)
    n2 = np.where(zero, n + 2 * cc, n)
    y = np.log(e2 / (n2 - e2))
    v = 1.0 / e2 + 1.0 / (n2 - e2)
    return y, v


def dersimonian_laird(y, v, level: float = 0.95) -> dict:
    y = np.asarray(y, float)
    v = np.asarray(v, float)
    k = len(y)
    w = 1.0 / v
    mu_fe = np.sum(w * y) / np.sum(w)
    q = float(np.sum(w * (y - mu_fe) ** 2))
    df = k - 1
    c = np.sum(w) - np.sum(w ** 2) / np.sum(w)
    tau2 = max(0.0, (q - df) / c) if k > 1 and c > 0 else 0.0
    ws = 1.0 / (v + tau2)
    mu = float(np.sum(ws * y) / np.sum(ws))
    se = float(np.sqrt(1.0 / np.sum(ws)))
    z = norm.ppf(0.5 + level / 2)
    i2 = max(0.0, (q - df) / q) if q > 0 and k > 1 else 0.0
    out = {"k": k, "mu": mu, "se": se, "ci": (mu - z * se, mu + z * se), "tau2": float(tau2),
           "q": q, "i2": float(i2), "pi": (None, None)}
    if k >= 3:  # Higgins et al. (2009) prediction interval, t with k-2 df
        tq = student_t.ppf(0.5 + level / 2, k - 2)
        h = tq * np.sqrt(tau2 + se ** 2)
        out["pi"] = (mu - h, mu + h)
    return out


def inv_logit(x):
    return None if x is None else float(1.0 / (1.0 + np.exp(-x)))
