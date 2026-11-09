"""Regression coverage for a medium 379-part no-global-shift revision."""
import inspect
import json
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29 import compare as comparator, native_guard, cli
from dsac29.geometry import describe
from dsac29.brep_transport import write_brep


@pytest.fixture(autouse=True)
def _isolate_stage_one_from_rigid_matching(monkeypatch):
    """These tests verify the same-position native B-Rep stage only.

    One deliberately unproven STEP copy must not trigger thousands of
    unrelated rigid Booleans over synthetic 80-150-element box assemblies.
    Full rigid geometry has independent dedicated regression suites.
    """
    monkeypatch.setattr(comparator,'equivalent_rigid',
                        lambda *args,**kwargs:(False,None,None))
    # This suite deliberately drives the stage-one native guard with
    # synthetic negative, timeout and transient-crash responses. An exact
    # canonical STEP digest must not short-circuit the simulated failure:
    # the dedicated test_occurrence_identity.py verifies the canonical
    # identity optimization independently.
    from dsac29 import occurrence_identity
    monkeypatch.setattr(occurrence_identity,'prepare_occurrence_identities',
                        lambda *args,**kwargs: {'selected':0,'proven':0,
                                               'skipped':0,'elapsed_s':0.0})


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
    assert 'world_probe_failures' in src


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


def test_zw3d_solid_set_fallback_is_name_independent_and_still_requires_brep(monkeypatch):
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
    assert any(k.get('allow_solid_set_proof') is True for k in calls)


def test_cad_no_shift_negative_proofs_are_never_promoted_to_same():
    original=_part(0,'plate')
    changed=describe(BRepPrimAPI_MakeBox(gp_Pnt(0,0,0),9.,9.,10.).Shape(),
                     'plate','plate-new')
    out=comparator.compare([original],[changed],revision_only=True,exact_serialization=True)
    assert not any(r.status in ('SAME','RENAMED') for r in out)


def _repeated_150(extra=False):
    """150 located copies from distinct STEP export definitions."""
    from dsac29.alignment import _relocate
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    first=_part(0,'P')
    second=describe(BRepPrimAPI_MakeBox(8.,9.,10.).Shape(),'P','new_definition')
    a=[];b=[]
    for i in range(150):
        pos=np.array([float(i*23),float(i%7*30),float(i%5*10)])
        a.append(_relocate(first,np.eye(3),pos))
        b.append(_relocate(second,np.eye(3),pos))
    if extra:
        b.append(_part(100000,'EXTRA_SOLID'))
    return a,b


def test_150_repeated_zw3d_copies_recover_after_one_unproven_world_sample(monkeypatch):
    from collections import Counter
    from dsac29.geometry_registry import GeometryRegistry
    a,b=_repeated_150(extra=True)
    calls=[]
    # Separate exporter definitions share no serialization shortcut.
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *args:False)
    def proof(*args,**kwargs):
        calls.append(1)
        # First old-world/face proof is inconclusive. A different occurrence
        # is independently proven; only then may all copies reuse the anchor.
        return len(calls)>=3
    monkeypatch.setattr(comparator,'guarded_world_equivalent',proof)
    monkeypatch.setattr(comparator,'guarded_world_reexport',proof)
    records=comparator.compare(a,b,revision_only=True,exact_serialization=False)
    counts=Counter(r.status for r in records)
    assert counts['SAME']==150,counts
    assert counts['ADDED']==1 and counts['UNCERTAIN']==0,counts
    assert len(calls)==3, 'Do not run 150 independent native Booleans'


