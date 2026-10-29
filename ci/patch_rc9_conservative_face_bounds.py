"""Do not reject analytic torus/cylinder faces on conservative AABB drift.

Real Trident shifted STEP pair (run 40789984229) had a torus face with
centroid delta 0.000097 mm and area delta 0.000770 mm2, but conservative
face AABB delta 1.42 mm due different STEP parameter/trim bounds. The
second 'db > tolerance and not BSpline' prefilter rejected this valid
candidate even though the original necessary (centroid OR box) condition
passed. Removing ONLY the redundant second filter allows the mandatory
analytic surface + complete oriented wire proof to decide equivalence.

On four actual failed Trident shifted B-Rep pairs, independent proof was
True in 0.66-0.74 s locally. Negative geometry and all material-Boolean
checks remain unchanged. No AABB or centroid can establish SAME.
"""
from pathlib import Path
import ast

p = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual" / "dsac29" / "step_reexport_tolerance.py"
s = p.read_text(encoding="utf-8")
old = "            if db>tolerance and 'BSpline' not in typ:continue\n"
if s.count(old) != 1:
    raise SystemExit(f"Unexpected strict analytic-face bbox rejection ({s.count(old)})")
s = s.replace(old, (
    "            # Conservative analytic-face AABBs can differ after STEP re-export.\n"
    "            # A near centroid admits only a candidate; full face/wire proof follows.\n"))
assert "if dc>tolerance and db>tolerance:continue" in s
assert "if prove(" not in s or "prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=True)" in s
ast.parse(s, filename=str(p))
p.write_text(s, encoding="utf-8")
print("RC9: removed unsound analytic-face AABB rejection; oriented proof mandatory")
