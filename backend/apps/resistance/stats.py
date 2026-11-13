import math

_Z_95 = 1.959963984540054


def wilson_interval(successes, n, z=_Z_95):
    """Wilson score interval for a proportion, computed only from valid counts."""
    if n <= 0 or successes < 0 or successes > n:
        raise ValueError("Counts must satisfy 0 <= successes <= n and n > 0.")
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)