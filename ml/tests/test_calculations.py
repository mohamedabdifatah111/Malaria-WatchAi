"""Unit tests for calculations and transformations.

All inputs here are small hand-made TEST FIXTURES, not malaria evidence.
"""
import numpy as np
import pandas as pd
import pytest

from ml.src.data.surveys import empirical_logit, flag_drops, inv_logit, normalise_method
from ml.src.drug_efficacy.meta import dersimonian_laird, logit_transform
from ml.src.evaluation import spatial_cv
from ml.src.evaluation.metrics import regression_metrics, risk_class
from ml.src.models import uncertainty
from ml.src.models.baseline import IDW, AdminMean
from ml.src.resistance.markers import classify_k13, k13_mutations, wilson_ci


# ------------------------------------------------------------------ surveys
def test_empirical_logit_finite_at_bounds_and_inverts():
    assert np.isfinite(empirical_logit(0, 50))
    assert np.isfinite(empirical_logit(50, 50))
    assert empirical_logit(25, 50) == pytest.approx(0.0)
    assert inv_logit(empirical_logit(30, 100)) == pytest.approx(30.5 / 101)


def _raw(**over):
    base = dict(location_available=True, malaria_metrics_available=True, pf_pos=5, examined=50,
                latitude=-1.0, longitude=36.0, year_start=2010)
    base.update(over)
    return base


def test_flag_drops_rules_in_order():
    df = pd.DataFrame([
        _raw(),                                  # keep
        _raw(location_available=False),          # withheld
        _raw(examined=0, pf_pos=0),              # examined_not_positive
        _raw(pf_pos=60),                         # positives_invalid
        _raw(pf_pos=-1),                         # positives_invalid
        _raw(year_start=1990),                   # out of period
        _raw(year_start=None),                   # missing year
        _raw(examined=None),                     # missing counts
    ])
    s = flag_drops(df, "pf")
    assert pd.isna(s.iloc[0])
    r = [None if pd.isna(x) else x for x in s]
    assert r == [None, "withheld_by_provider", "examined_not_positive", "positives_invalid",
                 "positives_invalid", "year_missing_or_out_of_period", "year_missing_or_out_of_period",
                 "missing_counts_or_coords"]


def test_normalise_method():
    assert normalise_method("Microscopy") == "microscopy"
    assert normalise_method("RDT") == "rdt"
    assert normalise_method("RDT, confirmed by microscopy") == "rdt_confirmed_microscopy"
    assert normalise_method(None) == "unknown"


# ------------------------------------------------------------------ metrics
def test_regression_metrics_known_values():
    m = regression_metrics([0.1, 0.2, 0.3], [0.2, 0.2, 0.1])
    assert m["mae"] == pytest.approx((0.1 + 0 + 0.2) / 3)
    assert m["rmse"] == pytest.approx(np.sqrt((0.01 + 0 + 0.04) / 3))
    assert m["bias"] == pytest.approx((0.1 + 0 - 0.2) / 3)


def test_risk_class_boundaries_lower_inclusive():
    assert list(risk_class([0.0, 0.0099, 0.01, 0.0999, 0.10, 0.3499, 0.35, 1.0])) == [
        "very_low", "very_low", "low", "low", "moderate", "moderate", "high", "high"]


# ------------------------------------------------------------------ spatial CV
def test_blocks_never_split_across_folds():
    rng = np.random.default_rng(0)
    x, y = rng.uniform(0, 1e6, 500), rng.uniform(0, 1e6, 500)
    b = spatial_cv.block_ids(x, y, 100_000)
    f = spatial_cv.assign_group_folds(b, 5, seed=1)
    assert pd.DataFrame({"b": b, "f": f}).groupby("b")["f"].nunique().max() == 1
    assert set(f) == set(range(5))
    assert (spatial_cv.assign_group_folds(b, 5, seed=1) == f).all()  # deterministic


def test_leave_one_group_out_marks_missing():
    f = spatial_cv.leave_one_group_out(["a", "b", None, "a"])
    assert f[0] == f[3] and f[0] != f[1] and f[2] == -1


# ------------------------------------------------------------------ baselines
def test_idw_exact_at_survey_and_between():
    tr = pd.DataFrame({"x_eqd": [0.0, 10_000.0], "y_eqd": [0.0, 0.0], "prevalence": [0.1, 0.3]})
    m = IDW(k=2, power=2).fit(tr)
    p = m.predict(pd.DataFrame({"x_eqd": [0.0, 5_000.0], "y_eqd": [0.0, 0.0]}))
    assert p[0] == pytest.approx(0.1)
    assert p[1] == pytest.approx(0.2)


