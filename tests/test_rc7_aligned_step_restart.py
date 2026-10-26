"""STEP round-trip: count, names, positions and fail-closed negative controls."""
import numpy as np
import pytest
from dataclasses import replace
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.aligned_step_restart import save_aligned_step_and_reload, _match_imported


def _assembly():
    parts=[]
    for i in range(5):
        shape=BRepPrimAPI_MakeBox(10.+i, 15., 7.).Shape()
        original=describe(shape, 'plate' if i<3 else 'gusset',
                          f'ROOT/item_{i}', 'original.step')
        parts.append(_relocate(original,np.eye(3),
                               np.array([float(i*40+1200),-400.,200.])))
    return parts


def test_roundtrip_reimports_and_restores_metadata(tmp_path):
    parts=_assembly()
    result,path,stats=save_aligned_step_and_reload(parts,tmp_path,0.01)
    assert path.is_file() and path.stat().st_size>500
    assert stats['solids_expected']==stats['solids_reimported']==len(parts)
    assert sorted(p.path for p in result)==sorted(p.path for p in parts)
    assert sorted(p.source for p in result)==sorted(p.source for p in parts)
    for a in parts:
        b=next(x for x in result if x.path==a.path)
        assert np.linalg.norm(a.center-b.center)<.001
        assert abs(a.volume-b.volume)<.001


def test_roundtrip_refuses_missing_occurrence():
    parts=_assembly()
    with pytest.raises(RuntimeError,match='liczba brył'):
        _match_imported(parts,parts[:-1],.01)


def test_roundtrip_refuses_wrong_geometry_metadata():
    parts=_assembly()
    changed=list(parts)
    changed[0]=replace(changed[0],volume=changed[0].volume+100)
    with pytest.raises(RuntimeError,match='brak jednoznacznie'):
        _match_imported(parts,changed,.01)


def test_occurrence_ids_restore_reordered_metadata_despite_integral_drift():
    parts=_assembly()
    imported=[replace(p,name=f'DSC_OCC_{i:08d}',volume=p.volume*1.003,
                      center=p.center+np.array([.036,0.,0.])) for i,p in enumerate(parts)]
    restored=_match_imported(parts,list(reversed(imported)),.01,occurrence_ids=True)
    assert [p.path for p in restored]==[p.path for p in reversed(parts)]
    # Reimported geometry/properties are retained, never replaced by old proof.
    assert restored[0].volume==imported[-1].volume


@pytest.mark.parametrize('bad_name',['DSC_OCC_00000000','DSC_OCC_99999999','plate'])
def test_occurrence_ids_reject_duplicate_missing_or_unknown(bad_name):
    parts=_assembly()
    imported=[replace(p,name=f'DSC_OCC_{i:08d}') for i,p in enumerate(parts)]
    imported[-1]=replace(imported[-1],name=bad_name)
    with pytest.raises(RuntimeError,match='ID'):
        _match_imported(parts,imported,.01,occurrence_ids=True)


def test_shared_coincident_shapes_keep_distinct_occurrences(tmp_path):
    first=_assembly()[0]
    parts=[replace(first,name='duplicate',path=f'ROOT/branch_{i}/duplicate') for i in range(3)]
    restored,_,stats=save_aligned_step_and_reload(parts,tmp_path,.01)
    assert stats['solids_reimported']==3
    assert sorted(p.path for p in restored)==sorted(p.path for p in parts)


def test_fresh_step_comparison_checks_geometry_despite_integral_drift():
    from dsac29.compare import compare
    a=_assembly()[0]
    b=replace(a,volume=a.volume*.997,center=a.center+np.array([.036,0,0]))
    # Independent topology, no IsSame shortcut or pre-existing certificates.
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    b=replace(b,shape=BRepBuilderAPI_Copy(a.shape).Shape())
    records=compare([a],[b],.01,step_reexport_tolerance=True)
    assert len(records)==1 and records[0].status=='SAME'
    changed=_relocate(b,np.eye(3),np.array([.03,0,0]))
    records=compare([a],[changed],.01,step_reexport_tolerance=True)
    assert not any(r.status in ('SAME','RENAMED') for r in records)


def test_repeated_parts_keep_shared_definitions_after_step(tmp_path):
    from dsac29.geometry_registry import GeometryRegistry
    first=_assembly()[0]
    parts=[replace(_relocate(first,np.eye(3),np.array([i*40.,0.,0.])),
                   name='same-name',path=f'ROOT/{i}') for i in range(30)]
    restored,_,stats=save_aligned_step_and_reload(parts,tmp_path,.01)
    assert stats['definitions_created']==1
    assert stats['definitions_reused']==29
    registry=GeometryRegistry()
    assert len({registry.definition(p) for p in restored})==1
    for old in parts:
        new=next(p for p in restored if p.path==old.path)
        assert np.linalg.norm(new.center-old.center)<1.e-6


def test_fresh_comparison_scopes_native_worker_session():
    from dsac29.aligned_step_restart import run_fresh_comparison
    from dsac29.native_session import current
    assert current() is None
    def large():
        assert current() is not None
        return 123
    assert run_fresh_comparison(large,600)==123
    assert current() is None
    assert run_fresh_comparison(lambda: current(),10) is None
    with pytest.raises(ValueError):
        run_fresh_comparison(lambda: (_ for _ in ()).throw(ValueError()),600)
    assert current() is None
