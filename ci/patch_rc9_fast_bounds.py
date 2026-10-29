"""Use conservative OCCT AABBs only as fast rejection filters.

AddOptimal_s is expensive for STEP re-exports with hundreds of trimmed
B-Spline faces. A positive SAME or repair verdict still requires the original
full analytic-surface and oriented-trim proof. Tolerance is not relaxed.
"""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1] / "dscompare_rc9_manual" / "dsac29"
expected = {"brep_safety.py": 1, "step_reexport_tolerance.py": 3, "parametric_identity.py": 1}
for name, count in expected.items():
    path = root / name
    source = path.read_text(encoding="utf-8")
    old = "BRepBndLib.AddOptimal_s("
    if source.count(old) != count or source.count(",False,False)") < count:
        raise SystemExit(f"Unexpected AABB source in {name}; refuse patch")
    updated = source.replace(old, "BRepBndLib.Add_s(").replace(",False,False)", ",False)")
    if name == "step_reexport_tolerance.py":
        updated = updated.replace(
            "Exact OCP bounds below are the geometric test instead.",
            "Conservative OCCT bounds below are only a necessary candidate filter; full surface/trim proof is mandatory.")
        updated = updated.replace("report('exact_bounds')", "report('conservative_bounds_prefilter')")
    ast.parse(updated, filename=str(path))
    path.write_text(updated, encoding="utf-8")
print("Fast conservative CAD AABB prefilters installed; strict surface/trim proof unchanged")
