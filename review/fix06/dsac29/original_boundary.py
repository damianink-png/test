"""Prove exporter-independent surfaces while retaining ORIGINAL trimming wires."""
import numpy as np


def _surface_face(face):
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.Geom import Geom_RectangularTrimmedSurface
    from OCP.GeomConvert import GeomConvert
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace

    bounds=BRepTools.UVBounds_s(face)
    if not all(np.isfinite(v) for v in bounds):return None
    if bounds[0]>=bounds[1] or bounds[2]>=bounds[3]:return None
    # Convert the bounded underlying surface only. Never convert, sew,
    # repair or replace the original face's edges/pcurves.
    trimmed=Geom_RectangularTrimmedSurface(BRep_Tool.Surface_s(face),*bounds)
    spline=GeomConvert.SurfaceToBSplineSurface_s(trimmed)
    builder=BRepBuilderAPI_MakeFace(spline,1e-7)
    if not builder.IsDone():return None
    result=builder.Face();result.Orientation(face.Orientation())
    return result

class SurfaceCache:
    """Operation-local cache, keyed by exact shape, placement and orientation."""
    def __init__(self):self.entries={}
    def get(self,face):
        key=(hash(face),int(face.Orientation()))
        bucket=self.entries.setdefault(key,[])
        for saved,value in bucket:
            if face.IsEqual(saved):return value
        value=_surface_face(face)
        bucket.append((face,value))
        return value


def surface_equal(a,b,tolerance,cache=None):
    from .nurbs_orientation import oriented_surface_equal
    try:
        convert=cache.get if cache is not None else _surface_face
        x,y=convert(a),convert(b)
        return x is not None and y is not None and oriented_surface_equal(x,y,tolerance)
    except Exception:
        return False


def equivalent(a,b,tolerance,progress=None):
    from types import SimpleNamespace
    from .brep_safety import is_valid
    from .step_reexport_tolerance import _faces
    from .parametric_identity import prove
    from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from .parametric_identity import items
    from .same_domain import _count
    if not np.isfinite(tolerance) or tolerance<=0:raise ValueError('Invalid tolerance')
    if not all(is_valid(s) and _count(s,TopAbs_SOLID)==1 for s in (a,b)):return False
    report=progress or (lambda phase:None)
    report('original_boundary_surface_candidates')
    report('original_boundary_face_descriptors_A')
    fa=_faces(SimpleNamespace(shape=a))
    report('original_boundary_face_descriptors_B')
    fb=_faces(SimpleNamespace(shape=b))
    if not fa or len(fa)!=len(fb):return False
    centers=np.array([f[3] for f in fb]);boxes=np.array([f[4] for f in fb])
    faces_a=items(a,TopAbs_FACE,TopoDS.Face_s)
    faces_b=items(b,TopAbs_FACE,TopoDS.Face_s)
    cache=SurfaceCache()
    def cached_surface(a,b,tol):return surface_equal(a,b,tol,cache)
    options=[]
    for index,f in enumerate(fa):
        dc=np.linalg.norm(centers-f[3],axis=1);db=np.max(np.abs(boxes-f[4]),axis=1)
        candidates=np.flatnonzero(np.minimum(dc,db)<=max(.03,3*tolerance))
        if not len(candidates):return False
        options.append(sorted(map(int,candidates),key=lambda j:min(dc[j],db[j])))
    from .boundary_work import verified_face_owner
    attempted=0
    def verify(i,j):
        nonlocal attempted
        attempted+=1
        if attempted==1 or attempted%16==0:
            report(f'original_boundary_face_{i+1}_of_{len(fa)}_candidate_{j+1}_attempt_{attempted}')
        return prove(faces_a[i],faces_b[j],{0:0},[fa[i]],tolerance,
                     strict_repair=False,allow_original_micro_degenerate=True,
                     surface_prover=cached_surface)
    owner=verified_face_owner(options,verify)
    if owner is None:return False
    # Matching uses only fully verified face/wire pairs. A greedy geometric
    # choice cannot hide a valid alternate correspondence between near faces.
    report('original_boundary_proven')
    return True
