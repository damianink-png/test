import json
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.compare import Record
from dsac29 import cli,cad_registration


def mixed_scene(extra=0,repeated=False,local_mm=220.):
    shift=np.array([1700.,-250.,90.]);a=[];b=[]
    for i in range(8):
        dims=(20,13,7) if repeated else (20+i*3,13+i,7+i*.3)
        part=describe(BRepPrimAPI_MakeBox(*dims).Shape(),f'PART_{i}_REV_A','old')
        pos=np.array([i*77.,(i*i%17)*41.,i%3*51.])
        old=_relocate(part,np.eye(3),pos);a.append(old)
        local=np.array([0.,local_mm,0.]) if i>=6 else np.zeros(3)
        b.append(_relocate(describe(part.shape,f'PART_{i}_REV_B','new'),np.eye(3),pos+shift+local))
    for i in range(extra):
        a.append(_relocate(describe(BRepPrimAPI_MakeBox(3+i*.01,4,5).Shape(),f'OLD_{i}','old'),np.eye(3),np.array([i*35.,1500.,0.])))
        b.append(_relocate(describe(BRepPrimAPI_MakeBox(60+i,70,80).Shape(),f'NEW_{i}','new'),np.eye(3),np.array([10000.+i*100.,10000.,10000.])))
    rows=[Record(i,None,'REMOVED','') for i in range(len(a))]+[Record(None,j,'ADDED','') for j in range(len(b))]
    return a,b,rows,shift


def test_six_unique_coherent_anchors_survive_two_local_moves_in_large_changed_assembly():
    a,b,rows,t=mixed_scene(extra=72)
    result=cad_registration.propose(a,b,rows,.01)
    assert result['status']=='registered',result
    assert result['votes']==6 and result['requires_confirmation'] is True
    assert result['translation_B_to_A_mm']==pytest.approx(-t,abs=1e-6)
    assert set(map(tuple,result['certified_pairs']))=={(i,i) for i in range(6)}
    assert result['full_pair_map']==[]


@pytest.mark.parametrize('repeated',[False,True])
def test_approved_global_frame_keeps_two_local_moves_as_moved(tmp_path,monkeypatch,repeated):
    a,b,_,t=mixed_scene(repeated=repeated)
    pa=tmp_path/'old.step';pb=tmp_path/'new.step';pa.write_text('old');pb.write_text('new')
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p==pa else b)
    questions=[]
    def approve(p):questions.append(p);return 'align'
    cli.process(pa,pb,tmp_path/'result',step=False,diff_step=False,full_bom=False,
                revision_style=True,auto_align=True,alignment_approval=approve,progress=None)
    data=json.loads((tmp_path/'result/PODSUMOWANIE.json').read_text())
    assert data['statuses']=={'SAME':6,'MOVED':2},data['statuses']
    assert data['alignment']['applied'] and data['alignment']['translation_B_to_A_mm']==pytest.approx(-t)
    rows=data['records']
    moved=[r for r in rows if r['status']=='MOVED']
    assert len(moved)==2 and all(abs(r['delta_y']-220.)<1e-5 for r in moved)
    assert data['revision_overlap']['boolean_checks']==0


def test_large_sparse_frame_requires_approval_and_finishes_local_motion(tmp_path,monkeypatch):
    a,b,_,t=mixed_scene(extra=72)
    pa=tmp_path/'old.step';pb=tmp_path/'new.step';pa.write_text('old');pb.write_text('new')
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p==pa else b)
    questions=[]
    cli.process(pa,pb,tmp_path/'result',step=False,diff_step=False,full_bom=False,
                revision_style=True,auto_align=True,alignment_approval=lambda p:(questions.append(p) or 'align'),progress=None)
    data=json.loads((tmp_path/'result/PODSUMOWANIE.json').read_text())
    assert len(questions)==1 and questions[0]['votes']==6
    assert data['statuses']=={'SAME':6,'MOVED':2,'REMOVED':72,'ADDED':72}


def test_unique_translation_anchors_do_not_require_noncollinear_centers():
    a,b,rows,t=mixed_scene(extra=72)
    for i in range(8):
        offset=np.array([0.,-a[i].center[1],-a[i].center[2]])
        a[i]=_relocate(a[i],np.eye(3),offset)
        b[i]=_relocate(b[i],np.eye(3),offset)
    result=cad_registration.propose(a,b,rows,.01)
    assert result['status']=='registered' and result['requires_confirmation']
    assert result['votes']==6 and result['translation_B_to_A_mm']==pytest.approx(-t)


def test_two_local_moves_without_global_shift_do_not_relocate_assembly(tmp_path,monkeypatch):
    a,b,_,t=mixed_scene(repeated=True)
    b=[_relocate(p,np.eye(3),-t) for p in b]
    pa=tmp_path/'old.step';pb=tmp_path/'new.step';pa.write_text('old');pb.write_text('new')
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p==pa else b)
    def forbidden(p):pytest.fail('Local part moves must not require a global relocation')
    cli.process(pa,pb,tmp_path/'result',step=False,diff_step=False,full_bom=False,
                revision_style=True,auto_align=True,alignment_approval=forbidden,progress=None)
    data=json.loads((tmp_path/'result/PODSUMOWANIE.json').read_text())
    assert data['statuses']=={'SAME':6,'MOVED':2}
    assert not data['alignment'].get('applied')


def test_six_anchor_frame_is_not_applied_without_approval(tmp_path,monkeypatch):
    a,b,_,_=mixed_scene(extra=72)
    pa=tmp_path/'old.step';pb=tmp_path/'new.step';pa.write_text('old');pb.write_text('new')
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p==pa else b)
    with pytest.raises(InterruptedError):
        cli.process(pa,pb,tmp_path/'result',step=False,diff_step=False,full_bom=False,
                    revision_style=True,auto_align=True,alignment_approval=lambda p:'cancel',progress=None)
    assert not (tmp_path/'result/PODSUMOWANIE.json').exists()


def test_six_of_eight_world_proofs_accept_outliers_without_unique_seed():
    a,b,rows,t=mixed_scene(extra=72,repeated=True,local_mm=.04)
    result=cad_registration.propose(a,b,rows,.01)
    assert result['status']=='registered',result
    assert result['votes']==6 and result['requires_confirmation'] is True
    assert result['initial_position_candidate_count']==8
    assert result['initial_world_proof_count']==6
    assert len(result['certified_pairs'])==6
    assert result['translation_B_to_A_mm']==pytest.approx(-t,abs=1e-6)


def test_small_local_outliers_do_not_bias_final_global_vector_or_motion(tmp_path,monkeypatch):
    a,b,_,t=mixed_scene(extra=72,repeated=True,local_mm=.04)
    pa=tmp_path/'old.step';pb=tmp_path/'new.step';pa.write_text('old');pb.write_text('new')
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p==pa else b)
    cli.process(pa,pb,tmp_path/'result',step=False,diff_step=False,full_bom=False,
                revision_style=True,auto_align=True,alignment_approval=lambda p:'align',progress=None)
    data=json.loads((tmp_path/'result/PODSUMOWANIE.json').read_text())
    assert data['statuses']=={'SAME':6,'MOVED':2,'REMOVED':72,'ADDED':72}
    assert data['alignment']['translation_B_to_A_mm']==pytest.approx(-t,abs=1e-6)
    assert data['alignment']['final_moved_count']==2
    assert all(r['delta_y']==pytest.approx(.04,abs=1e-6) for r in data['records'] if r['status']=='MOVED')
