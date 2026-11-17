import pytest
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf, gp_Vec
from dsac29.geometry import describe
from dsac29.step_roundtrip import normalize_pair


def parts(offset=0):
    shape=BRepPrimAPI_MakeBox(10,20,30).Shape()
    result=[]
    for i in range(3):
        tr=gp_Trsf();tr.SetTranslation(gp_Vec(offset+i*50,20,30))
        result.append(describe(shape.Moved(TopLoc_Location(tr)), f'czesc1_afm{i}', f'root/{i}'))
    return result


def test_both_files_and_repeated_occurrences_roundtrip(tmp_path):
    a,b=parts(),parts(130)
    aa,bb,info=normalize_pair(a,b,tmp_path)
    assert info['a'] != info['b']
    for old,new in ((a,aa),(b,bb)):
        assert len(new)==3
        for x,y in zip(old,new):
            assert (x.name,x.path)==(y.name,y.path)
            assert y.volume==pytest.approx(x.volume)
            assert y.center==pytest.approx(x.center)
            assert y is not x
    assert not np.allclose(aa[0].center, bb[0].center)


def test_aligned_pair_reimported_without_losing_local_move(tmp_path):
    a,b=parts(),parts()
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(0,0,5))
    b[2]=describe(b[2].shape.Moved(TopLoc_Location(tr)),b[2].name,b[2].path)
    aa,bb,_=normalize_pair(a,b,tmp_path)
    assert aa[0].center==pytest.approx(bb[0].center)
    assert not np.allclose(aa[2].center,bb[2].center)


def test_cancel_before_export(tmp_path):
    with pytest.raises(InterruptedError):
        normalize_pair(parts(),parts(),tmp_path,cancelled=lambda:True)


def test_process_uses_two_fresh_inputs_and_no_second_alignment(tmp_path, monkeypatch):
    from dsac29 import cli
    from dsac29.step_roundtrip import _write
    source=tmp_path/'source.step'; _write(parts(),source)
    original_compare=cli.compare
    seen=[]
    def compare(a,b,*args,**kwargs):
        seen.append((a,b,kwargs.get('stage1_check')))
        assert a is not b
        assert all(x is not y for x,y in zip(a,b))
        return original_compare(a,b,*args,**kwargs)
    monkeypatch.setattr(cli,'compare',compare)
    folder,records,error=cli.process(str(source),str(source),str(tmp_path/'result'),
        normalize_steps=True,auto_align=True,step=False,full_bom=False,progress=None)
    assert error is None
    assert len(seen)==1 and seen[0][2] is None
    assert all(record.status=='SAME' for record in records)
    assert (folder/'UJEDNOLICENIE_STEP.json').is_file()


@pytest.mark.parametrize('automatic',[False,True])
def test_alignment_exports_both_again_and_discards_old_proofs(tmp_path, monkeypatch,automatic):
    import json
    from dsac29 import cli
    from dsac29.step_roundtrip import _write
    a_path,b_path=tmp_path/'old.step',tmp_path/'new.step'
    _write(parts(),a_path);_write(parts(130),b_path)
    original_compare=cli.compare
    calls=[]
    proposal={'status':'registered','votes':3,'previous_world_matches':0,
              'translation_B_to_A_mm':[-130,0,0], 'rotation_B_to_A':np.eye(3).tolist(),
              'full_pair_map':[(0,0),(1,1),(2,2)],'certified_pairs':[(0,0)]}
    monkeypatch.setattr(cli,'_continue_strong_incomplete_frame',lambda a,b,t,s,p,*args:p)
    def compare(a,b,*args,**kwargs):
        calls.append(kwargs)
        if len(calls)==1:
            assert kwargs['stage1_check'] is not None
            raise cli.ShiftDetected(proposal)
        assert kwargs['stage1_check'] is None
        assert kwargs['geometry_context'] is not calls[0]['geometry_context']
        assert kwargs['certified_pairs']==[]
        for x,y in zip(a,b): assert x.center==pytest.approx(y.center)
        return original_compare(a,b,*args,**kwargs)
    monkeypatch.setattr(cli,'compare',compare)
    def approval(proposal):
        assert not automatic, 'Automatic mode must not open an approval dialog'
        return 'align'
    folder,records,error=cli.process(str(a_path),str(b_path),str(tmp_path/'result'),
        normalize_steps=True,auto_align=True,automatic_alignment=automatic,alignment_approval=approval,
        step=False,full_bom=False,progress=None)
    assert error is None and len(calls)==2
    passes=json.loads((folder/'UJEDNOLICENIE_STEP.json').read_text())
    assert len(passes)==2 and passes[0]['a']!=passes[1]['a']
    assert all(r.status=='SAME' for r in records)
    timing=json.loads((folder/'CZASY_ANALIZY.json').read_text())
    assert timing['final_comparison_after_alignment_s']>0
    assert timing['alignment_preflight_and_optional_registration_s']>=0


def test_reimport_count_loss_is_not_silently_accepted(tmp_path,monkeypatch):
    from dsac29 import step_io
    monkeypatch.setattr(step_io,'load_step',lambda *a,**k:[])
    with pytest.raises(RuntimeError,match='liczbę brył'):
        normalize_pair(parts(),parts(),tmp_path)
