"""Regression for safe necessary face coverage filtering in RC9.

No B-Rep operations are skipped for a candidate with possible perfect
correspondence. A coverage rejection cannot produce a positive SAME verdict.
"""
import ast
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual"
sys.path.insert(0, str(root))
from dsac29.step_reexport_tolerance import _perfect_face_owner

assert _perfect_face_owner([[0], [0]]) is None
assert _perfect_face_owner([[0], []]) is None
assert _perfect_face_owner([[0, 1], [0, 1], [0, 1]]) is None
assert _perfect_face_owner([[0, 1], [0, 1]]) is not None
assert _perfect_face_owner([[0], [0, 1]]) is not None
assert _perfect_face_owner([[0, 1], [0]]) is not None
assert _perfect_face_owner([[0], [1], [2]]) is not None
assert _perfect_face_owner([[0], [0, 1], [0, 1]]) is None
print("PASS: impossible coverage rejected; valid bijections preserved")
