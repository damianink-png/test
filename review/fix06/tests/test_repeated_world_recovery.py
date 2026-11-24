from collections import Counter
from dataclasses import replace
import numpy as np
import pytest
from dsac29 import native_guard
from dsac29.compare import compare
from dsac29.alignment import _relocate
from dsac29.repeated_world_recovery import RepeatedWorldRecovery
from test_repeated_revision_policy import parts


def test_fixed_frame_recovery_preserves_relative_placement_and_inputs(monkeypatch):
    a=parts(count=3,shift=2000);b=parts(count=3,shift=2000.04)
    before=[p.center.copy() for p in a+b]
    calls=[]
    def prove(left,right,tol,**kw):
        calls.append(kw)
        assert np.allclose(right.center-left.center,b[0].center-a[0].center)
        assert np.linalg.norm((left.center+right.center)*.5)<1e-8
        return False
    monkeypatch.setattr(native_guard,'guarded_registered_world',prove)
    recovery=RepeatedWorldRecovery(a,b,[0]*3,[1]*3,.01)
    assert recovery.recover(0,0,'timeout') is False
    assert recovery.recover(1,1,'timeout') is None
    assert recovery.recover(0,2,'timeout') is None
    assert calls==[{'timeout_s':75.0}]
    assert all(np.array_equal(p.center,c) for p,c in zip(a+b,before))


@pytest.mark.parametrize('verdict',[True,False,None])
def test_world_timeout_recovers_repeats_only_with_complete_native_proof(monkeypatch,verdict):
    import dsac29.compare as engine
    a=parts(count=120,shift=2000);b=parts(count=120,shift=2000)
    b[-1]=_relocate(b[-1],np.eye(3),np.array([1000.,0.,0.]))
    calls=[]
    def timeout(*args,**kw):raise native_guard.NativeGeometryFailure('timeout original world')
    def recovery(left,right,tol,**kw):
        calls.append(1)
        if verdict is None:raise native_guard.NativeGeometryFailure('timeout recovery')
        return verdict
    monkeypatch.setattr(engine,'guarded_world_equivalent',timeout)
    monkeypatch.setattr(engine,'guarded_world_reexport',timeout)
    monkeypatch.setattr(engine,'guarded_registered_world',timeout)
    monkeypatch.setattr(native_guard,'guarded_registered_world',recovery)
    rows=compare(a,b,revision_only=True,exact_serialization=False)
    expected=({'SAME':119,'REMOVED':1,'ADDED':1} if verdict is True
              else {'UNCERTAIN':238,'REMOVED':1,'ADDED':1})
    assert Counter(r.status for r in rows)==expected
    assert len(calls)==1


def test_unique_and_non_timeout_pairs_do_not_launch_recovery(monkeypatch):
    a=parts(count=2);b=parts(count=2)
    def forbidden(*args,**kw):raise AssertionError('No recovery warranted')
    monkeypatch.setattr(native_guard,'guarded_registered_world',forbidden)
    assert RepeatedWorldRecovery(a,b,[0,1],[2,3],.01).recover(0,0,'timeout') is None
    assert RepeatedWorldRecovery(a,b,[0,0],[1,1],.01).recover(0,0,'invalid topology') is None


def test_real_analytic_and_nurbs_pair_keeps_local_motion_visible():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    from dsac29.geometry import describe
    shape=BRepPrimAPI_MakeBox(20.,10.,7.).Shape()
    other=BRepBuilderAPI_NurbsConvert(shape,True).Shape()
    a=[_relocate(describe(shape,'old','old'),np.eye(3),np.array([2000.+100*i,3000.,410.])) for i in range(2)]
    b=[_relocate(describe(other,'new','new'),np.eye(3),np.array([2000.+100*i,3000.,410.])) for i in range(2)]
    recovery=RepeatedWorldRecovery(a,b,[0,0],[1,1],.01)
    assert recovery.recover(0,0,'timeout') is True
    moved=[_relocate(p,np.eye(3),np.array([0.,.2,0.])) for p in b]
    recovery=RepeatedWorldRecovery(a,moved,[0,0],[1,1],.01)
    assert recovery.recover(0,0,'timeout') is not True



