"""OCCT material regions with one pair-scoped PaveFiller for Common/Cut.

Production calls run in material_guard's crash-contained worker. Repairs are
deep copies, accepted only after original oriented trim equivalence is proven.
"""
from __future__ import annotations
from dataclasses import dataclass
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Cut
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

COLORS={
 'CHANGED_COMMON':(38/255,117/255,247/255),
 'CHANGED_ADDED':(245/255,158/255,11/255),
 'CHANGED_REMOVED':(190/255,18/255,60/255),
}

@dataclass(frozen=True)
class CommonEvidence:
    """Pair-bound Common produced earlier by the trusted OCCT pipeline.

    This is a provenance guard, NOT an independent geometric proof. Keep
    source shape references so location/orientation and topology identity
    can be checked before reusing a previously calculated intersection.
    """
    shape: object
    old_shape: object
    new_shape: object
    tolerance_mm: float


def bind_common(common, old_shape, new_shape, tolerance):
    """Bind a trusted precomputed Common to its exact input B-Reps."""
    from .brep_safety import is_valid
    tol = float(tolerance)
    if not 0. < tol <= .01:
        raise ValueError('Common evidence tolerance must be within 0.01 mm')
    if not is_valid(old_shape) or not is_valid(new_shape):
        raise ValueError('Cannot cache Common for invalid source B-Reps')
    return CommonEvidence(_check_result(common), old_shape, new_shape, tol)


@dataclass
class MaterialRegions:
    common:object
    added:object
    removed:object
    common_mm3:float
    added_mm3:float
    removed_mm3:float

def volume(shape):
    prop=GProp_GProps()
    BRepGProp.VolumeProperties_s(shape,prop)
    return max(0.,float(prop.Mass()))

def solids(shape,epsilon=1e-7):
    ex=TopExp_Explorer(shape,TopAbs_SOLID)
    while ex.More():
        piece=ex.Current();ex.Next()
        if volume(piece)>epsilon:yield piece

def _check_result(result):
    from .brep_safety import is_valid
    if result.IsNull() or not is_valid(result):
        raise RuntimeError('OCCT Boolean returned invalid or null topology')
    return result

@dataclass(frozen=True)
class RegionEvidence:
    """Pair-scoped material regions from a trusted isolated OCCT calculation.

    Like CommonEvidence, this is provenance, not a geometric SAME proof.
    """
    regions: MaterialRegions
    old_shape: object
    new_shape: object
    tolerance_mm: float


def bind_regions(regions, old, new, tolerance):
    """Bind a verified producer's material regions to exact source shapes."""
    from .brep_safety import is_valid
    tol = float(tolerance)
    if not 0. < tol <= .01:
        raise ValueError('Region evidence tolerance must be within 0.01 mm')
    if not isinstance(regions, MaterialRegions):
        raise TypeError('Only MaterialRegions can be bound')
    if not is_valid(old.shape) or not is_valid(new.shape):
        raise ValueError('Cannot cache regions for invalid original B-Reps')
    for shape in (regions.common, regions.added, regions.removed):
        _check_result(shape)
    if not _regions_balance(regions, old, new, tol):
        raise ValueError('Cannot bind material regions with invalid volume balance')
    return RegionEvidence(regions, old.shape, new.shape, tol)


def _regions_balance(regions, old, new, tolerance):
    import math
    cv, av, rv = regions.common_mm3, regions.added_mm3, regions.removed_mm3
    if not all(math.isfinite(v) and v >= 0 for v in (cv, av, rv)):
        return False
    limit = max(1e-3, 10.*tolerance**3, 5e-5*max(old.volume, new.volume))
    return (abs(cv + rv - old.volume) <= limit
            and abs(cv + av - new.volume) <= limit)


def _matching_regions(entry, old, new, tolerance):
    """Reject unbound, stale, repaired, or cross-pair precomputed regions."""
    from .brep_safety import is_valid
    if not isinstance(entry, RegionEvidence):
        return False
    if entry.tolerance_mm != float(tolerance):
        return False
    if not is_valid(old.shape) or not is_valid(new.shape):
        return False
    if not (entry.old_shape.IsEqual(old.shape)
            and entry.new_shape.IsEqual(new.shape)):
        return False
    if not _regions_balance(entry.regions, old, new, float(tolerance)):
        return False
    return all(is_valid(shape) for shape in
               (entry.regions.common, entry.regions.added, entry.regions.removed))


