"""Regression coverage for a medium 379-part no-global-shift revision."""
import inspect
import json
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29 import compare as comparator, native_guard, cli
from dsac29.geometry import describe
from dsac29.brep_transport import write_brep


def _part(x,name):
    return describe(BRepPrimAPI_MakeBox(gp_Pnt(float(x),0.,0.),8.,9.,10.).Shape(),
                    name,name)


def test_medium_revision_native_world_proof_does_not_run_unbounded(monkeypatch):
    original=_part(0,'old')
    revised=_part(0,'new')
    far_a=[_part(1_000+i*30,'old-'+str(i)) for i in range(79)]
    far_b=[_part(200_000+i*30,'new-'+str(i)) for i in range(79)]
    assert len(far_a)+1==80
    calls=[]
    monkeypatch.setattr(comparator,'guarded_world_equivalent',
                        lambda a,b,t,**kw:(calls.append(kw.get('timeout_s')) or True))
    from dsac29.geometry_registry import GeometryRegistry
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *a:False)
    out=comparator.compare([original]+far_a,[revised]+far_b,revision_only=True,
                           exact_serialization=False)
    assert calls and all(t==25 for t in calls)
    assert any(r.a_index==0 and r.b_index==0 and r.status in ('SAME','RENAMED') for r in out)


def test_unknown_native_world_is_never_same_and_does_not_blow_up_other_parts(monkeypatch):
    original=_part(0,'same')
    revised=_part(0,'same')
    far_a=[_part(1_000+i*30,'old-'+str(i)) for i in range(79)]
    far_b=[_part(200_000+i*30,'new-'+str(i)) for i in range(79)]
    from dsac29.geometry_registry import GeometryRegistry
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *a:False)
    def fail(*a,**kwargs):
        raise native_guard.NativeGeometryFailure('synthetic native timeout')
    monkeypatch.setattr(comparator,'guarded_world_equivalent',fail)
    out=comparator.compare([original]+far_a,[revised]+far_b,revision_only=True,
                           exact_serialization=False)
    assert any(r.a_index==0 and r.status=='UNCERTAIN' for r in out)
    assert any(r.b_index==0 and r.status=='UNCERTAIN' for r in out)
    assert not any(r.a_index==0 and r.status in ('SAME','RENAMED') for r in out)


def test_original_equivalent_world_dispatched_in_native_worker(tmp_path):
    a=_part(0,'A');b=_part(0,'B')
    pa=tmp_path/'A.brep';pb=tmp_path/'B.brep'
    write_brep(a.shape,pa);write_brep(b.shape,pb)
    req=tmp_path/'request.json';reply=tmp_path/'reply.json'
    req.write_text(json.dumps({'operation':'world_equivalent',
        'a':str(pa),'b':str(pb),'tolerance':.01}),encoding='utf-8')
    result=native_guard.worker(req,reply)
    assert result==0
    data=json.loads(reply.read_text(encoding='utf-8'))
    assert data['ok'] and data['match'] is True


def test_same_position_medium_assembly_uses_shared_guarded_process():
    src=inspect.getsource(cli.process)
    assert 'with world_session(max(len(a),len(b))>=80 or registered_frame):' in src


def test_per_part_native_progress_reports_last_active_pair():
    src=inspect.getsource(comparator.compare)
    assert 'Zgodność położenia: B-Rep A[' in src
    assert 'unknown_world_groups' in src


def test_zw3d_reexport_mass_center_drift_does_not_hide_no_shift_candidate(monkeypatch):
    """Medium 80-599 assemblies must check an 0.2 mm integrated center drift.

    The mocked native proof stands in for the unchanged B-Rep (not a
    descriptor-based SAME). Without the wider lookup no native call occurs.
    """
    from dataclasses import replace
    a=[_part(0,'plate')]+[_part(1000+i*50,'old'+str(i)) for i in range(79)]
    b=[replace(_part(0,'plate'),center=a[0].center+np.array([.2,0.,0.]))]+[
        _part(100000+i*50,'new'+str(i)) for i in range(79)]
    calls=[]
    def verified(*args,**kwargs):
        calls.append(kwargs)
        return True
    monkeypatch.setattr(comparator,'guarded_world_equivalent',verified)
    monkeypatch.setattr(comparator,'guarded_world_reexport',verified)
    out=comparator.compare(a,b,exact_serialization=False,revision_only=True)
    assert calls, 'The centered re-export candidate must reach native B-Rep'
    assert any(r.a_index==r.b_index==0 and r.status=='SAME' for r in out)


def test_zw3d_mass_drift_never_means_geometry_same_without_native_proof(monkeypatch):
    from dataclasses import replace
    a=[_part(0,'plate')]+[_part(1000+i*50,'old'+str(i)) for i in range(79)]
    b=[replace(_part(0,'plate'),center=a[0].center+np.array([.2,0.,0.]))]+[
        _part(100000+i*50,'new'+str(i)) for i in range(79)]
    calls=[]
    def unproven(*args,**kwargs):
        calls.append(1)
        return False
    monkeypatch.setattr(comparator,'guarded_world_equivalent',unproven)
    monkeypatch.setattr(comparator,'guarded_world_reexport',unproven)
    out=comparator.compare(a,b,exact_serialization=False,revision_only=True)
    assert calls
    assert not any(r.a_index==0 and r.status in ('SAME','RENAMED') for r in out)


def test_zw3d_solid_set_fallback_requires_original_pair_and_same_name(monkeypatch):
    from dataclasses import replace
    a=[_part(0,'plate')]+[_part(1000+i*50,'old'+str(i)) for i in range(79)]
    b=[replace(_part(0,'plate'),center=a[0].center+np.array([.2,0.,0.]))]+[
        _part(100000+i*50,'new'+str(i)) for i in range(79)]
    calls=[]
    def proven(*args,**kwargs):
        calls.append(kwargs)
        return False
    monkeypatch.setattr(comparator,'guarded_world_equivalent',proven)
    monkeypatch.setattr(comparator,'guarded_world_reexport',proven)
    comparator.compare(a,b,exact_serialization=False,revision_only=True)
    assert any(k.get('allow_solid_set_proof') is True for k in calls)
    b[0]=replace(b[0],name='renamed_plate')
    calls.clear()
    comparator.compare(a,b,exact_serialization=False,revision_only=True)
    assert not any(k.get('allow_solid_set_proof') for k in calls)


def test_cad_no_shift_negative_proofs_are_never_promoted_to_same():
    original=_part(0,'plate')
    changed=describe(BRepPrimAPI_MakeBox(gp_Pnt(0,0,0),9.,9.,10.).Shape(),
                     'plate','plate-new')
    out=comparator.compare([original],[changed],revision_only=True,exact_serialization=True)
    assert not any(r.status in ('SAME','RENAMED') for r in out)
