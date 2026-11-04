"""Large sparse assembly regression for conservative X broad-phase.

The oracle deliberately performs independent linear scanning.  Candidate
enumeration must never silently discard a valid B-Rep pair.
"""
import random

import numpy as np

from dsac29.revision_overlap import _XIntervalIndex


def _box(x0, x1):
    return np.array([x0, -2., -3., x1, 2., 3.], dtype=float)


def test_2500_sparse_parts_with_tolerance_and_extreme_queries():
    rng = random.Random(20261104)
    rows = {i: _box(i * 17. - 21000., i * 17. - 20999.)
            for i in range(2500)}
    index = _XIntervalIndex(rows)
    queries = [_box(-1e9, -1e9), _box(1e9, 1e9),
               _box(-1e9, 1e9), _box(-21000., -21000.),
               _box(21484., 21484.)]
    for _ in range(180):
        x = rng.uniform(-25000., 25000.)
        queries.append(_box(x, x + rng.uniform(0., 70.)))
    for tolerance in (0., 0.01, 0.5):
        for query in queries:
            expected = {key for key, box in rows.items()
                        if box[0] <= query[3] + tolerance
                        and box[3] >= query[0] - tolerance}
            actual = list(index.candidates(query, tolerance))
            assert len(actual) == len(set(actual))
            assert set(actual) == expected
            assert [rows[key][0] for key in actual] == sorted(
                rows[key][0] for key in actual)
