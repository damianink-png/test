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
