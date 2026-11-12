"""Fold assignment for spatial, grouped and random cross-validation."""
from __future__ import annotations

import numpy as np
import pandas as pd


def block_ids(x, y, size_m: float) -> np.ndarray:
    """Square spatial blocks of ``size_m`` in a projected CRS (metres)."""
    bx = np.floor(np.asarray(x, float) / size_m).astype(np.int64)
    by = np.floor(np.asarray(y, float) / size_m).astype(np.int64)
    return bx * 1_000_003 + by


def assign_group_folds(groups, n_folds: int, seed: int) -> np.ndarray:
    """Assign whole groups to folds, balancing row counts.

    Groups are shuffled (seeded) and then placed largest-first into the fold
    with the fewest rows, so no group is ever split across folds.
    """
    groups = pd.Series(np.asarray(groups))
    sizes = groups.value_counts()
    rng = np.random.default_rng(seed)
    order = sizes.index.to_numpy().copy()
    rng.shuffle(order)
    order = sorted(order, key=lambda g: -sizes[g])  # stable: ties keep shuffled order
    load = np.zeros(n_folds, dtype=int)
    fold_of = {}
    for g in order:
        f = int(np.argmin(load))
        fold_of[g] = f
        load[f] += sizes[g]
    return groups.map(fold_of).to_numpy()


def random_folds(n: int, n_folds: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    f = np.arange(n) % n_folds
    rng.shuffle(f)
    return f


def leave_one_group_out(groups) -> np.ndarray:
    """Each distinct group becomes its own fold (NaN groups -> -1, never tested)."""
    s = pd.Series(np.asarray(groups, dtype=object))
    codes, _ = pd.factorize(s, use_na_sentinel=True)
    return codes
