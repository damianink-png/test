import json
from dataclasses import replace
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_FACE,TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.native_session import world_session
from dsac29.native_guard import guarded_world_reexport,guarded_registered_world
from dsac29 import cli


def count(shape,kind):
    ex=TopExp_Explorer(shape,kind);n=0
    while ex.More():n+=1;ex.Next()
    return n


def shapes(split=4.):
    old=BRepPrimAPI_MakeBox(20,30,5).Shape()
    left=BRepPrimAPI_MakeBox(split,30,5).Shape()
    right=BRepPrimAPI_MakeBox(gp_Pnt(split,0,0),20-split,30,5).Shape()
    new=BRepAlgoAPI_Fuse(left,right).Shape()
    assert count(old,TopAbs_FACE)!=count(new,TopAbs_FACE)
    assert count(old,TopAbs_SOLID)==count(new,TopAbs_SOLID)==1
    return old,new


def test_valid_same_material_with_split_faces_uses_independent_directional_cuts():
    left,right=shapes()
    a=describe(left,'A','A');b=describe(right,'B','B')
    with world_session(True):
        assert guarded_world_reexport(a,b,.01,allow_boolean=False) is False
        assert guarded_registered_world(a,b,.01,allow_boolean=False) is True


def test_solid_proof_rejects_different_material_despite_equal_fake_properties():
    a=describe(BRepPrimAPI_MakeBox(10,12,10).Shape(),'A','A')
    other=describe(BRepPrimAPI_MakeBox(12,10,10).Shape(),'B','B')
    other=replace(other,volume=a.volume,area=a.area,inertia=a.inertia,eigenvalues=a.eigenvalues)
    with world_session(True):
        assert guarded_registered_world(a,other,.01,allow_boolean=False) is False


@pytest.mark.parametrize('split',[4.,10.])
def test_translated_same_revision_with_repartitioned_faces_finishes_as_same(tmp_path,monkeypatch,split):
    left,right=shapes(split);a=[];b=[];shift=np.array([1000.,250.,-50.])
    for i in range(8):
        pos=np.array([i*57.,i*i*3.,(i%3)*40.])
        a.append(_relocate(describe(left,'PLATE_123_REV_A','old'),np.eye(3),pos))
        b.append(_relocate(describe(right,'PLATE_123_REV_B','new'),np.eye(3),pos+shift))
    pa=tmp_path/'a.step';pb=tmp_path/'b.step';pa.write_text('old');pb.write_text('new')
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p==pa else b)
    questions=[]
    def approve(p):questions.append(p);return 'align'
    cli.process(pa,pb,tmp_path/'result',step=False,diff_step=False,full_bom=False,
                revision_style=True,auto_align=True,alignment_approval=approve,progress=None)
    data=json.loads((tmp_path/'result/PODSUMOWANIE.json').read_text())
    assert data['statuses']=={'SAME':8}
    assert data['alignment']['translation_B_to_A_mm']==pytest.approx(-shift,abs=1e-5)
    assert data['alignment']['applied']
    if questions:assert all(p['status']=='registered' for p in questions)
