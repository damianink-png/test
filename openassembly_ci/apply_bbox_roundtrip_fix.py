"""Treat STEP AABB noise as unchanged only after world-face geometry verification.

Never suppress real in-place rotations or design changes based solely on
matching fingerprints, centers or names. Apply after world-face helper patch.
"""
from pathlib import Path
import sys

def apply(root):
    p = Path(root)/"src/openassembly/model.py"
    s = p.read_text(encoding="utf-8")
    old = """    if a.extents and b.extents and not (a.virtual_transform or b.virtual_transform) and any(abs(x-y)>tol for x,y in zip(a.extents,b.extents)):
        return False
"""
    new = """    if (a.extents and b.extents and not (a.virtual_transform or b.virtual_transform)
            and any(abs(x-y)>tol for x,y in zip(a.extents,b.extents))):
        # STEP re-export can alter AABB without moving material. A matching
        # fingerprint and center alone are NOT sufficient evidence: genuine
        # in-place rotations may have both. Require identical world faces.
        if a.fingerprint != b.fingerprint or not _same_world_faces(a,b):
            return False
"""
    if s.count(old) != 1:
        raise RuntimeError("Placement anchor changed; refusing silent patch")
    if 'def _same_world_faces(' not in s:
        raise RuntimeError("Missing world-space geometry verification")
    p.write_text(s.replace(old,new,1),encoding="utf-8")
    print("Guarded bbox roundtrip verification installed")

if __name__ == "__main__":
    apply(sys.argv[1])
