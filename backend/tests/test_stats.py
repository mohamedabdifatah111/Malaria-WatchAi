import pytest

from apps.resistance.stats import wilson_interval


def test_wilson_midpoint():
    low, high = wilson_interval(50, 100)
    assert low == pytest.approx(0.4038, abs=1e-3)
    assert high == pytest.approx(0.5962, abs=1e-3)


def test_wilson_zero_successes():
    low, high = wilson_interval(0, 10)
    assert low == pytest.approx(0.0, abs=1e-9)
    assert high == pytest.approx(0.2775, abs=1e-3)


@pytest.mark.parametrize("successes,n", [(5, 0), (-1, 10), (11, 10)])
def test_wilson_rejects_invalid_counts(successes, n):
    with pytest.raises(ValueError):
        wilson_interval(successes, n)