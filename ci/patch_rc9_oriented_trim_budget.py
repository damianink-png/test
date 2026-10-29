"""Allow strict re-export proof to use its allocated 0.01 mm boundary budget.

Previously parametric_identity.prove used tolerance/8 for ALL calls. A real
Voron V2 STEP re-export had a 0.002788 mm trim-edge displacement: the exact
analytic surface and all remaining oriented trims matched, but the internal
0.00125 mm limit caused a false negative and a 90 s Common timeout.

Only normal re-export identity uses tolerance/2 for its independent
surface/trim proof. The other half is reserved for accumulated surface/trim
error. Repair of invalid input B-Reps retains the original tolerance/8
boundary proof. Micro-seam deletion caps stay fixed at tolerance/4 per edge
and tolerance/2 total, independent of the matching budget.

This does not change user tolerance, allow Boolean-free material changes,
or bypass any original face, orientation, wire, or edge assertions.
"""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual" / "dsac29"
p = root / "parametric_identity.py"
s = p.read_text(encoding="utf-8")
changes = [
    ("def prove(a,b,owner,face_data,tolerance):",
     "def prove(a,b,owner,face_data,tolerance,*,strict_repair=False):"),
    ("fa=items(a,TopAbs_FACE,TopoDS.Face_s);fb=items(b,TopAbs_FACE,TopoDS.Face_s);tol=tolerance/8",
     "fa=items(a,TopAbs_FACE,TopoDS.Face_s);fb=items(b,TopAbs_FACE,TopoDS.Face_s);tol=tolerance/(8 if strict_repair else 2)"),
    ("tiny=[k for k,span in enumerate(spans) if span<=tol*2]",
     "tiny=[k for k,span in enumerate(spans) if span<=tolerance/4]"),
    ("if not tiny or len(tiny)>8 or sum(spans[k] for k in tiny)>tol*4:return edges",
     "if not tiny or len(tiny)>8 or sum(spans[k] for k in tiny)>tolerance/2:return edges"),
]
for old, new in changes:
    if s.count(old) != 1:
        raise SystemExit(f"Unexpected parametric proof anchor ({s.count(old)}): {old}")
    s = s.replace(old, new)
s = s.replace(
    "# tol is user tolerance/8; per-edge budget is tolerance/4; aggregate is tolerance/2.",
    "# Micro-edge budgets are independent of the normal/repair proof tolerance.")
ast.parse(s, filename=str(p))
p.write_text(s, encoding="utf-8")

q = root / "step_reexport_tolerance.py"
s = q.read_text(encoding="utf-8")
old = "prove(a.shape,b.shape,owner,fa,tolerance)"
new = "prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=_repair_boundary_only)"
if s.count(old) != 1:
    raise SystemExit(f"Unexpected STEP re-export proof call ({s.count(old)})")
s = s.replace(old, new)
ast.parse(s, filename=str(q))
q.write_text(s, encoding="utf-8")
print("RC9 oriented trim proof: re-export <= tolerance/2; repair remains <= tolerance/8; micro seams capped")
