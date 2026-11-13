from pathlib import Path
import json
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.compare import Record
from dsac29 import cad_pose_search,cli,deferred_alignment,surface_registration
from dsac29.registration_search import RegistrationSearch


def changed_assembly(shift=(1000.,250.,-50.),rotated=False,count=8):
    old=BRepPrimAPI_MakeBox(20,30,5).Shape()
    tool=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(6,9,-1),gp_Dir(0,0,1)),2.,7.).Shape()
    new=BRepAlgoAPI_Cut(old,tool).Shape()
    a=[];b=[]
    rotation=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]]) if rotated else np.eye(3)
    for i in range(count):
        position=np.array([i*57.,i*i*3.,(i%3)*40.])
        a.append(_relocate(describe(old,'PLATE_123_REV_A','old'),np.eye(3),position))
        part=_relocate(describe(new,'PLATE_123_REV_B','new'),np.eye(3),position)
        b.append(_relocate(part,rotation,np.array(shift)))
    records=[Record(i,None,'REMOVED','') for i in range(count)]+[Record(None,j,'ADDED','') for j in range(count)]
    return a,b,records,rotation,np.array(shift)


@pytest.mark.parametrize('rotated',[False,True])
def test_all_bodies_changed_but_preserved_original_faces_establish_frame(rotated):
    a,b,records,r,t=changed_assembly(rotated=rotated)
    result=deferred_alignment.propose(a,b,records,.01)
    assert result and result['status']=='registered',result
    assert result['method']=='preserved_native_faces'
    assert result['requires_confirmation'] is True
    assert result['surface_anchor_count']>=8 and result['surface_parts_a']>=4
    assert result['certified_pairs']==[] and result['full_pair_map']==[]
    rr=np.asarray(result['rotation_B_to_A']);tt=np.asarray(result['translation_B_to_A_mm'])
    assert rr@r==pytest.approx(np.eye(3),abs=1e-6)
    assert rr@t+tt==pytest.approx(np.zeros(3),abs=1e-6)


def test_changed_bodies_in_original_frame_need_no_relocation_confirmation():
    a,b,_,_,_=changed_assembly(shift=(0,0,0))
    state=RegistrationSearch();state.bind(a,b,.01)
    state.features=(cad_pose_search.landmarks(a),cad_pose_search.landmarks(b))
    result=surface_registration.propose(a,b,.01,state)
    assert result['status']=='already_aligned'
    assert not result['requires_confirmation'] and result['certified_pairs']==[]


def test_face_worker_rejects_changed_trimming_even_on_same_supporting_plane(tmp_path):
    from dsac29.native_session import world_session
    a,b,_,_,_=changed_assembly(shift=(0,0,0))
    state=RegistrationSearch();state.bind(a,b,.01)
    with world_session(True):
        fa=surface_registration._features(a,cad_pose_search.landmarks(a),tmp_path/'a',surface_registration.monotonic()+30,None)
        fb=surface_registration._features(b,cad_pose_search.landmarks(b),tmp_path/'b',surface_registration.monotonic()+30,None)
        left=next(f for f in fa if f['direction'] and abs(f['direction'][2])>.99)
        right=next(f for f in fb if f['direction'] and abs(f['direction'][2])>.99 and f['kind'][1]>1)
        data=surface_registration._run(dict(operation='registration_face_proofs',tolerance=.01,
            rotation=np.eye(3).tolist(),translation=[0.,0.,0.],pairs=[dict(a=left,b=right)]),tmp_path,15)
    assert data['matches']==[False]


def test_surface_native_failure_never_becomes_whole_body_equality(monkeypatch):
    from dsac29.native_guard import NativeGeometryFailure
    a,b,_,_,_=changed_assembly();state=RegistrationSearch();state.bind(a,b,.01)
    state.features=(cad_pose_search.landmarks(a),cad_pose_search.landmarks(b))
    def failure(*args,**kwargs):raise NativeGeometryFailure('synthetic native timeout')
    monkeypatch.setattr(surface_registration,'_run',failure)
    result=surface_registration.propose(a,b,.01,state)
    assert result['status']=='unresolved' and not result.get('certified_pairs')


def test_whole_revision_still_compares_material_after_surface_frame_approval(tmp_path,monkeypatch):
    a,b,_,_,_=changed_assembly();pa=tmp_path/'a.step';pb=tmp_path/'b.step'
    pa.write_text('old');pb.write_text('new')
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p==pa else b)
    questions=[]
    def approve(proposal):questions.append(proposal);return 'align'
    cli.process(pa,pb,tmp_path/'result',step=False,diff_step=False,full_bom=False,
                revision_style=True,auto_align=True,alignment_approval=approve,progress=None)
    data=json.loads((tmp_path/'result/PODSUMOWANIE.json').read_text())
    assert len(questions)==1 and questions[0]['method']=='preserved_native_faces'
    assert data['alignment']['applied'] and data['statuses']=={'CHANGED':8}
    assert data['alignment']['certified_pairs']==[]


def test_extended_surface_search_still_asks_before_applying_frame(tmp_path,monkeypatch):
    a,b,_,_,_=changed_assembly();pa=tmp_path/'a.step';pb=tmp_path/'b.step';pa.write_text('old');pb.write_text('new')
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p==pa else b)
    def initial(left,right,matched,fa,fb,tol,*args,search_state=None,**kw):
        search_state.bind(left,right,tol);search_state.stage1_records=list(matched)
        search_state.free_a=fa;search_state.free_b=fb
        return {'status':'unresolved','reason':'initial search incomplete'}
    monkeypatch.setattr(deferred_alignment,'propose_from_stage1',initial)
    questions=[]
    def answer(proposal):questions.append(proposal);return 'cancel'
    with pytest.raises(InterruptedError):
        cli.process(pa,pb,tmp_path/'result',step=False,diff_step=False,full_bom=False,
                    revision_style=True,auto_align=True,alignment_approval=answer,progress=None)
    assert len(questions)==1 and questions[0]['method']=='preserved_native_faces'
    assert not (tmp_path/'result/PODSUMOWANIE.json').exists()


def test_refused_surface_pose_does_not_mark_original_coordinates_as_verified(tmp_path,monkeypatch):
    a,b,_,_,_=changed_assembly();pa=tmp_path/'a.step';pb=tmp_path/'b.step'
    pa.write_text('old');pb.write_text('new')
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p==pa else b)
    original_compare=cli.compare;frames=[]
    def compare(*args,**kwargs):
        frames.append(kwargs.get('registered_frame',False))
        return original_compare(*args,**kwargs)
    monkeypatch.setattr(cli,'compare',compare)
    cli.process(pa,pb,tmp_path/'result',step=False,diff_step=False,full_bom=False,
                revision_style=True,auto_align=True,alignment_approval=lambda p:'original',progress=None)
    data=json.loads((tmp_path/'result/PODSUMOWANIE.json').read_text())
    assert not data['alignment']['applied']
    assert frames==[False,False]
    assert data['statuses']=={'REMOVED':8,'ADDED':8}
