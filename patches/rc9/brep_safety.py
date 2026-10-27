"""Copy-only B-Rep repair gated by strict oriented face/wire equivalence.

Never changes source STEP shapes and never establishes SAME from repaired
volumes, bounding boxes, meshes, or heuristics. Called in isolated workers.
"""
from __future__ import annotations
import math

class UnprovenRepair(RuntimeError):
    """Input topology invalid or repair not independently proven."""

def is_valid(shape):
    from OCP.BRepCheck import BRepCheck_Analyzer
    return not shape.IsNull() and bool(BRepCheck_Analyzer(shape).IsValid())

def _deep_copy(shape):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    result=BRepBuilderAPI_Copy(shape,True,False).Shape()
    if result.IsNull() or result.IsSame(shape):
        raise UnprovenRepair('Deep B-Rep copy failed')
    return result

def _shape_fix(candidate,tolerance):
    from OCP.ShapeFix import ShapeFix_Shape
    fixer=ShapeFix_Shape(candidate)
    fixer.SetPrecision(tolerance/8.)
    fixer.SetMaxTolerance(tolerance)
    fixer.Perform()
    return fixer.Shape()

def _wire_fix(candidate,tolerance):
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.ShapeFix import ShapeFix_Wire
    from OCP.ShapeBuild import ShapeBuild_ReShape
    from OCP.TopAbs import TopAbs_FACE,TopAbs_WIRE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    analysis=BRepCheck_Analyzer(candidate)
    replacements=ShapeBuild_ReShape()
    changes=0
    faces=TopExp_Explorer(candidate,TopAbs_FACE)
    while faces.More():
        face=TopoDS.Face_s(faces.Current());faces.Next()
        if analysis.IsValid(face):continue
        wires=TopExp_Explorer(face,TopAbs_WIRE)
        while wires.More():
            wire=TopoDS.Wire_s(wires.Current());wires.Next()
            fixer=ShapeFix_Wire(wire,face,tolerance/8.)
            fixer.SetMaxTolerance(tolerance)
            fixer.SetPrecision(tolerance/8.)
            if fixer.FixSelfIntersection():
                replacements.Replace(wire,fixer.Wire())
                changes+=1
    if not changes:raise UnprovenRepair('No invalid wire could be repaired')
    return _shape_fix(replacements.Apply(candidate),tolerance)

def _strict_original_boundary_proof(original,repaired,tolerance):
    import numpy as np
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from .geometry import describe
    from .step_reexport_tolerance import reexport_equivalent_world
    def bounds(shape):
        bb=Bnd_Box();BRepBndLib.AddOptimal_s(shape,bb,False,False)
        return np.asarray(bb.Get(),dtype=float)
    ba,bb=bounds(original),bounds(repaired)
    if not np.isfinite(ba).all() or not np.isfinite(bb).all():return False
    if np.max(np.abs(ba-bb))>tolerance/8.:return False
    a,b=GProp_GProps(),GProp_GProps()
    BRepGProp.VolumeProperties_s(original,a)
    BRepGProp.VolumeProperties_s(repaired,b)
    va,vb=float(a.Mass()),float(b.Mass())
    if not math.isfinite(va) or not math.isfinite(vb) or va<=0 or vb<=0:return False
    if abs(va-vb)>max(tolerance**3,max(va,vb)*1e-9):return False
    # Original may be invalid; still demand every original oriented trim.
    # This path NEVER invokes the Boolean residual volume shortcut.
    return bool(reexport_equivalent_world(
        describe(original,'original','repair-original'),
        describe(repaired,'repaired','repair-copy'),
        tolerance/2.,allow_boolean=False,_repair_boundary_only=True))

def validated_copy(shape,tolerance=0.01):
    """Return (original,False) or (strictly proven copy,True); else raise."""
    if not 0<float(tolerance)<=.01:
        raise ValueError('Repair tolerance exceeds 0.01 mm CAD limit')
    if shape.IsNull():raise UnprovenRepair('Null input B-Rep')
    if is_valid(shape):return shape,False
    for method in (_shape_fix,_wire_fix):
        try:
            candidate=method(_deep_copy(shape),tolerance)
            if is_valid(candidate) and _strict_original_boundary_proof(shape,candidate,tolerance):
                return candidate,True
        except Exception:
            continue
    raise UnprovenRepair('Invalid B-Rep: no repair with proven original oriented trims')
