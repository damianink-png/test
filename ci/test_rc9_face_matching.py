"""Regression: exact face multiset and nonrecursive bijective matching."""
import sys
from pathlib import Path
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dscompare_rc9_manual"))
from dsac29.step_reexport_tolerance import (
    _face_type_orientation_compatible, _perfect_face_owner)

left = [("BSpline", 0)] * 175 + [("BSpline", 1)] * 159
right = [("BSpline", 0)] * 174 + [("BSpline", 1)] * 160
assert not _face_type_orientation_compatible(left, right)
assert _face_type_orientation_compatible(left, left.copy())

# The old recursive matcher can spend >90 s on this dense impossible case.
start = monotonic()
assert _perfect_face_owner([list(range(717)) for _ in range(718)]) is None
assert monotonic() - start < 10.0

for count in (1, 10, 718, 1705):
    options = [list(range(count)) for _ in range(count)]
    owner = _perfect_face_owner(options)
    assert owner is not None and len(owner) == count
    assert len(set(owner.values())) == count
    assert all(j in options[i] for j, i in owner.items())

# Hall's theorem failure and non-greedy augmenting path.
assert _perfect_face_owner([[0], [0]]) is None
owner = _perfect_face_owner([[0, 1], [0]])
assert owner is not None and owner == {1: 0, 0: 1}
print("PASS: strict face-orientation multiset, iterative bijection, dense negatives")
