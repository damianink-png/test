"""Avoid false 'moved' results from STEP round-trip bbox tessellation noise.

Only the strict fingerprint path is relaxed. Geometry and orientation checks
remain unchanged; actual centroid displacement still means moved.
"""
from pathlib import Path
import sys

def apply(root):
    p=Path(root)/"src/openassembly/model.py"
    s=p.read_text(encoding="utf-8")
    old="""    if a.extents and b.extents and not (a.virtual_transform or b.virtual_transform) and any(abs(x-y)>tol for x,y in zip(a.extents,b.extents)):
        return False
"""
    new="""    # AABB is an axis-aligned *measurement*, not a placement transform.
    # OCCT STEP round-trip can alter AABB slightly without moving a solid.
    # For identical geometric fingerprints, matching centers and orientation
    # are sufficient; do not turn bbox noise into a 'moved' classification.
    if (a.fingerprint != b.fingerprint and a.extents and b.extents
            and not (a.virtual_transform or b.virtual_transform)
            and any(abs(x-y)>tol for x,y in zip(a.extents,b.extents))):
        return False
"""
    if s.count(old)!=1: raise RuntimeError("Placement anchor changed; refusing silent patch")
    p.write_text(s.replace(old,new,1),encoding="utf-8")
    print("Strict fingerprint bbox roundtrip fix applied")

if __name__=="__main__":
    apply(sys.argv[1])
