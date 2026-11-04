"""Bounded timeouts for isolated Common/Cut on complex parts."""
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29 import material_guard
from dsac29.geometry import describe
from dsac29.native_guard import NativeGeometryFailure


@pytest.mark.parametrize('bytes_count,expected', [
    (0,60),(256*1024-1,60),(256*1024,120),
    (2*1024*1024-1,120),(2*1024*1024,180),
    (8*1024*1024-1,180),(8*1024*1024,240),(128*1024*1024,240),
])
def test_brep_size_selects_bounded_timeout(bytes_count, expected):
    assert material_guard.material_operation_timeout(bytes_count) == expected


@pytest.mark.parametrize('override',[.5,35,90,150,240])
def test_explicit_timeout_is_preserved(override):
    assert material_guard.material_operation_timeout(2*1024*1024, override) == override


@pytest.mark.parametrize('invalid',[0,-1,float('inf'),float('nan'),901])
def test_bad_explicit_timeout_rejected(invalid):
    with pytest.raises(ValueError):
        material_guard.material_operation_timeout(100,invalid)


def test_negative_brep_size_rejected():
    with pytest.raises(ValueError):
        material_guard.material_operation_timeout(-1)


def test_worker_receives_deadline_and_keeps_fail_closed(monkeypatch):
    a=describe(BRepPrimAPI_MakeBox(10,10,10).Shape(),'A','A')
    b=describe(BRepPrimAPI_MakeBox(10,10,9).Shape(),'B','B')
    requests=[]
    def fake_run(*args,**kwargs):
        requests.append(kwargs['timeout'])
        raise material_guard.subprocess.TimeoutExpired(args[0],kwargs['timeout'])
    monkeypatch.setattr(material_guard.subprocess,'run',fake_run)
    with pytest.raises(NativeGeometryFailure,match='60 s'):
        material_guard.calculate_isolated(a,b)
    assert requests==[60]
    with pytest.raises(NativeGeometryFailure,match='0.2 s'):
        material_guard.calculate_isolated(a,b,timeout_s=.2)
    assert requests==[60,.2]


def test_actual_small_common_cut_is_still_exact():
    a=describe(BRepPrimAPI_MakeBox(10,10,10).Shape(),'A','A')
    b=describe(BRepPrimAPI_MakeBox(12,10,10).Shape(),'B','B')
    reg=material_guard.calculate_isolated(a,b)
    assert abs(reg.common_mm3-1000.)<.001
    assert abs(reg.added_mm3-200.)<.001
    assert abs(reg.removed_mm3)<.001