@pytest.mark.parametrize("alternate_proves", [False, True])
def test_exhausted_solid_difference_has_one_alternate_copy(monkeypatch, alternate_proves):
    import dsac29.compare as engine
    a=parts(count=120,shift=2000);b=parts(count=120,shift=2000)
    b[-1]=_relocate(b[-1],np.eye(3),np.array([1000.,0.,0.]))
    calls=[]
    def timeout(*args,**kw):
        calls.append(1)
        raise native_guard.NativeGeometryFailure(
            'Timeout odizolowanej weryfikacji STEP; etap: validated_solid_symmetric_difference')
    def alternative(left,right,tolerance,**kw):
        calls.append(2)
        assert kw['timeout_s']==30.
        assert kw['operation']=='world_fixed_partition'
        assert np.allclose(left.center+right.center,0.)
        return alternate_proves
    monkeypatch.setattr(engine,'guarded_world_equivalent',timeout)
    monkeypatch.setattr(engine,'guarded_world_reexport',timeout)
    monkeypatch.setattr(engine,'guarded_registered_world',timeout)
    monkeypatch.setattr(native_guard,'guarded_world_reexport',alternative)
    monkeypatch.setattr(native_guard,'guarded_rigid',lambda *args,**kw:(False,None,None))
    rows=compare(a,b,revision_only=True,exact_serialization=False)
    expected={'SAME':119} if alternate_proves else {'UNCERTAIN':238}
    assert Counter(r.status for r in rows)==dict(expected,REMOVED=1,ADDED=1)
    assert calls==[1,2]


def test_failed_relative_pose_does_not_block_an_independent_pose(monkeypatch):
    import dsac29.compare as engine
    a=parts(count=120,shift=2000);b=parts(count=120,shift=2000)
    b[1]=_relocate(b[1],np.eye(3),np.array([.1,0.,0.]))
    calls=[]
    def proof(left,right,*args,**kw):
        calls.append(float(right.center[0]-left.center[0]))
        if abs(calls[-1])<.01:
            raise native_guard.NativeGeometryFailure('Timeout; etap: validated_solid_symmetric_difference')
        return False
    monkeypatch.setattr(engine,'guarded_world_equivalent',proof)
    monkeypatch.setattr(engine,'guarded_world_reexport',proof)
    monkeypatch.setattr(native_guard,'guarded_world_reexport',proof)
    monkeypatch.setattr(native_guard,'guarded_rigid',lambda *args,**kw:(False,None,None))
    rows=compare(a,b,revision_only=True,exact_serialization=False)
    assert any(abs(x-.1)<1e-6 for x in calls)
    assert not any(r.status in ('SAME','RENAMED') for r in rows)

@pytest.mark.parametrize('rotation,translation,expected',[
    (np.eye(3),np.zeros(3),True),
    (np.eye(3),np.array([0.,.04,0.]),False),
    (np.diag([-1.,-1.,1.]),np.zeros(3),False),
])
def test_representative_rigid_witness_requires_original_pose(monkeypatch,rotation,translation,expected):
    a=parts(count=3); b=parts(count=3)
    calls=[]
    def witness(*args,**kw):
        calls.append(1)
        if kw.get("repeated_cells"):
            return False,None,None
        return True,rotation,translation
    monkeypatch.setattr(native_guard,'guarded_rigid',witness)
    policy=RepeatedWorldRecovery(a,b,[0]*3,[1]*3,.01)
    assert policy.recover(0,0,'Timeout original_equivalent_world') is expected
    assert policy.recover(1,1,'Timeout original_equivalent_world') is None
    assert len(calls)==2

def test_real_rigid_witness_for_stationary_repeated_boxes():
    a=parts(count=3); b=parts(count=3,separate=True)
    policy=RepeatedWorldRecovery(a,b,[0]*3,[1]*3,.01)
    assert policy.recover(0,0,'Timeout original_equivalent_world') is True


def test_shared_material_cells_at_fixed_pose():
    from dsac29.shared_cells import same_material_cells
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    from OCP.gp import gp_Pnt
    old=BRepPrimAPI_MakeBox(20.,10.,7.).Shape()
    assert same_material_cells(old,BRepBuilderAPI_NurbsConvert(old,True).Shape(),.01)
    for new in [BRepPrimAPI_MakeBox(gp_Pnt(.04,0,0),20.,10.,7.).Shape(),
                BRepPrimAPI_MakeBox(10.,20.,7.).Shape(),
                BRepPrimAPI_MakeBox(20.,10.,6.9).Shape()]:
        assert not same_material_cells(old,new,.01)


