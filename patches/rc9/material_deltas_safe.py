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

def operate(klass,s,t,tolerance):
    """One-off native Boolean, used only in isolated proof operations."""
    from .boolean_ops import configured
    from .brep_safety import validated_copy
    s,_=validated_copy(s,tolerance)
    t,_=validated_copy(t,tolerance)
    op=configured(klass,s,t,tolerance)
    op.Build()
    if not op.IsDone() or op.HasErrors():
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
        if not op.IsDone() or op.HasErrors():
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
    # Cached Common refers to original inputs: invalidate after any repair.
    if common_shape is not None and not (repaired_a or repaired_b):
        if not is_valid(common_shape):
            raise RuntimeError('Precomputed Common has invalid topology')
        common=common_shape
    else:
        common=_from_filler(BRepAlgoAPI_Common,filler,a,b,tolerance)
    added=_from_filler(BRepAlgoAPI_Cut,filler,b,a,tolerance)
    removed=_from_filler(BRepAlgoAPI_Cut,filler,a,b,tolerance)
    cv,av,rv=map(volume,(common,added,removed))
    abs_tol=max(1e-3,10.*tolerance**3,5e-5*max(old.volume,new.volume))
    if abs(cv+rv-old.volume)>abs_tol or abs(cv+av-new.volume)>abs_tol:
        raise RuntimeError('OCCT Boolean material balance failed')
    return MaterialRegions(common,added,removed,cv,av,rv)