def operate(klass,s,t,tolerance):
    """One-off native Boolean, used only in isolated proof operations."""
    from .boolean_ops import configured
    from .brep_safety import validated_copy
    s,_=validated_copy(s,tolerance)
    t,_=validated_copy(t,tolerance)
    op=configured(klass,s,t,tolerance)
    op.Build()
    if not op.IsDone():
        raise RuntimeError('OCCT Boolean did not complete')
    return _check_result(op.Shape())

def _shared_filler(a,b,tolerance):
    from OCP.BOPAlgo import BOPAlgo_PaveFiller
    from OCP.TopTools import TopTools_ListOfShape
    args=TopTools_ListOfShape();args.Append(a);args.Append(b)
    filler=BOPAlgo_PaveFiller()
    filler.SetArguments(args)
    filler.SetNonDestructive(True)
    filler.SetUseOBB(True)
    filler.SetFuzzyValue(max(float(tolerance)/100.,1e-6))
    filler.Perform()
    if filler.HasErrors():
        raise RuntimeError('OCCT PaveFiller intersection failed')
    return filler

def _from_filler(klass,filler,first,second,tolerance):
    from OCP.TopTools import TopTools_ListOfShape
    args=TopTools_ListOfShape();args.Append(first)
    tools=TopTools_ListOfShape();tools.Append(second)
    op=klass(filler)
    try:
        op.SetArguments(args);op.SetTools(tools)
        op.SetNonDestructive(True)
        op.SetUseOBB(True)
        op.SetFuzzyValue(max(float(tolerance)/100.,1e-6))
        op.Build()
        if not op.IsDone():
            raise RuntimeError('OCCT Boolean with shared filler failed')
        return _check_result(op.Shape())
    finally:
        del op

def calculate(old,new,tolerance=0.01,*,common_shape=None):
    """Use one intersection and validate Common/Cut volume conservation."""
    from .brep_safety import validated_copy,is_valid
    a,repaired_a=validated_copy(old.shape,tolerance)
    b,repaired_b=validated_copy(new.shape,tolerance)
    filler=_shared_filler(a,b,tolerance)
    # A bare TopoDS_Shape has no pair provenance: its volume may happen
    # to balance even when the intersection belongs to a different pair.
    # IsEqual checks TShape, location and orientation; repairs invalidate it.
    cached = None
    if isinstance(common_shape, CommonEvidence) and not (repaired_a or repaired_b):
        if (common_shape.tolerance_mm == float(tolerance)
                and common_shape.old_shape.IsEqual(a)
                and common_shape.new_shape.IsEqual(b)):
            cached = _check_result(common_shape.shape)
    common = cached if cached is not None else _from_filler(
        BRepAlgoAPI_Common, filler, a, b, tolerance)
    added=_from_filler(BRepAlgoAPI_Cut,filler,b,a,tolerance)
    removed=_from_filler(BRepAlgoAPI_Cut,filler,a,b,tolerance)
    cv,av,rv=map(volume,(common,added,removed))
    abs_tol=max(1e-3,10.*tolerance**3,5e-5*max(old.volume,new.volume))
    if abs(cv+rv-old.volume)>abs_tol or abs(cv+av-new.volume)>abs_tol:
        raise RuntimeError('OCCT Boolean material balance failed')
    return MaterialRegions(common,added,removed,cv,av,rv)

def all_changes(records,a,b,tolerance=0.01,progress=None,precomputed=None):
    """Generate once for STEP/HTML/CSV, reusing precomputed region evidence."""
    cache=dict(precomputed or {});out={};errors={}
    indices=[i for i,r in enumerate(records) if r.status=='CHANGED'
             and r.a_index is not None and r.b_index is not None]
    for n,index in enumerate(indices,1):
        r=records[index]
        entry=cache.get(index)
        if _matching_regions(entry,a[r.a_index],b[r.b_index],tolerance):
            out[index]=entry.regions
            continue
        if progress:progress(f'R15: podział materiału {n}/{len(indices)} — {b[r.b_index].name}')
        from .material_guard import calculate_isolated
        from .native_guard import NativeGeometryFailure
        try:out[index]=calculate_isolated(a[r.a_index],b[r.b_index],tolerance)
        except NativeGeometryFailure:raise
        except Exception as exc:errors[index]=str(exc)
    return out,errors
