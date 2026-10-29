"""Fix false negative world B-Rep proof from tessellation-inflated OCCT bounds.

Trident shift, run 40906508416, rigid A327/B327:
BRepBndLib.Add_s(...,False) Z-max differed by 0.073685 mm despite
AddOptimal_s(...,False,False) agreeing to <1e-9 mm. The old 0.01-mm
candidate gate rejected identical analytic geometry, causing an unnecessary
35-second rigid search timeout. Exact CAD face/trim proof remains mandatory.
"""
from pathlib import Path
import ast

p = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual" / "dsac29" / "step_reexport_tolerance.py"
s = p.read_text(encoding="utf-8")
replacements = (
    ("BRepBndLib.Add_s(f,bound,False)", "BRepBndLib.AddOptimal_s(f,bound,False,False)"),
    ("BRepBndLib.Add_s(a.shape,exact_a,False)", "BRepBndLib.AddOptimal_s(a.shape,exact_a,False,False)"),
    ("BRepBndLib.Add_s(b.shape,exact_b,False)", "BRepBndLib.AddOptimal_s(b.shape,exact_b,False,False)"),
)
for old,new in replacements:
    if s.count(old) != 1:
        raise SystemExit(f"Expected one analytic bounds anchor, found {s.count(old)}: {old}")
    s=s.replace(old,new)
ast.parse(s,filename=str(p))
p.write_text(s,encoding="utf-8")
print("RC9 analytic optimal bounds installed; exact oriented CAD proof retained")
