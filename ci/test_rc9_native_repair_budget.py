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
        return True
    monkeypatch.setattr(step_reexport_tolerance,'reexport_equivalent_world',prove)
    req=tmp_path/'request.json';out=tmp_path/'reply.json'
    req.write_text(json.dumps({'operation':'world_reexport','a':'A.brep','b':'B.brep','tolerance':0.01,'allow_boolean':True}))
    assert native_guard.worker(str(req),str(out))==0
    assert json.loads(out.read_text())=={'ok':True,'match':True}
    assert [x[2] for x in calls[:2]]==[0.005,0.005]
    assert calls[2][1] is repaired_a and calls[2][2] is repaired_b
    assert calls[2][3]==0.005
    assert calls[2][4]['allow_boolean'] is False
    assert calls[2][4]['_repair_boundary_only'] is False
