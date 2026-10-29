"""Regression: faster conservative AABBs cannot establish SAME themselves."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual"
sys.path.insert(0, str(root))
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.geometry import describe
from dsac29.step_reexport_tolerance import reexport_equivalent_world
from dsac29.brep_safety import is_valid

box = BRepPrimAPI_MakeBox(10., 12., 15.).Shape()
identical = BRepPrimAPI_MakeBox(10., 12., 15.).Shape()
shifted = BRepPrimAPI_MakeBox(gp_Pnt(.02, 0, 0), 10., 12., 15.).Shape()
changed = BRepPrimAPI_MakeBox(10.2, 12., 15.).Shape()
assert all(is_valid(s) for s in (box, identical, shifted, changed))
a = describe(box, "a", "a")
assert reexport_equivalent_world(a, describe(identical, "b", "b"), .01, allow_boolean=False)
assert not reexport_equivalent_world(a, describe(shifted, "b", "b"), .01, allow_boolean=False)
assert not reexport_equivalent_world(a, describe(changed, "b", "b"), .01, allow_boolean=False)
source = (root / "dsac29" / "step_reexport_tolerance.py").read_text(encoding="utf-8")
assert "prove(a.shape,b.shape,owner,fa,tolerance)" in source
assert "not allow_boolean and not _repair_boundary_only and " in source
assert "prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=False)" in source
assert "BRepBndLib.AddOptimal_s(" not in source
print("PASS: faster prefilters preserve strict geometric SAME proof")