def test_admin_mean_falls_back():
    tr = pd.DataFrame({"adm1_id": ["A", "A", "B"], "country": ["K", "K", "K"],
                       "positive": [1, 3, 10], "examined": [10, 10, 20]})
    m = AdminMean().fit(tr)
    p = m.predict(pd.DataFrame({"adm1_id": ["A", "Z", None], "country": ["K", "K", "T"]}))
    assert p[0] == pytest.approx(0.2)
    assert p[1] == pytest.approx(14 / 40)
    assert p[2] == pytest.approx(14 / 40)


# ------------------------------------------------------------------ uncertainty
def test_conformal_quantile_and_coverage_on_gaussian():
    rng = np.random.default_rng(3)
    r = np.abs(rng.normal(size=4000))
    q = uncertainty.conformal_quantile(r[:2000], alpha=0.1)
    assert np.mean(r[2000:] <= q) == pytest.approx(0.9, abs=0.02)


def test_bins_monotone_in_distance():
    rng = np.random.default_rng(4)
    dist = rng.uniform(0, 150, 3000)
    resid = np.abs(rng.normal(scale=1 + dist / 100))
    b = uncertainty.fit_bins(resid, dist, [0, 10, 25, 50, 100], 0.1, 30)
    assert np.all(np.diff(b["halfwidth_logit"]) >= 0)


def test_decomposition_removes_sampling_noise():
    rng = np.random.default_rng(5)
    n = 5000
    v = rng.uniform(0.05, 0.5, n)            # known sampling variance
    resid = rng.normal(scale=np.sqrt(0.64 + v))  # model sd 0.8 + noise
    fit = uncertainty.fit_decomposed(resid, v, np.zeros(n), [0], 0.1, 30)
    assert fit["sigma_model_logit"][0] == pytest.approx(0.8, abs=0.05)


# ------------------------------------------------------------------ meta-analysis
def test_dersimonian_laird_homogeneous_studies():
    y, v = logit_transform([5, 5, 5], [100, 100, 100])
    m = dersimonian_laird(y, v)
    assert m["tau2"] == 0 and m["i2"] == 0
    assert inv_logit(m["mu"]) == pytest.approx(0.05)


def test_dersimonian_laird_matches_hand_calculation():
    y = np.array([0.0, 1.0, 2.0])
    v = np.array([0.1, 0.1, 0.1])
    m = dersimonian_laird(y, v)
    # FE mean 1; Q = 10*(1+0+1) = 20; c = 30 - 300/30 = 20; tau2 = (20-2)/20 = 0.9
    assert m["q"] == pytest.approx(20)
    assert m["tau2"] == pytest.approx(0.9)
    assert m["i2"] == pytest.approx(0.9)
    assert m["mu"] == pytest.approx(1.0)
    assert m["se"] == pytest.approx(np.sqrt(1.0 / 3.0))  # 1/sum(1/(0.1+0.9))


def test_continuity_correction_only_at_bounds():
    y, v = logit_transform([0, 3], [50, 50])
    assert y[0] == pytest.approx(np.log(0.5 / 50.5))
    assert y[1] == pytest.approx(np.log(3 / 47))


# ------------------------------------------------------------------ resistance
def test_wilson_ci_known_value():
    lo, hi = wilson_ci([0], [10])
    assert lo[0] == pytest.approx(0.0)
    assert hi[0] == pytest.approx(0.2775, abs=1e-3)


def test_k13_parsing():
    assert k13_mutations("R539T/C580Y") == {"R539T", "C580Y"}
    assert k13_mutations("Y493H&C580Y") == {"Y493H", "C580Y"}
    assert k13_mutations("a578s,v445i*") == {"A578S", "V445I"}
    assert classify_k13("C580Y") == (True, False)
    assert classify_k13("A578S") == (False, False)     # common African variant, not validated
    assert classify_k13("P441L") == (False, True)
    assert classify_k13(None) == (False, False)


def test_wilson_ci_contains_estimate_exactly_at_bounds():
    lo, hi = wilson_ci([0, 10, 3], [10, 10, 10])
    assert lo[0] == 0.0 and hi[1] == 1.0
    assert (lo <= np.array([0, 1, 0.3])).all() and (hi >= np.array([0, 1, 0.3])).all()
