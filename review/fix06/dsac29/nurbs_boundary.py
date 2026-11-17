"""Exact OCCT representation conversion before complete boundary comparison.

STEP exporters may replace analytic surfaces AND curves with rational NURBS.
Type mismatches are not geometric differences. Conversion runs on copies in
an isolated native worker; it neither repairs nor aligns either operand.
"""
from collections import Counter
from math import isfinite


def _profile(shape):
    from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX, TopAbs_SOLID, TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
    from OCP.BRep import BRep_Tool
    from .same_domain import _count
    surfaces=Counter();curves=Counter()
    faces=TopExp_Explorer(shape,TopAbs_FACE)
    while faces.More():
        surfaces[str(BRepAdaptor_Surface(TopoDS.Face_s(faces.Current())).GetType())]+=1
        faces.Next()
    edges=TopExp_Explorer(shape,TopAbs_EDGE)
    while edges.More():
        edge=TopoDS.Edge_s(edges.Current())
        curves['degenerated' if BRep_Tool.Degenerated_s(edge)
               else str(BRepAdaptor_Curve(edge).GetType())]+=1
        edges.Next()
    counts=tuple(_count(shape,k) for k in (TopAbs_SOLID,TopAbs_SHELL,TopAbs_FACE,TopAbs_EDGE,TopAbs_VERTEX))
    return counts,surfaces,curves


def _already_nurbs(profile):
    return all('BSpline' in kind for kind in profile[1]) and all(
        kind == 'degenerated' or 'BSpline' in kind for kind in profile[2])


def _convert(shape):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    operation=BRepBuilderAPI_NurbsConvert(shape,True)
    return operation.Shape() if operation.IsDone() else None


def _facewise(shape, report):
    """Exact conversion of each oriented boundary face, without sewing/repair.

    Caller validates the ORIGINAL solid. Every converted face must be valid,
    retain its orientation and wires. The compound is only a proof operand,
    never an exported solid or a replacement for the original geometry.
    """
    from OCP.TopAbs import TopAbs_FACE, TopAbs_WIRE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS_Compound
    from OCP.BRep import BRep_Builder
    from .same_domain import _count
    from .brep_safety import is_valid
    builder=BRep_Builder(); compound=TopoDS_Compound();builder.MakeCompound(compound)
    faces=TopExp_Explorer(shape,TopAbs_FACE);count=0
    while faces.More():
        face=faces.Current();faces.Next()
        converted=_convert(face)
        if converted is None or converted.IsNull():
            report('nurbs_facewise_incomplete');return None
        if (not is_valid(converted) or _count(converted,TopAbs_FACE)!=1 or
            _count(converted,TopAbs_WIRE)!=_count(face,TopAbs_WIRE) or
            converted.Orientation()!=face.Orientation()):
            report('nurbs_facewise_invalid_boundary');return None
        builder.Add(compound,converted);count+=1
    return compound if count else None


def equivalent(a_shape,b_shape,tolerance,progress=None,*,properties=None):
    """A positive requires complete oriented surfaces AND trimming wires.

    The native NurbsConvert operation converts analytic geometry exactly;
    it is not mesh fitting. Unsupported or changed topology remains unknown
    to this optional path and continues through original-solid verification.
    """
    from .brep_safety import is_valid
    from .boundary_descriptor import describe_boundary
    from .step_reexport_tolerance import reexport_equivalent_world
    tolerance=float(tolerance)
    if not isfinite(tolerance) or tolerance<=0:
        raise ValueError('Invalid boundary tolerance')
    report=progress or (lambda phase:None)
    if a_shape.IsNull() or b_shape.IsNull():return False
    pa,pb=_profile(a_shape),_profile(b_shape)
    # Matching NURBS type histograms can still hide different UV conventions.
    # Only skip pairs that contain no spline representation at all.
    if pa[0]!=pb[0] or pa[0][0]!=1:
        report('nurbs_rejected_topology_count');return False
    if not any('BSpline' in kind for profile in (pa,pb) for histogram in profile[1:] for kind in histogram):
        report('nurbs_skipped_analytic_pair');return False
    if not is_valid(a_shape) or not is_valid(b_shape):
        report('nurbs_rejected_invalid_source');return False
    converted=[]
    for label,shape,profile in (('A',a_shape,pa),('B',b_shape,pb)):
        if _already_nurbs(profile):
            report('nurbs_reuse_existing_'+label)
            result=shape
        else:
            report('nurbs_boundary_convert_'+label)
            result=_convert(shape)
            rejection=None
            if result is None: rejection='incomplete'
            elif result.IsNull(): rejection='null'
            elif not is_valid(result): rejection='invalid_topology'
            else:
                from .same_domain import _count
                from OCP.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_FACE
                counts=tuple(_count(result,k) for k in (TopAbs_SOLID,TopAbs_SHELL,TopAbs_FACE))
                if counts!=profile[0][:3]: rejection='changed_boundary_count'
            if rejection:
                report('nurbs_conversion_'+rejection+'_'+label)
                report('nurbs_facewise_convert_'+label)
                result=_facewise(shape,report)
                if result is None:
                    report('nurbs_rejected_conversion_'+label)
                    from .original_boundary import equivalent as original_equivalent
                    return original_equivalent(a_shape,b_shape,tolerance,report)
        converted.append(describe_boundary(result,properties[len(converted)] if properties is not None else None))
    report('nurbs_boundary_surface_and_trim_proof')
    # Exact representation conversion spends no shape-repair displacement
    # budget. The original-boundary verifier allocates its own surface/trim
    # budgets inside the user's tolerance; do not divide it again as repair.
    matched=bool(reexport_equivalent_world(*converted,tolerance,
        allow_boolean=False,_original_boundary_only=True,_nurbs_orientation=True,progress=report))
    report('nurbs_boundary_accepted' if matched else 'nurbs_boundary_rejected_surface_or_trim')
    if not matched:
        from .original_boundary import equivalent as original_equivalent
        return original_equivalent(a_shape,b_shape,tolerance,report)
    return True
