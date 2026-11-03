"""Conservative spatial broad-phase must match a brute-force interval oracle.

These tests check candidate *completeness*, not B-Rep equivalence.  No
geometric thresholds are changed and no candidate is declared a match.
"""
import random

import numpy as np
import pytest

from dsac29.revision_overlap import _XIntervalIndex


def _bounds(left, right):
    return np.array([left, -1., -1., right, 1., 1.], dtype=float)


def _oracle(rows, query, tolerance):
    return {key for key, box in rows.items()
            if box[0] <= query[3] + tolerance
            and box[3] >= query[0] - tolerance}


@pytest.mark.parametrize("size", [0, 1, 2, 3, 7, 16, 31, 100])
def test_x_index_matches_exhaustive_oracle_with_negative_coordinates(size):
    rng = random.Random(20261103 + size)
    rows = {}
    for index in range(size):
        left = rng.uniform(-1000., 1000.)
        rows[index * 3 + 1] = _bounds(left, left + rng.uniform(0., 80.))
    spatial = _XIntervalIndex(rows)
    for tolerance in (0., 0.01, 0.5):
        for _ in range(80):
            left = rng.uniform(-1100., 1100.)
            query = _bounds(left, left + rng.uniform(0., 100.))
            found = list(spatial.candidates(query, tolerance))
            assert len(found) == len(set(found)), "Duplicate candidates"
            assert set(found) == _oracle(rows, query, tolerance)
            starts = [rows[key][0] for key in found]
            assert starts == sorted(starts)


def test_x_index_includes_exact_tolerance_boundaries_and_touching_boxes():
    rows = {1: _bounds(-10., -5.), 2: _bounds(0., 2.),
            3: _bounds(2.01, 4.), 4: _bounds(100., 101.)}
    spatial = _XIntervalIndex(rows)
    query = _bounds(2., 2.)
    assert set(spatial.candidates(query, 0.)) == {2}
    # Construct the boundary using the exact same arithmetic as the index.
    boundary = 2. + 0.01
    rows[3] = _bounds(boundary, 4.)
    spatial = _XIntervalIndex(rows)
    assert set(spatial.candidates(query, 0.01)) == {2, 3}
    assert set(spatial.candidates(_bounds(-5., -5.), 0.)) == {1}


def test_x_index_never_returns_nonoverlapping_intervals():
    rows = {i: _bounds(float(i * 10), float(i * 10 + 1))
            for i in range(500)}
    spatial = _XIntervalIndex(rows)
    query = _bounds(1234., 1235.)
    assert set(spatial.candidates(query, 0.01)) == set()
