"""Common/Cut worker deadline estimated from topology and spline control points."""
from math import isfinite
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_BezierCurve, GeomAbs_BSplineCurve, GeomAbs_BezierSurface, GeomAbs_BSplineSurface
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS


def material_operation_timeout(old, new, override=None):
    if override is not None:
        limit = float(override)
        if not isfinite(limit) or not 0 < limit <= 900:
            raise ValueError('Nieprawidłowy limit Common/Cut')
        return limit
    # Face trims and spline poles matter even for a single trimmed face.
    # Stop traversing once the maximum allowance has been reached.
    work = 0
    try:
        for shape in (old, new):
            faces = TopExp_Explorer(shape, TopAbs_FACE)
            while faces.More():
                face = TopoDS.Face_s(faces.Current())
                if not BRep_Tool.IsGeometric_s(face):
                    return 240
                surface = BRepAdaptor_Surface(face)
                work += 4
                if surface.GetType() in (GeomAbs_BezierSurface, GeomAbs_BSplineSurface):
                    work += surface.NbUPoles() * surface.NbVPoles()
                if work >= 60000:
                    return 240
                faces.Next()
            edges = TopExp_Explorer(shape, TopAbs_EDGE)
            while edges.More():
                edge = TopoDS.Edge_s(edges.Current())
                edges.Next()
                work += 1
                if BRep_Tool.Degenerated_s(edge):
                    continue
                if not BRep_Tool.IsGeometric_s(edge):
                    return 240
                curve = BRepAdaptor_Curve(edge)
                if curve.GetType() in (GeomAbs_BezierCurve, GeomAbs_BSplineCurve):
                    work += curve.NbPoles()
                if work >= 60000:
                    return 240
    except RuntimeError:
        # Degenerate STEP edges may have no 3D curve. Leave the verdict to OCCT.
        return 240
    if work >= 11000:
        return 180
    if work >= 1000:
        return 120
    return 60
