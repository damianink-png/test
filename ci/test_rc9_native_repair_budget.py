"""Invalid B-Reps must be proved using independently verified repaired copies."""
import json
from types import SimpleNamespace
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29 import native_guard, brep_safety, geometry, step_reexport_tolerance


def test_repaired_copies_are_used_with_conserved_budget(tmp_path,monkeypatch):
    original_a=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    original_b=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    repaired_a=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    repaired_b=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    inputs=iter((original_a,original_b))
    monkeypatch.setattr(native_guard,'_load_brep',lambda _:next(inputs))
    monkeypatch.setattr(brep_safety,'is_valid',lambda shape:False)
    calls=[]
    def repair(shape,tolerance):
        calls.append(('repair',shape,tolerance))
        return (repaired_a if shape is original_a else repaired_b),True
    monkeypatch.setattr(brep_safety,'validated_copy',repair)
    monkeypatch.setattr(geometry,'describe',lambda shape,*args:SimpleNamespace(shape=shape))
    def prove(a,b,tolerance,**kwargs):
        calls.append(('prove',a.shape,b.shape,tolerance,kwargs))
        return kwargs.get('_repair_boundary_only') is False
    monkeypatch.setattr(step_reexport_tolerance,'reexport_equivalent_world',prove)
    req=tmp_path/'request.json';out=tmp_path/'reply.json'
    req.write_text(json.dumps({'operation':'world_reexport','a':'A.brep','b':'B.brep','tolerance':0.01,'allow_boolean':True}))
    assert native_guard.worker(str(req),str(out))==0
    assert json.loads(out.read_text())=={'ok':True,'match':True}
    assert calls[0][0]=='prove' and calls[0][3]==0.01
    assert calls[0][4]['_repair_boundary_only'] is True
    assert [x[2] for x in calls[1:3]]==[0.005,0.005]
    assert calls[3][1] is repaired_a and calls[3][2] is repaired_b
    assert calls[3][3]==0.005
    assert calls[3][4]['allow_boolean'] is False
    assert calls[3][4]['_repair_boundary_only'] is False


def test_identical_invalid_boundaries_skip_repairs(tmp_path,monkeypatch):
    first=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    second=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    inputs=iter((first,second))
    monkeypatch.setattr(native_guard,'_load_brep',lambda _:next(inputs))
    monkeypatch.setattr(brep_safety,'is_valid',lambda _:False)
    monkeypatch.setattr(brep_safety,'validated_copy',
        lambda *args:(_ for _ in ()).throw(AssertionError('Unexpected repair')))
    monkeypatch.setattr(geometry,'describe',lambda shape,*args:SimpleNamespace(shape=shape))
    proofs=[]
    def strict(a,b,tolerance,**kw):
        proofs.append((a.shape,b.shape,tolerance,kw))
        return True
    monkeypatch.setattr(step_reexport_tolerance,'reexport_equivalent_world',strict)
    req=tmp_path/'request.json';out=tmp_path/'reply.json'
    req.write_text(json.dumps({'operation':'world_reexport','a':'A.brep','b':'B.brep','tolerance':0.01,'allow_boolean':True}))
    assert native_guard.worker(str(req),str(out))==0
    assert json.loads(out.read_text())=={'ok':True,'match':True}
    assert len(proofs)==1 and proofs[0][0] is first and proofs[0][1] is second
    assert proofs[0][2]==0.01
    assert proofs[0][3]['allow_boolean'] is False
    assert proofs[0][3]['_repair_boundary_only'] is True


def test_one_invalid_shape_never_uses_direct_fastpath(tmp_path,monkeypatch):
    a=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    b=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    inputs=iter((a,b))
    monkeypatch.setattr(native_guard,'_load_brep',lambda _:next(inputs))
    monkeypatch.setattr(brep_safety,'is_valid',lambda shape:shape is b)
    repaired=BRepPrimAPI_MakeBox(10.,10.,10.).Shape()
    monkeypatch.setattr(brep_safety,'validated_copy',lambda shape,tol:(repaired if shape is a else shape,shape is a))
    monkeypatch.setattr(geometry,'describe',lambda shape,*args:SimpleNamespace(shape=shape))
    proofs=[]
    def strict(left,right,tol,**kwargs):
        proofs.append((left.shape,right.shape,tol,kwargs))
        return False
    monkeypatch.setattr(step_reexport_tolerance,'reexport_equivalent_world',strict)
    req=tmp_path/'request.json';out=tmp_path/'reply.json'
    req.write_text(json.dumps({'operation':'world_reexport','a':'A.brep','b':'B.brep','tolerance':0.01}))
    assert native_guard.worker(str(req),str(out))==0
    assert json.loads(out.read_text())=={'ok':True,'match':False}
    assert len(proofs)==1 and proofs[0][2]==0.005
    assert proofs[0][3]['_repair_boundary_only'] is False
