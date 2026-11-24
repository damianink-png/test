import pytest
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf, gp_Vec
from dsac29.geometry import describe


def parts(offset=0):
    shape=BRepPrimAPI_MakeBox(10,20,30).Shape()
    result=[]
    for i in range(3):
        tr=gp_Trsf();tr.SetTranslation(gp_Vec(offset+i*50,20,30))
        result.append(describe(shape.Moved(TopLoc_Location(tr)), f'czesc1_afm{i}', f'root/{i}'))
    return result


def _write(parts,path):
    from dsac29.step_io import ColoredDocument
    document=ColoredDocument()
    for part in parts:document.add(part.shape,part.name,(.2,.5,.8))
    document.write(path)


def test_process_reuses_identical_input_without_intermediate_export(tmp_path, monkeypatch):
    from dsac29 import cli
    source=tmp_path/'source.step'; _write(parts(),source)
    original_compare=cli.compare
    seen=[]
    def compare(a,b,*args,**kwargs):
        seen.append((a,b,kwargs.get('stage1_check')))
        assert a is b
        return original_compare(a,b,*args,**kwargs)
    monkeypatch.setattr(cli,'compare',compare)
    folder,records,error=cli.process(str(source),str(source),str(tmp_path/'result'),
        auto_align=True,step=False,full_bom=False,progress=None)
    assert error is None
    assert len(seen)==1 and seen[0][2] is None
    assert all(record.status=='SAME' for record in records)
    assert not (folder/'UJEDNOLICENIE_STEP.json').exists()
    assert not list(folder.glob('STEP_DO_POROWNANIA_*'))


@pytest.mark.parametrize('automatic,budget_exhausted',[(False,False),(True,False),(True,True)])
def test_alignment_in_memory_without_second_search_or_export(tmp_path, monkeypatch,automatic,budget_exhausted):
    import json
    from dsac29 import cli
    a_path,b_path=tmp_path/'old.step',tmp_path/'new.step'
    _write(parts(),a_path);_write(parts(130),b_path)
    original_compare=cli.compare
    calls=[]
    proposal={'status':'registered','votes':3,'previous_world_matches':0,
              'translation_B_to_A_mm':[-130,0,0], 'rotation_B_to_A':np.eye(3).tolist(),
              'full_pair_map':[],'certified_pairs':[]}
    if budget_exhausted:
        proposal.update(search_budget_exhausted=True,requires_confirmation=True,
                        verification_scope='sample_then_final_compare',verified_sample_count=3)
    monkeypatch.setattr(cli,'_continue_strong_incomplete_frame',lambda a,b,t,s,p,*args:p)
    def compare(a,b,*args,**kwargs):
        calls.append(kwargs)
        if len(calls)==1:
            assert kwargs['stage1_check'] is not None
            raise cli.ShiftDetected(proposal)
        assert kwargs['stage1_check'] is None
        assert kwargs['geometry_context'] is calls[0]['geometry_context']
        assert kwargs['certified_pairs']==[]
        for x,y in zip(a,b): assert x.center==pytest.approx(y.center)
        return original_compare(a,b,*args,**kwargs)
    monkeypatch.setattr(cli,'compare',compare)
    def approval(proposal):
        assert not automatic, 'Automatic mode must not open an approval dialog'
        return 'align'
    folder,records,error=cli.process(str(a_path),str(b_path),str(tmp_path/'result'),
        auto_align=True,automatic_alignment=automatic,alignment_approval=approval,
        step=False,full_bom=False,progress=None)
    assert error is None and len(calls)==2
    assert not (folder/'UJEDNOLICENIE_STEP.json').exists()
    assert not list(folder.glob('STEP_DO_POROWNANIA_*'))
    assert all(r.status=='SAME' for r in records)
    timing=json.loads((folder/'CZASY_ANALIZY.json').read_text())
    assert timing['final_comparison_after_alignment_s']>0
    assert timing['alignment_preflight_and_optional_registration_s']>=0
    alignment=json.loads((folder/'PODSUMOWANIE.json').read_text())['alignment']
    assert alignment['approved_by_user'] is not automatic
    if budget_exhausted:
        assert alignment['verification_status']=='confirmed_by_final_comparison'




def test_automatic_unresolved_alignment_continues_in_original_coordinates(tmp_path, monkeypatch):
    import json
    from dsac29 import cli

    source_a,source_b=tmp_path/'old.step',tmp_path/'new.step'
    _write(parts(),source_a)
    _write(parts(130),source_b)
    proposal={'status':'unresolved','reason':'Brak dowodu B-Rep','search_failed':True}
    original_compare=cli.compare

    def compare(a,b,*args,**kwargs):
        if kwargs['stage1_check'] is not None:
            raise cli.ShiftDetected(proposal)
        assert kwargs['registered_frame'] is False
        assert b[0].center-a[0].center==pytest.approx([130,0,0])
        return original_compare(a,b,*args,**kwargs)

    def approval(_):
        pytest.fail('No approval callback is needed for automatic alignment.')

    monkeypatch.setattr(cli,'compare',compare)
    monkeypatch.setattr(cli,'_continue_strong_incomplete_frame',lambda *args:proposal)
    folder,_,error=cli.process(str(source_a),str(source_b),str(tmp_path/'result'),auto_align=True,
        automatic_alignment=True,alignment_approval=approval,step=False,full_bom=False,progress=None)
    assert error is None
    alignment=json.loads((folder/'PODSUMOWANIE.json').read_text())['alignment']
    assert alignment['status']=='search_unresolved_original'
    assert alignment['applied'] is False and 'Brak dowodu B-Rep' in alignment['warning']


def test_world_matching_counters_do_not_restart_inside_same_frame(tmp_path):
    import json
    from dsac29.compare import compare
    from dsac29.progress_events import ProgressEvents

    out=tmp_path/'progress.jsonl'
    compare(parts(),parts(130),revision_only=True,progress=ProgressEvents(out))
    events=[json.loads(line) for line in out.read_text().splitlines()]
    counters=[(event['completed'],event['total']) for event in events
              if event['tekst'].startswith('Etap zgodności:')]
    assert counters==[(6,6)]
