"""Regression: analytic-face AABBs are only candidate filters, not SAME."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual"
sys.path.insert(0, str(root))
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.geometry import describe
from dsac29.step_reexport_tolerance import reexport_equivalent_world

source = (root / "dsac29" / "step_reexport_tolerance.py").read_text(encoding="utf-8")
assert "if dc>tolerance and db>tolerance:continue" in source
assert "if db>tolerance and 'BSpline' not in typ:continue" not in source
assert "if not _face_type_orientation_compatible(fa,fb):return False" in source
assert "prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=True)" in source
assert "prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=False)" in source

a = describe(BRepPrimAPI_MakeBox(10., 12., 15.).Shape(), "a", "a")
same = describe(BRepPrimAPI_MakeBox(10., 12., 15.).Shape(), "same", "same")
changed = describe(BRepPrimAPI_MakeBox(10.2, 12., 15.).Shape(), "changed", "changed")
shifted = describe(BRepPrimAPI_MakeBox(gp_Pnt(.02, 0, 0), 10., 12., 15.).Shape(), "shifted", "shifted")
assert reexport_equivalent_world(a, same, .01, allow_boolean=False)
assert not reexport_equivalent_world(a, changed, .01, allow_boolean=False)
assert not reexport_equivalent_world(a, shifted, .01, allow_boolean=False)
print("PASS: conservative face candidate only, full oriented proof and negative geometry")
