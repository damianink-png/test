"""Dense and coincident interval regression for the conservative X index.

Sparse-only fixtures do not exercise equal starts, nested intervals, or
intervals that touch the tolerance boundary. This is an independent O(N)
oracle: broad-phase may add no false negatives before OCCT Boolean checks.
"""
import random

import numpy as np
import pytest

from dsac29.revision_overlap import _XIntervalIndex


def _bounds(left, right):
    return np.array((left, -1., -1., right, 1., 1.), dtype=float)


@pytest.mark.parametrize("tolerance", [0., 0.01, 0.5])
def test_dense_nested_duplicate_and_touching_intervals(tolerance):
    rng = random.Random(20261104)
    rows = {}
    for i in range(600):
        if i < 100:
            lo, hi = 0., 10.  # coincident definitions / occurrences
        elif i < 200:
            lo, hi = -float(i - 100), float(i - 100)  # nesting
        elif i < 300:
            lo = float(i - 200)
            hi = lo  # degenerate X intervals
        else:
            lo = rng.uniform(-150., 150.)
            hi = lo + rng.uniform(0., 120.)
        rows[i] = _bounds(lo, hi)

    index = _XIntervalIndex(rows)
    queries = [
        _bounds(10. + tolerance, 10. + tolerance),
        _bounds(10. + tolerance + 1e-5, 10. + tolerance + 1e-5),
        _bounds(-150., 150.),
        _bounds(0., 0.),
        _bounds(500., 600.),
    ]
    for _ in range(120):
        lo = rng.uniform(-200., 200.)
        queries.append(_bounds(lo, lo + rng.uniform(0., 40.)))

    for query in queries:
        expected = [
            key for key, bounds in rows.items()
            if bounds[0] <= query[3] + tolerance
            and bounds[3] >= query[0] - tolerance
        ]
        actual = list(index.candidates(query, tolerance))
        assert len(actual) == len(set(actual)), "duplicate occurrence candidate"
        assert set(actual) == set(expected), "lost or invented X candidate"
        assert actual == sorted(actual, key=lambda key: (rows[key][0], rows[key][3], key))
