"""Guarded surface-placement evidence for STEP roundtrip bbox/TopLoc changes."""
from pathlib import Path
import sys

def replace_once(s, old, new, label):
    if s.count(old) != 1:
        raise RuntimeError(f'{label}: expected one anchor, got {s.count(old)}')
    return s.replace(old, new, 1)

def apply(root):
    p = Path(root) / 'src/openassembly/model.py'
    s = p.read_text(encoding='utf-8')
    anchor = 'def _pair_min_distance(old: list[Part], new: list[Part]):'
    helper = '''def _same_world_faces(old: Part, new: Part, tol: float = 0.002) -> bool:
    """Verify actual world-space face placement, not TopLoc/AABB metadata.

    STEP re-export may change AABB and TopLoc without moving any material.
    Exact local fingerprints plus equal centroids are not sufficient: an
    in-place rotation can preserve both. Require matching world-space face
    surface type, area, and center for every face. Fail closed.
    """
    if old.shape is None or new.shape is None:
        return False
    try:
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_FACE
        from OCP.TopoDS import TopoDS
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        from OCP.BRepAdaptor import BRepAdaptor_Surface
        from .stepio import view_shape

        def signature(part):
            result = []
            ex = TopExp_Explorer(view_shape(part), TopAbs_FACE)
            while ex.More():
                face = TopoDS.Face_s(ex.Current())
                prop = GProp_GProps()
                BRepGProp.SurfaceProperties_s(face, prop)
                center = prop.CentreOfMass()
                result.append((int(BRepAdaptor_Surface(face).GetType().value),
                               float(prop.Mass()),
                               (float(center.X()), float(center.Y()), float(center.Z()))))
                if len(result) > 600: return None
                ex.Next()
            return sorted(result, key=lambda item: (item[0], round(item[1], 6),
                                                    *(round(v, 5) for v in item[2])))

        a, b = signature(old), signature(new)
        if a is None or b is None or not a or len(a) != len(b): return False
        for (type_a, area_a, center_a), (type_b, area_b, center_b) in zip(a, b):
            if type_a != type_b or abs(area_a-area_b) > max(1e-5, 1e-6*max(area_a,area_b)):
                return False
            if math.dist(center_a, center_b) > tol:
                return False
        return True
    except Exception:
        return False


'''
    s = replace_once(s, anchor, helper + anchor, 'world-face helper')
    anchor = "    # Some exact-fingerprint parts look 'moved' because STEP rewrites\n"
    addition = '''    # Re-exported STEP may change TopLoc/AABB without changing world faces.
    # Require strong global consensus, identical fingerprints and same center;
    # never classify an in-place rotation as unchanged by centroid alone.
    if (alignment and min(len(a),len(b)) >= 100
            and alignment.matching >= math.ceil(.985 * min(len(a),len(b)))
            and alignment.fingerprint_types >= 20):
        by_id = {p.uid: p for p in b}
        for old in a:
            if old.status != 'moved' or old.match not in by_id: continue
            new = by_id[old.match]
            if (_dist(old,new) <= min(pos_tol,.002)
                    and old.name.casefold() == new.name.casefold()
                    and old.fingerprint == new.fingerprint
                    and _same_world_faces(old,new)):
                old.status = new.status = 'unchanged'
                old.match_quality = new.match_quality = 'world_faces_verified_roundtrip'
    # Some exact-fingerprint parts look 'moved' because STEP rewrites
'''
    s = replace_once(s, anchor, addition, 'moved classification')
    p.write_text(s, encoding='utf-8')
    print('Installed conservative world-space face verification')

if __name__ == '__main__':
    apply(sys.argv[1])
