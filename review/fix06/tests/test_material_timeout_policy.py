"""Bounded timeouts for isolated Common/Cut on complex parts."""
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29 import material_guard
from dsac29.geometry import describe
from dsac29.native_guard import NativeGeometryFailure


def test_reexport_pair_receives_same_deadline_after_binary_transfer(tmp_path):
    from pathlib import Path
    from dsac29.brep_transport import read_brep, write_brep
    folder = Path(__file__).parent / 'fixtures/volume_reexport'
    originals = [read_brep(folder / name) for name in ('A.brep','B.brep')]
    for i, shape in enumerate(originals):
        write_brep(shape,tmp_path / str(i))
    restored = [read_brep(tmp_path / str(i)) for i in range(2)]
    assert material_guard.material_operation_timeout(*originals) >= 180
    assert material_guard.material_operation_timeout(*originals) == material_guard.material_operation_timeout(*restored)


@pytest.mark.parametrize('override',[.5,35,90,150,240])
def test_explicit_timeout_is_preserved(override):
    assert material_guard.material_operation_timeout(None,None,override) == override


@pytest.mark.parametrize('invalid',[0,-1,float('inf'),float('nan'),901])
def test_bad_explicit_timeout_rejected(invalid):
    with pytest.raises(ValueError):
        material_guard.material_operation_timeout(None,None,invalid)


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


def test_geometry_failure_is_not_reported_as_timeout(monkeypatch):
    import json
    from pathlib import Path
    from types import SimpleNamespace
    shape=BRepPrimAPI_MakeBox(1,2,3).Shape()
    part=describe(shape,'part','part')
    def failed(argv,**kwargs):
        Path(argv[-1]).write_text(json.dumps({'ok':False,'error_code':'MATERIAL_BOOLEAN_UNVERIFIED','error':'invalid topology'}))
        return SimpleNamespace(returncode=70,stderr=b'')
    monkeypatch.setattr(material_guard.subprocess,'run',failed)
    with pytest.raises(NativeGeometryFailure) as error:
        material_guard.calculate_isolated(part,part)
    assert 'MATERIAL_BOOLEAN_UNVERIFIED' in str(error.value)
    assert 'limit' not in str(error.value).lower()
