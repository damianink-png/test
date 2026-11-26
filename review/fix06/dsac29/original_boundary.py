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


def _planar_surface_equal(a, b, tolerance):
    """Prove an oriented graph over a plane without matching UV frames."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_BSplineSurface

    if any(int(face.Orientation()) not in (0, 1) for face in (a, b)):
        return False
    left, right = BRepAdaptor_Surface(a), BRepAdaptor_Surface(b)
    if left.GetType() != GeomAbs_Plane:
        a, b = b, a
        left, right = right, left
    if left.GetType() != GeomAbs_Plane:
        return False

    plane = left.Plane()
    axes = plane.Position()
    normal = np.cross(axes.XDirection().Coord(), axes.YDirection().Coord())
    if int(a.Orientation()) == 1:
        normal = -normal
    if right.GetType() == GeomAbs_Plane:
        us = (right.FirstUParameter(), right.LastUParameter())
        vs = (right.FirstVParameter(), right.LastVParameter())
        poles = np.array([[right.Value(u, v).Coord() for v in vs] for u in us])
    elif right.GetType() == GeomAbs_BSplineSurface:
        spline = right.BSpline()
        if ((spline.UDegree(), spline.VDegree(), spline.NbUPoles(), spline.NbVPoles()) != (1, 1, 2, 2)
                or spline.NbUKnots() != 2 or spline.NbVKnots() != 2
                or spline.IsUPeriodic() or spline.IsVPeriodic()
                or spline.IsURational() or spline.IsVRational()):
            return False
        poles = np.array([[spline.Pole(u, v).Coord() for v in (1, 2)] for u in (1, 2)])
    else:
        return False

    # A bilinear patch is inside the hull of its poles. Its projected
    # Jacobian is affine in UV, so strict agreement at all four corners
    # proves the projection is oriented and one-to-one over the whole patch.
    if not np.isfinite(poles).all() or np.max(np.abs((poles - plane.Location().Coord()) @ normal)) > tolerance:
        return False
    du = poles[1] - poles[0]
    dv = poles[:, 1] - poles[:, 0]
    if int(b.Orientation()) == 1:
        normal = -normal
    jacobian = np.cross(du[:, None, :], dv[None, :, :]) @ normal
    scale = np.linalg.norm(du, axis=1)[:, None] * np.linalg.norm(dv, axis=1)[None, :]
    return bool(np.all(jacobian > 1e-10 * scale))


def surface_equal(a,b,tolerance,cache=None):
    from .cylindrical_boundary import equivalent as cylinder_equal
    from .nurbs_orientation import oriented_surface_equal
    if not np.isfinite(tolerance) or tolerance<=0:return False
    try:
        if _planar_surface_equal(a, b, tolerance) or cylinder_equal(a, b, tolerance):
            return True
    except Exception:
        pass  # The existing bounded UV proof can still verify this pair.
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
    from .cylindrical_boundary import circular_edge_equal
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
    options=[]
    for index,f in enumerate(fa):
        dc=np.linalg.norm(centers-f[3],axis=1);db=np.max(np.abs(boxes-f[4]),axis=1)
        candidates=np.flatnonzero(np.minimum(dc,db)<=max(.03,3*tolerance))
        if not len(candidates):return False
        options.append(sorted(map(int,candidates),key=lambda j:min(dc[j],db[j])))
    from .boundary_work import verified_face_owner
    attempted=0
    first_rejections={}
    def verify(i,j):
        nonlocal attempted
        attempted+=1
        if attempted==1 or attempted%16==0:
            report(f'original_boundary_face_{i+1}_of_{len(fa)}_candidate_{j+1}_attempt_{attempted}')
        stage='face_precheck'
        def cached_surface(left,right,tol):
            nonlocal stage
            stage='surface'
            matched=surface_equal(left,right,tol,cache)
            if matched:stage='trims'
            return matched
        matched=prove(faces_a[i],faces_b[j],{0:0},[fa[i]],tolerance,
                      strict_repair=False,allow_original_micro_degenerate=True,
                      surface_prover=cached_surface,edge_prover=circular_edge_equal)
        if not matched:first_rejections.setdefault(stage,(i,j))
        return matched
    owner=verified_face_owner(options,verify)
    if owner is None:
        for stage,(i,j) in first_rejections.items():
            report(f'original_boundary_candidate_rejected_{stage} A[{i+1}] {fa[i][0]} / B[{j+1}] {fb[j][0]}')
        return False
    # Matching uses only fully verified face/wire pairs. A greedy geometric
    # choice cannot hide a valid alternate correspondence between near faces.
    report('original_boundary_proven')
    return True