def test_one_native_timeout_cannot_poison_150_repeated_occurrences(monkeypatch):
    from collections import Counter
    from dsac29.geometry_registry import GeometryRegistry
    a,b=_repeated_150()
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *args:False)
    tries=[]
    def occasionally_crashes(*args,**kwargs):
        tries.append(1)
        if len(tries)==1:
            raise native_guard.NativeGeometryFailure('OCC transient worker error')
        return True
    monkeypatch.setattr(comparator,'guarded_world_equivalent',occasionally_crashes)
    monkeypatch.setattr(comparator,'guarded_world_reexport',occasionally_crashes)
    records=comparator.compare(a,b,revision_only=True,exact_serialization=False)
    assert Counter(r.status for r in records)=={'SAME':150}
    assert len(tries)==2


def test_completed_native_nonmatches_cannot_certify_repeated_occurrences(monkeypatch):
    from collections import Counter
    from dsac29.geometry_registry import GeometryRegistry
    a,b=_repeated_150()
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *args:False)
    calls=[]
    def unverified(*args,**kwargs):
        calls.append(1)
        return False
    monkeypatch.setattr(comparator,'guarded_world_equivalent',unverified)
    monkeypatch.setattr(comparator,'guarded_world_reexport',unverified)
    result=comparator.compare(a,b,revision_only=True,exact_serialization=False)
    assert not any(r.status in ('SAME','RENAMED') for r in result)
    # A completed native False is a negative outcome, not a timeout.
    # It must never certify SAME; status UNCERTAIN is reserved for actual
    # unfinished/failing CAD calls, not mandatory for a finished False.
    assert len(calls)>3, 'Completed nonmatches must not poison the whole repeated family'
    assert len(calls)<=300, 'All hypotheses must remain bounded by the source occurrences'


def test_four_native_failures_abort_without_publishing_unverified_same(monkeypatch):
    """Real native failures (unlike completed False) fail closed."""
    import pytest
    from dsac29.geometry_registry import GeometryRegistry
    # Four independent world-position candidates. A single repeated
    # definition deliberately stops retrying after three native crashes,
    # so using 150 copies of ONE family cannot exercise the global
    # four-failure fail-closed policy.
    a=[_part(i*30,'P') for i in range(4)]+[
        _part(10000+i*50,'old'+str(i)) for i in range(76)]
    b=[_part(i*30,'P') for i in range(4)]+[
        _part(100000+i*50,'new'+str(i)) for i in range(76)]
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *args:False)
    tries=[]
    def crashed_worker(*args,**kwargs):
        tries.append(1)
        raise native_guard.NativeGeometryFailure('synthetic OCC worker timeout')
    monkeypatch.setattr(comparator,'guarded_world_equivalent',crashed_worker)
    monkeypatch.setattr(comparator,'guarded_world_reexport',crashed_worker)
    with pytest.raises(native_guard.NativeGeometryFailure,match='4 nieukończonych'):
        comparator.compare(a,b,revision_only=True,exact_serialization=False)
    assert len(tries)==4, 'Native failure policy must be bounded'


def test_failed_local_positions_cannot_poison_147_true_matches(monkeypatch):
    from collections import Counter
    from dataclasses import replace
    from dsac29.alignment import _relocate
    from dsac29.geometry_registry import GeometryRegistry
    a,b=_repeated_150()
    # Three locally moved occurrences are not grounds for rejecting
    # the remaining 147 identical-world-position copies.
    b[:3]=[_relocate(b[i],np.eye(3),np.array([.2,0.,0.])) for i in range(3)]
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *args:False)
    calls=[]
    def native_world(left,right,*args,**kwargs):
        calls.append(1)
        return bool(np.linalg.norm(left.center-right.center)<.01)
    monkeypatch.setattr(comparator,'guarded_world_equivalent',native_world)
    monkeypatch.setattr(comparator,'guarded_world_reexport',native_world)
    result=comparator.compare(a,b,revision_only=True,exact_serialization=False)
    counts=Counter(r.status for r in result)
    assert counts['SAME']>=147,counts
    assert all(r.status not in ('SAME','RENAMED') or
               (r.a_index not in (0,1,2) and r.b_index not in (0,1,2))
               for r in result)
    assert len(calls)<=8,'147 unchanged instances should reuse native positive anchor'
