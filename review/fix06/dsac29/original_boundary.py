"""Prove exporter-independent surfaces while retaining ORIGINAL trimming wires."""
import numpy as np


def surface_equal(a,b,tolerance):
    from OCP.BRep import BRep_Tool
    from OCP.BRepTools import BRepTools
    from OCP.Geom import Geom_RectangularTrimmedSurface
    from OCP.GeomConvert import GeomConvert
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from .nurbs_orientation import oriented_surface_equal
    def surface_face(face):
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
    try:
        x,y=surface_face(a),surface_face(b)
        return x is not None and y is not None and oriented_surface_equal(x,y,tolerance)
    except Exception:
        return False


def equivalent(a,b,tolerance,progress=None):
    from types import SimpleNamespace
    from .brep_safety import is_valid
    from .step_reexport_tolerance import _faces,_perfect_face_owner
    from .parametric_identity import prove
    from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from .parametric_identity import items
    from .same_domain import _count
    if not np.isfinite(tolerance) or tolerance<=0:raise ValueError('Invalid tolerance')
    if not all(is_valid(s) and _count(s,TopAbs_SOLID)==1 for s in (a,b)):return False
    report=progress or (lambda phase:None)
    report('original_boundary_surface_candidates')
    fa,fb=(_faces(SimpleNamespace(shape=s)) for s in (a,b))
    if not fa or len(fa)!=len(fb):return False
    centers=np.array([f[3] for f in fb]);boxes=np.array([f[4] for f in fb])
    faces_a=items(a,TopAbs_FACE,TopoDS.Face_s)
    faces_b=items(b,TopAbs_FACE,TopoDS.Face_s)
    options=[]
    for index,f in enumerate(fa):
        dc=np.linalg.norm(centers-f[3],axis=1);db=np.max(np.abs(boxes-f[4]),axis=1)
        candidates=np.flatnonzero(np.minimum(dc,db)<=max(.03,3*tolerance))
        if not len(candidates):return False
        verified=[]
        for j in sorted(map(int,candidates),key=lambda j:min(dc[j],db[j])):
            if prove(faces_a[index],faces_b[j],{0:0},[f],tolerance,
                     strict_repair=False,allow_original_micro_degenerate=True,
                     surface_prover=surface_equal):verified.append(j)
        if not verified:
            report('original_boundary_unproven_face_'+str(index));return False
        options.append(verified)
    owner=_perfect_face_owner(options)
    if owner is None:return False
    # Matching uses only fully verified face/wire pairs. A greedy geometric
    # choice cannot hide a valid alternate correspondence between near faces.
    report('original_boundary_proven')
    return True
