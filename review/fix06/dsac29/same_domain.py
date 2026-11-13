"""Exporter-independent analytic boundary normalization in isolated workers.

Unification removes redundant same-domain seams, never aligns either operand.
Original shapes are copied, spline concatenation is disabled, and only valid
closed solids with analytic faces enter this path. A normalized shape is NOT
an equality verdict: full oriented surface/trim proof is still mandatory.
"""
from math import isfinite


def _count(shape, kind):
    from OCP.TopExp import TopExp_Explorer
    it = TopExp_Explorer(shape, kind)
    count = 0
    while it.More():
        count += 1
        it.Next()
    return count


def normalize(shape, tolerance):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Sphere, GeomAbs_Torus
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID, TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from .brep_safety import is_valid

    tolerance = float(tolerance)
    if not isfinite(tolerance) or tolerance <= 0:
        raise ValueError('Invalid normalization tolerance')
    # OCCT's geometric confusion is 1e-7 mm. Do not spend the entire
    # caller's tolerance on topology normalization at sub-micron settings.
    if tolerance < 1e-5 or shape.IsNull() or not is_valid(shape):
        return None
    if _count(shape, TopAbs_SOLID) != 1 or _count(shape, TopAbs_SHELL) != 1:
        return None
    allowed = {GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Sphere, GeomAbs_Torus}
    it = TopExp_Explorer(shape, TopAbs_FACE)
    while it.More():
        if BRepAdaptor_Surface(TopoDS.Face_s(it.Current())).GetType() not in allowed:
            return None
        it.Next()
    copy = BRepBuilderAPI_Copy(shape, True, False).Shape()
    unify = ShapeUpgrade_UnifySameDomain(copy, True, True, False)
    unify.SetSafeInputMode(True)
    unify.SetLinearTolerance(1e-7)
    unify.SetAngularTolerance(1e-12)
    unify.AllowInternalEdges(False)
    unify.Build()
    result = unify.Shape()
    if result.IsNull() or not is_valid(result):
        return None
    if _count(result, TopAbs_SOLID) != 1 or _count(result, TopAbs_SHELL) != 1:
        return None
    # Reject anomalous native output. These checks cannot prove equality;
    # that is the separate oriented boundary test below.
    for integrate in (BRepGProp.VolumeProperties_s, BRepGProp.SurfaceProperties_s):
        old, new = GProp_GProps(), GProp_GProps()
        integrate(shape, old)
        integrate(result, new)
        x, y = old.Mass(), new.Mass()
        if not all(isfinite(v) and v > 0 for v in (x, y)):
            return None
        if abs(x-y) > max(1e-7, 1e-9*max(x, y)):
            return None
    return result


def equivalent(a_shape, b_shape, tolerance, progress=None):
    """Return positive only after whole normalized boundaries agree in place.

    False means this fast path is inconclusive, not necessarily different.
    Existing original-solid difference verification remains the fallback.
    """
    from .geometry import describe
    from .step_reexport_tolerance import reexport_equivalent_world
    report = progress or (lambda phase: None)
    report('same_domain_normalize_A')
    a = normalize(a_shape, tolerance)
    if a is None:
        return False
    report('same_domain_normalize_B')
    b = normalize(b_shape, tolerance)
    if b is None:
        return False
    report('same_domain_oriented_boundary')
    return bool(reexport_equivalent_world(
        describe(a, 'A', 'normalized/A'), describe(b, 'B', 'normalized/B'),
        float(tolerance)*.5, allow_boolean=False, _repair_boundary_only=True,
        progress=report))
