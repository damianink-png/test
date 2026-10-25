"""RC4 registration: unverified B-Rep must not be marked SAME."""
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.registration_gate import frame_support
from dsac29 import native_guard
from dsac29.geometry_registry import GeometryRegistry

def assemblies():
    a0=describe(BRepPrimAPI_MakeBox(10,12,14).Shape(),'base','base')
    b0=describe(BRepPrimAPI_MakeBox(10,12,14).Shape(),'base','base')
    a=[];b=[]
    for i in range(601):
        offset=np.array([float(i)*50,0,0])
        left=_relocate(a0,np.eye(3),offset);left.name=str(i)
        right=_relocate(b0,np.eye(3),offset);right.name=str(i)
        a.append(left);b.append(right)
    return a,b

def no_digest(monkeypatch):
    monkeypatch.setattr(GeometryRegistry,'definition',lambda self,part:id(part))
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda self,a,b:False)

def test_one_timeout_never_certified(monkeypatch):
    a,b=assemblies();no_digest(monkeypatch)
    def flaky(left,right,tol,**kwargs):
        if left.name=='333':raise native_guard.NativeGeometryFailure('simulated timeout')
        return True
    monkeypatch.setattr(native_guard,'guarded_world_reexport',flaky)
    proof=frame_support(a,b,.01,verify_all=True)
    assert proof['unverified']==1
    assert proof['count']==600
    assert (333,333) not in proof['pairs']
    assert (334,334) in proof['pairs']

def test_many_timeouts_fail_closed(monkeypatch):
    a,b=assemblies();no_digest(monkeypatch)
    def fail(*args,**kwargs):raise native_guard.NativeGeometryFailure('simulated timeout')
    monkeypatch.setattr(native_guard,'guarded_world_reexport',fail)
    with pytest.raises(native_guard.NativeGeometryFailure,match='niezweryfikowanych'):
        frame_support(a,b,.01,verify_all=True)
