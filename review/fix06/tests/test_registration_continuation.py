import json
import inspect
import numpy as np
import pytest
from dsac29 import cli,deferred_alignment as reg,alignment,native_guard
from dsac29.compare import Record
from dsac29.registration_search import RegistrationSearch,continue_registration
from test_repeated_revision_policy import parts


def setup_state(a,b):
    state=RegistrationSearch();state.bind(a,b,.01)
    state.free_a=frozenset(range(len(a)));state.free_b=frozenset(range(len(b)))
    return state


def test_extended_search_recovers_named_shift_missed_by_signature_buckets(monkeypatch):
    a,b=parts(),parts(shift=1000)
    ids={id(p) for p in a}
    monkeypatch.setattr(reg,'signature',lambda p:'old-export' if id(p) in ids else 'new-export')
    records=[Record(i,None,'REMOVED','') for i in range(8)]+[Record(None,j,'ADDED','') for j in range(8)]
    state=setup_state(a,b)
    assert reg.propose(a,b,records,.01,search_state=state) is None
    monkeypatch.setattr(alignment,'align_assembly',lambda *a,**kw:pytest.fail('legacy registration invoked'))
    proposal=continue_registration(a,b,.01,state)
    assert proposal['status']=='registered'
    assert proposal['translation_B_to_A_mm']==pytest.approx([-1000,0,0])
    assert len(proposal['certified_pairs'])==8
    assert proposal['search_diagnostics']['expanded']


def test_completed_failed_pose_is_not_replayed(monkeypatch):
    a,b=parts(),parts(shift=1000)
    state=setup_state(a,b);state.completed.append(np.array([-1000.,0,0]))
    monkeypatch.setattr(reg,'frame_support',lambda *a,**kw:pytest.fail('completed pose replayed'))
    result=continue_registration(a,b,.01,state)
    assert result['status']=='unresolved'
    assert continue_registration(a,b,.01,state)['status']=='unresolved'


def test_unverified_competitive_pose_is_not_mistaken_for_negative_proof():
    a,b=parts(),parts(shift=1000);state=setup_state(a,b)
    proposal=continue_registration(a,b,.01,state)
    assert proposal['status']=='registered'
    # Independently verified winner plus a still-competitive unknown rival.
    state.expanded=False
    state.failures.append({'offset':[-900.,0,0],'reason':'timeout',
                           'count_upper_bound':8,
                           'volume_upper_bound':sum(p.volume for p in a)})
    state.completed.append(np.array([-900.,0,0]))
    proposal=continue_registration(a,b,.01,state)
    assert proposal['status']=='unresolved' and 'Niezweryfikowana' in proposal['reason']


def test_registration_state_rejects_other_inputs_or_tolerance():
    a,b=parts(),parts(shift=1000);state=setup_state(a,b)
    with pytest.raises(ValueError):state.bind(a,b,.02)
    with pytest.raises(ValueError):state.bind(a,b[::-1],.01)


def force_initial_failure(monkeypatch,a,b):
    def initial(left,right,matched,fa,fb,tolerance,*args,search_state=None,**kwargs):
        search_state.bind(left,right,tolerance)
        search_state.stage1_records=list(matched)
        search_state.free_a=fa;search_state.free_b=fb
        return {'status':'unresolved','reason':'Synthetic incomplete automatic registration'}
    monkeypatch.setattr(reg,'propose_from_stage1',initial)
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p.name=='a.step' else b)
    monkeypatch.setattr(alignment,'align_assembly',lambda *a,**kw:pytest.fail('legacy registration invoked'))
    assert 'align_assembly(' not in inspect.getsource(cli.process)


def test_cli_search_continues_current_engine_and_does_not_ask_again(tmp_path,monkeypatch):
    a,b=parts(),parts(shift=1000);force_initial_failure(monkeypatch,a,b)
    pa,pb=tmp_path/'a.step',tmp_path/'b.step';pa.write_text('old');pb.write_text('new')
    questions=[]
    def answer(q):questions.append(q);return 'search'
    out=tmp_path/'out'
    cli.process(pa,pb,out,step=False,diff_step=False,full_bom=False,
                revision_style=True,auto_align=True,alignment_approval=answer,progress=None)
    data=json.loads((out/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
    assert len(questions)==1 and questions[0]['status']=='unresolved'
    assert data['alignment']['applied']
    assert data['alignment']['search_diagnostics']['expanded']
    assert data['statuses']=={'SAME':8}


def test_failed_expanded_search_cannot_loop_or_silently_use_original(tmp_path,monkeypatch):
    from dsac29 import registration_search
    a,b=parts(),parts(shift=1000);force_initial_failure(monkeypatch,a,b)
    calls=[]
    def failed(*args,**kwargs):calls.append(1);return {'status':'unresolved','reason':'No native proof'}
    monkeypatch.setattr(registration_search,'continue_registration',failed)
    pa,pb=tmp_path/'a.step',tmp_path/'b.step';pa.write_text('old');pb.write_text('new')
    questions=[]
    def answer(q):
        questions.append(q)
        return 'search' if len(questions)==1 else 'cancel'
    out=tmp_path/'out'
    with pytest.raises(InterruptedError):
        cli.process(pa,pb,out,step=False,diff_step=False,full_bom=False,
                    revision_style=True,auto_align=True,alignment_approval=answer,progress=None)
    assert len(calls)==1 and len(questions)==2
    assert questions[1]['search_failed'] is True
    assert not (out/'PODSUMOWANIE.json').exists()


def test_medium_assembly_uses_bounded_sample_not_full_native_preflight(monkeypatch):
    a,b=parts(count=120),parts(count=120,shift=1000)
    records=[Record(i,None,'REMOVED','') for i in range(120)]+[Record(None,j,'ADDED','') for j in range(120)]
    requests=[]
    def native(left,right,tol,proofs=8,verify_all=False,proof_cache=None,**kw):
        assert not verify_all
        requests.append(proofs)
        for k in range(min(proofs,120)):
            i=k*119//max(1,proofs-1)
            proof_cache.results[i,i]=True
        return {'count':120,'checked':proofs,'proofs':proofs,'ratio':1.}
    monkeypatch.setattr(reg,'frame_support',native)
    result=reg.propose(a,b,records,.01)
    assert result['status']=='registered' and max(requests)<=48
    assert result['verification_scope']=='sample_then_final_compare'
    assert not result['full_pair_map']


def test_native_timeout_is_not_restarted_in_same_pose_sample_and_full_pass(monkeypatch):
    from dsac29.registration_gate import FrameProofCache,frame_support
    from dsac29.geometry_registry import GeometryRegistry
    a,b=parts(count=80),parts(count=80)
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *a:False)
    monkeypatch.setattr(GeometryRegistry,'definition',lambda self,p:id(p))
    calls=[]
    def proof(left,right,*args,**kw):
        calls.append(id(left))
        if left is a[0]:raise native_guard.NativeGeometryFailure('Synthetic timeout')
        return True
    monkeypatch.setattr(native_guard,'guarded_world_reexport',proof)
    cache=FrameProofCache()
    assert frame_support(a,b,.01,proofs=2,proof_cache=cache)['proofs']==1
    full=frame_support(a,b,.01,verify_all=True,proof_cache=cache)
    assert full['count']==79 and calls.count(id(a[0]))==1
    assert (0,0) not in cache.results and cache.skipped_timeouts>=1
