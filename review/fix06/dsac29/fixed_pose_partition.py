"""Verify fixed placement through one shared, validated OCCT partition."""
from OCP.BOPAlgo import BOPAlgo_PaveFiller
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_Transform
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.Message import Message_Fail, Message_Warning
from OCP.Precision import Precision
from OCP.ShapeFix import ShapeFix_ShapeTolerance
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopLoc import TopLoc_Location
from OCP.TopTools import TopTools_ListOfShape

from .brep_safety import is_valid, topology_tolerances
from .material_deltas import volume


def _operation(kind, filler, left, right, fuzzy):
    arguments = TopTools_ListOfShape()
    tools = TopTools_ListOfShape()
    arguments.Append(left)
    tools.Append(right)
    operation = kind(filler)
    try:
        operation.SetArguments(arguments)
        operation.SetTools(tools)
        operation.SetNonDestructive(True)
        operation.SetRunParallel(True)
        operation.SetUseOBB(True)
        operation.SetFuzzyValue(fuzzy)
        operation.Build()
        shape = operation.Shape() if operation.IsDone() else None
        if shape is None or not is_valid(shape):
            return None
        return volume(shape)
    finally:
        # The OCCT operation borrows its filler.
        del operation


def _bounded_source(shape, stored, limit, progress):
    if stored <= limit:
        return shape
    progress(f'fixed_partition_limit_stored_tolerances {stored:.9g} mm to {limit:.9g} mm')
    # LimitTolerance changes only subshape tolerances on a detached copy.
    # The exact analyzer checks the unchanged curves, surfaces and topology
    # with the new limits before the copy can be used in a Boolean.
    bounded = BRepBuilderAPI_Copy(shape, True, False).Shape()
    if bounded.IsNull() or bounded.IsPartner(shape):
        return None
    ShapeFix_ShapeTolerance().LimitTolerance(bounded, 0., limit)
    if (max(topology_tolerances(bounded).values()) > limit
            or not BRepCheck_Analyzer(bounded, True, False, True).IsValid()):
        progress('fixed_partition_tightened_source_unverified')
        return None
    progress('fixed_partition_tightened_source_valid')
    return bounded


def _intersections(left, right, fuzzy, progress, *, parallel):
    arguments = TopTools_ListOfShape()
    arguments.Append(left)
    arguments.Append(right)
    filler = BOPAlgo_PaveFiller()
    filler.SetArguments(arguments)
    filler.SetNonDestructive(True)
    filler.SetRunParallel(parallel)
    filler.SetUseOBB(True)
    filler.SetFuzzyValue(fuzzy)
    filler.Perform()
    if filler.HasErrors() or filler.HasWarnings():
        report = filler.GetReport()
        for gravity, level in ((Message_Fail, 'error'), (Message_Warning, 'warning')):
            codes = dict.fromkeys(alert.GetMessageKey() for alert in report.GetAlerts(gravity))
            if codes:
                progress(f'fixed_partition_{level} ' + ', '.join(codes))
        return None
    return filler


def _bake_location(shape):
    # Copy the same world geometry into the surfaces/curves themselves so
    # intersection does not depend on a chain of STEP assembly locations.
    if shape.Location().IsIdentity():
        return shape
    return BRepBuilderAPI_Transform(
        shape.Located(TopLoc_Location()), shape.Location().Transformation(), True, False
    ).Shape()


def same_partition(left, right, tolerance, progress):
    """Require two near-empty Cuts and a balanced Common in the original pose."""
    progress('fixed_partition_validate_sources')
    for shape in (left, right):
        if shape.ShapeType() != TopAbs_SOLID or not is_valid(shape):
            progress('fixed_partition_invalid_source')
            return False

    left_volume, right_volume = volume(left), volume(right)
    if min(left_volume, right_volume) <= 0:
        progress('fixed_partition_invalid_source_volume')
        return False

    stored_left = max(topology_tolerances(left).values())
    stored_right = max(topology_tolerances(right).values())
    minimum_fuzzy = Precision.Confusion_s()
    # OCCT clamps any smaller setting to its minimum. Reserve only the
    # needed headroom before considering editing tolerance metadata.
    preferred_fuzzy = max(minimum_fuzzy, tolerance / 100)
    headroom = tolerance - max(stored_left, stored_right)
    fuzzy = max(minimum_fuzzy, min(preferred_fuzzy, headroom))
    limit = tolerance - fuzzy
    progress(f'fixed_partition_fuzzy_budget {fuzzy:.9g} mm with source limit {limit:.9g} mm')
    if limit <= 0:
        progress('fixed_partition_source_tolerance')
        return False
    left = _bounded_source(left, stored_left, limit, progress)
    if left is None:
        return False
    right = _bounded_source(right, stored_right, limit, progress)
    if right is None:
        return False

    progress('fixed_partition_intersections')
    filler = _intersections(left, right, fuzzy, progress, parallel=True)
    if filler is None:
        progress('fixed_partition_retry_baked')
        left, right = _bake_location(left), _bake_location(right)
        fuzzy = minimum_fuzzy
        for shape in (left, right):
            if (not is_valid(shape)
                    or max(topology_tolerances(shape).values()) > tolerance - fuzzy):
                progress('fixed_partition_retry_source_unverified')
                return False
        progress('fixed_partition_retry_intersections')
        filler = _intersections(left, right, fuzzy, progress, parallel=False)
        if filler is None:
            progress('fixed_partition_unverified_intersections')
            return False

    residual_limit = tolerance**3
    residuals = []
    for first, second, direction in ((left, right, 'a_minus_b'), (right, left, 'b_minus_a')):
        progress('fixed_partition_cut_' + direction)
        residual = _operation(BRepAlgoAPI_Cut, filler, first, second, fuzzy)
        if residual is None or residual > residual_limit:
            progress('fixed_partition_unverified_' + direction)
            return False
        residuals.append(residual)
    removed, added = residuals

    progress('fixed_partition_common')
    common = _operation(BRepAlgoAPI_Common, filler, left, right, fuzzy)
    if common is None or common <= 0:
        progress('fixed_partition_invalid_common')
        return False
    balance_limit = max(residual_limit, max(left_volume, right_volume) * 1e-7)
    same = max(abs(common + removed - left_volume),
               abs(common + added - right_volume)) <= balance_limit
    progress('fixed_partition_proven' if same else 'fixed_partition_volume_balance_failed')
    return same
