"""Regression: strict 0.01 mm re-export, tighter repair, no false SAME."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dscompare_rc9_manual"))
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf, gp_Vec
from dsac29.geometry import describe
from dsac29.parametric_identity import edge_equal
from dsac29.step_reexport_tolerance import reexport_equivalent_world

tolerance = 0.01
box = BRepPrimAPI_MakeBox(20., 30., 40.).Shape()
a = describe(box, "a", "a")

def moved(dx):
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(dx, 0., 0.))
    return describe(BRepBuilderAPI_Transform(box, trsf, True).Shape(), "b", "b")

def proven(b, *, repair=False, tol=tolerance):
    return reexport_equivalent_world(
        a, b, tol, allow_boolean=False, _repair_boundary_only=repair)

assert proven(moved(0.0))
assert proven(moved(0.003))  # within half of 0.01 mm, full surface/wire proof
assert not proven(moved(0.012))  # outside CAD tolerance: no SAME
assert not proven(moved(0.02))
assert proven(moved(0.0), repair=True, tol=0.005)
assert not proven(moved(0.003), repair=True, tol=0.005)

# Real Voron V2 failed trim had ~0.002788 mm displacement. It is
# larger than the previous 0.00125 mm internal proof limit, but
# smaller than the 0.005 mm half-budget. This checks the analytic
# oriented line-curve predicate, not a volume/mesh shortcut.
line_a = ("line", np.array([0., 0., 0.]), np.array([10., 0., 0.]))
line_b = ("line", np.array([0., 0.002788, 0.]),
          np.array([10., 0.002788, 0.]))
assert not edge_equal(line_a, line_b, tolerance / 8)
assert edge_equal(line_a, line_b, tolerance / 2)
line_bad = ("line", np.array([0., 0.012, 0.]),
            np.array([10., 0.012, 0.]))
assert not edge_equal(line_a, line_bad, tolerance / 2)

# A geometry change >0.01 mm must remain rejected.
changed = describe(BRepPrimAPI_MakeBox(20.02, 30., 40.).Shape(), "changed", "changed")
assert not proven(changed)
# A mocked failed original proof must never be bypassed by the new fallback
# in ordinary Boolean-enabled comparisons (existing R20 regression contract).
from dsac29 import parametric_identity as identity
from dsac29 import step_reexport_tolerance as step
original_prove = identity.prove
original_boolean = step._verified_difference_empty
try:
    identity.prove = lambda *args: False
    step._verified_difference_empty = lambda *args: False
    assert not step.reexport_equivalent_world(a, a, .01, allow_boolean=True)
finally:
    identity.prove = original_prove
    step._verified_difference_empty = original_boolean
print("PASS: half-budget re-export proof, repair strictness, negative geometry")