def test_fixed_cells_timeout_leaves_time_for_rigid_witness(monkeypatch):
    a,b=parts(count=3),parts(count=3)
    calls=[]
    def witness(*args,**kw):
        calls.append(kw)
        if kw.get('repeated_cells'):
            raise native_guard.NativeGeometryFailure('timeout')
        return True,np.eye(3),np.zeros(3)
    monkeypatch.setattr(native_guard,'guarded_rigid',witness)
    policy=RepeatedWorldRecovery(a,b,[0]*3,[1]*3,.01)
    assert policy.recover(0,0,'Timeout original_equivalent_world')
    assert len(calls)==2 and calls[0]['timeout_s']==45.
    assert 0<calls[1]['timeout_s']<=40.


def test_rigid_motion_shares_shape_proof_without_confirming_pose(monkeypatch):
    from dsac29.geometry_registry import GeometryRegistry
    a,b=parts(count=3),parts(count=3,separate=True)
    registry=GeometryRegistry()
    monkeypatch.setattr(native_guard,'guarded_rigid',
                        lambda *args,**kw:(not kw.get("repeated_cells"),np.eye(3),np.array([1.,0.,0.])))
    policy=RepeatedWorldRecovery(a,b,[0]*3,[1]*3,.01,registry)
    assert policy.recover(0,0,'Timeout original_equivalent_world') is False
    assert registry.has_rigid_proof(a[0],b[0],.01)


def test_cells_worker_proves_only_fixed_placement():
    a,b=parts(count=2),parts(count=2,separate=True)
    assert native_guard.guarded_rigid(a[0],b[0],.01,repeated_cells=True)[0]
    moved=_relocate(b[0],np.eye(3),np.array([.2,0.,0.]))
    assert not native_guard.guarded_rigid(a[0],moved,.01,repeated_cells=True)[0]


def test_successful_fixed_cells_skips_rigid_search_and_preserves_missing_copy(monkeypatch):
    import dsac29.compare as engine
    a=parts(count=54,shift=2000)
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from dsac29.geometry import describe
    new=describe(BRepBuilderAPI_NurbsConvert(BRepPrimAPI_MakeBox(20,10,7).Shape(),True).Shape(),'new','new')
    b=[replace(_relocate(new,np.eye(3),part.center-new.center),name=part.name) for part in a]
    b[-1]=_relocate(b[-1],np.eye(3),np.array([1000.,0.,0.]))
    # Use the isolated verification path of a large assembly.
    others=parts(width=15,count=26,shift=50000)
    a.extend(others)
    b.extend(others)
    def timeout(*args,**kw):
        raise native_guard.NativeGeometryFailure('Timeout validated_solid_symmetric_difference')
    for name in ('guarded_world_equivalent','guarded_world_reexport','guarded_registered_world'):
        monkeypatch.setattr(engine,name,timeout)
    original=native_guard.guarded_rigid
    calls=[]
    def fixed(*args,**kw):
        assert kw.get('repeated_cells')
        calls.append(1)
        return original(*args,**kw)
    monkeypatch.setattr(native_guard,'guarded_rigid',fixed)
    rows=compare(a,b,revision_only=True,exact_serialization=False)
    assert Counter(r.status for r in rows)=={'SAME':79,'REMOVED':1,'ADDED':1}
    assert {r.a_index for r in rows if r.status=='REMOVED'}=={53}
    assert {r.b_index for r in rows if r.status=='ADDED'}=={53}
    assert len(calls)==1


def test_fixed_partition_worker_accepts_reexport_and_rejects_changes():
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from dsac29.geometry import describe

    box=BRepPrimAPI_MakeBox(20.,10.,7.).Shape()
    a=describe(box,'old','old')
    b=describe(BRepBuilderAPI_NurbsConvert(box,True).Shape(),'new','new')
    kw={'operation':'world_fixed_partition','timeout_s':30.}
    assert native_guard.guarded_world_reexport(a,b,.01,**kw)
    moved=_relocate(b,np.eye(3),np.array([.04,0.,0.]))
    assert not native_guard.guarded_world_reexport(a,moved,.01,**kw)
    modified=describe(BRepPrimAPI_MakeBox(20.,10.,6.9).Shape(),'modified','modified')
    assert not native_guard.guarded_world_reexport(a,modified,.01,**kw)
