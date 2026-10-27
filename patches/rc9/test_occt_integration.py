"""Native OCCT safety regressions for integrated RC9."""
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from dsac29.brep_safety import validated_copy,is_valid,UnprovenRepair
from dsac29.material_deltas import calculate,operate,volume,bind_common
from dsac29.geometry import describe
from dsac29.step_reexport_tolerance import reexport_equivalent_world

def box(x,y=10,z=10):
    return BRepPrimAPI_MakeBox(x,y,z).Shape()

def info(shape):
    return describe(shape,'part','test')

def test_valid_inputs_never_copied_or_modified():
    original=box(20)
    result,repaired=validated_copy(original,.01)
    assert result.IsSame(original) and repaired is False
    assert is_valid(original)

def test_null_repair_fails_closed():
    from OCP.TopoDS import TopoDS_Shape
    with pytest.raises(UnprovenRepair):
        validated_copy(TopoDS_Shape(),.01)

def test_tolerance_not_relaxed():
    with pytest.raises(ValueError):
        validated_copy(box(20),.011)

def test_material_regions_shared_intersection_and_volume_balance():
    a,b=info(box(20)),info(box(25))
    regions=calculate(a,b,.01)
    assert abs(regions.common_mm3-2000)<1e-3
    assert abs(regions.added_mm3-500)<1e-3
    assert abs(regions.removed_mm3)<1e-3
    assert is_valid(regions.common) and is_valid(regions.added) and is_valid(regions.removed)
    assert is_valid(a.shape) and is_valid(b.shape)

def test_cached_common_reuse_preserves_regions():
    a,b=info(box(20)),info(box(25))
    common=operate(BRepAlgoAPI_Common,a.shape,b.shape,.01)
    regions=calculate(a,b,.01,common_shape=bind_common(common,a.shape,b.shape,.01))
    assert regions.common.IsEqual(common)
    assert abs(regions.common_mm3-volume(common))<1e-3
    assert abs(regions.added_mm3-500)<1e-3

def test_raw_or_wrong_pair_common_never_reused(monkeypatch):
    import dsac29.material_deltas as mod
    a,b,c=info(box(20)),info(box(25)),info(box(22))
    common=operate(BRepAlgoAPI_Common,a.shape,b.shape,.01)
    evidence=bind_common(common,a.shape,b.shape,.01)
    original=mod._from_filler
    common_calls=[]
    def observed(klass,*args,**kwargs):
        if klass is BRepAlgoAPI_Common:
            common_calls.append(True)
        return original(klass,*args,**kwargs)
    monkeypatch.setattr(mod,'_from_filler',observed)
    # Raw shape has no pair provenance, even if valid.
    mod.calculate(a,b,.01,common_shape=common)
    assert len(common_calls)==1
    # Correctly bound evidence is reused without rebuilding Common.
    common_calls.clear()
    mod.calculate(a,b,.01,common_shape=evidence)
    assert not common_calls
    # Different input B-Rep must recompute Common, not silently reuse it.
    common_calls.clear()
    regions=mod.calculate(c,b,.01,common_shape=evidence)
    assert len(common_calls)==1
    assert abs(regions.common_mm3-2200)<1e-3
    # Tolerance changes invalidate the same pair's cache.
    common_calls.clear()
    mod.calculate(a,b,.005,common_shape=evidence)
    assert len(common_calls)==1


def test_different_geometry_never_same_from_repair_flag():
    a,b=info(box(20)),info(box(20.2))
    assert not reexport_equivalent_world(a,b,.01,allow_boolean=False,_repair_boundary_only=True)

def test_repair_mode_never_uses_boolean_shortcut(monkeypatch):
    import dsac29.step_reexport_tolerance as mod
    a=info(box(20))
    def forbidden(*args,**kwargs):
        raise AssertionError('Boolean fallback called')
    monkeypatch.setattr(mod,'_verified_difference_empty',forbidden)
    assert reexport_equivalent_world(a,a,.01,allow_boolean=False,_repair_boundary_only=True)
