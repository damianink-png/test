import json
import numpy as np
import pytest
from dsac29 import cad_pose_search,cad_registration,deferred_alignment,native_guard,surface_registration,cli
from dsac29.registration_search import RegistrationSearch,continue_registration
from dsac29.compare import Record
from test_repeated_revision_policy import parts


def scene(monkeypatch):
    a,b=parts(),parts(shift=1000)
    rows=[Record(i,None,'REMOVED','') for i in range(8)]+[Record(None,j,'ADDED','') for j in range(8)]
    state=RegistrationSearch();state.bind(a,b,.01)
    state.free_a=frozenset(range(8));state.free_b=frozenset(range(8))
    monkeypatch.setattr(surface_registration,'propose',lambda *a,**kw:None)
    real=cad_pose_search.hypotheses
    def single(*args,**kwargs):
        if kwargs.get('rotations'):return []
        return [p for p in real(*args,**kwargs) if np.allclose(p.translation,[-1000.,0.,0.])][:1]
    monkeypatch.setattr(cad_pose_search,'hypotheses',single)
    return a,b,rows,state


def test_transient_native_failure_does_not_complete_pose_and_search_retries_real_geometry(monkeypatch):
    a,b,rows,state=scene(monkeypatch);native=deferred_alignment.frame_support;calls=[]
    def transient(*args,**kwargs):
        calls.append(kwargs['proof_cache'].pair_timeout)
        if len(calls)==1:raise native_guard.NativeGeometryFailure('synthetic first timeout at surface_and_trim_proof')
        return native(*args,**kwargs)
    monkeypatch.setattr(deferred_alignment,'frame_support',transient)
    initial=deferred_alignment.propose(a,b,rows,.01,search_state=state)
    assert initial['status']=='unresolved'
    assert not state.poses_completed and not state.completed
    assert len(state.failures)==1
    result=continue_registration(a,b,.01,state)
    assert result['status']=='registered',result
    assert result['translation_B_to_A_mm']==pytest.approx([-1000,0,0])
    assert len(result['certified_pairs'])==8
    assert calls[0]==12 and 24 in calls[1:]
    assert not state.failures and len(state.resolved_failures)==1


def test_incomplete_sample_without_exception_is_retried(monkeypatch):
    a,b,rows,state=scene(monkeypatch);native=deferred_alignment.frame_support;calls=[]
    def incomplete(*args,**kwargs):
        calls.append(1);cache=kwargs['proof_cache']
        if len(calls)==1:
            cache.failed_pairs.add((0,0));cache.native_errors[0,0]='fixture timeout: solid_validity'
            return dict(count=8,checked=8,proofs=0)
        return native(*args,**kwargs)
    monkeypatch.setattr(deferred_alignment,'frame_support',incomplete)
    assert deferred_alignment.propose(a,b,rows,.01,search_state=state)['status']=='unresolved'
    assert not state.completed and 'solid_validity' in state.failures[0]['reason']
    assert continue_registration(a,b,.01,state)['status']=='registered'


def test_completed_negative_is_not_replayed(monkeypatch):
    a,b,rows,state=scene(monkeypatch);calls=[]
    def negative(*args,**kwargs):calls.append(1);return dict(count=8,checked=8,proofs=0)
    monkeypatch.setattr(deferred_alignment,'frame_support',negative)
    assert deferred_alignment.propose(a,b,rows,.01,search_state=state)['status']=='unresolved'
    assert state.completed and not state.failures
    result=continue_registration(a,b,.01,state)
    assert result['status']=='unresolved' and len(calls)==1


def test_repeated_unknown_stays_unknown_and_diagnostic_retains_actual_error(tmp_path,monkeypatch):
    a,b,rows,state=scene(monkeypatch);state.diagnostic_path=tmp_path/'WYROWNANIE_DIAGNOSTYKA.json';calls=[]
    def unknown(*args,**kwargs):calls.append(1);raise native_guard.NativeGeometryFailure('fixture timeout: surface_and_trim_proof')
    monkeypatch.setattr(deferred_alignment,'frame_support',unknown)
    deferred_alignment.propose(a,b,rows,.01,search_state=state)
    result=continue_registration(a,b,.01,state)
    assert result['status']=='unresolved' and len(calls)==2
    assert 'surface_and_trim_proof' in result['reason']
    assert not state.completed and not state.pose_winners
    data=json.loads(state.diagnostic_path.read_text())
    pending=data['pending_hypotheses'][0]
    assert pending['attempts']==2 and pending['pair_timeout_s']==24
    assert pending['translation_B_to_A_mm']==[-1000.,0.,0.]
    assert data['result_status']=='unresolved'


def test_positive_proofs_resume_only_for_exact_same_pose(monkeypatch):
    a,b,rows,state=scene(monkeypatch);native=deferred_alignment.frame_support;calls=[]
    def partial(*args,**kwargs):
        cache=kwargs['proof_cache'];calls.append(dict(cache.results))
        if len(calls)==1:
            # This fixture first completes a real positive native sample.
            native(*args,**(kwargs|dict(proofs=2)))
            raise native_guard.NativeGeometryFailure('fixture crash after two real positive proofs')
        return native(*args,**kwargs)
    monkeypatch.setattr(deferred_alignment,'frame_support',partial)
    deferred_alignment.propose(a,b,rows,.01,search_state=state)
    assert len(state.failures[0]['proven_pairs'])==2
    assert continue_registration(a,b,.01,state)['status']=='registered'
    assert len(calls[1])==2 and all(v is True for v in calls[1].values())


def test_failed_search_confirmation_preserves_diagnostic_details():
    captured=[]
    assert cli.confirm_original_after_failed_search(lambda q:(captured.append(q) or 'original'),'fixture',
        search_diagnostics={'pending_hypotheses':[{'attempts':2}]})=='original'
    assert captured[0]['search_diagnostics']['pending_hypotheses'][0]['attempts']==2


@pytest.mark.parametrize('recovers',[True,False])
def test_unknown_rival_is_retried_and_only_completed_evidence_removes_veto(monkeypatch,recovers):
    a,b,rows,state=scene(monkeypatch);native=deferred_alignment.frame_support
    points=(cad_pose_search.landmarks(a),cad_pose_search.landmarks(b))
    pairs=[(i,i) for i in range(8)];volume=sum(p.volume for p in a)
    rival=cad_pose_search.Pose(np.eye(3),np.array([-999.96,0.,0.]),pairs,volume,'rival_fixture')
    correct=cad_pose_search.Pose(np.eye(3),np.array([-1000.,0.,0.]),pairs,volume,'correct_fixture')
    monkeypatch.setattr(cad_pose_search,'hypotheses',lambda *a,**kw:[] if kw.get('rotations') else [rival,correct])
    def fail_rival(left,right,*args,**kwargs):
        offset=right[0].center[0]-b[0].center[0]
        if abs(offset+999.96)<1e-6 and (not state.expanded or not recovers):
            raise native_guard.NativeGeometryFailure('fixture rival timeout')
        return native(left,right,*args,**kwargs)
    monkeypatch.setattr(deferred_alignment,'frame_support',fail_rival)
    first=deferred_alignment.propose(a,b,rows,.01,search_state=state)
    assert first['status']=='unresolved' and 'konkurencyjna' in first['reason']
    assert len(state.pose_winners)==1 and len(state.failures)==1
    result=continue_registration(a,b,.01,state)
    if recovers:
        assert result['status']=='registered',result
        assert result['translation_B_to_A_mm']==pytest.approx([-1000.,0.,0.])
        assert not state.failures and len(state.resolved_failures)==1
    else:
        assert result['status']=='unresolved' and 'rival timeout' in result['reason']
        assert state.failures[0]['attempts']==2


def test_saved_positive_proofs_are_not_transferred_to_changed_pose(monkeypatch):
    a,b,rows,state=scene(monkeypatch);native=deferred_alignment.frame_support;calls=[]
    def partial(*args,**kwargs):
        cache=kwargs['proof_cache'];calls.append(dict(cache.results))
        if len(calls)==1:
            native(*args,**(kwargs|dict(proofs=2)))
            raise native_guard.NativeGeometryFailure('fixture interrupted')
        return native(*args,**kwargs)
    monkeypatch.setattr(deferred_alignment,'frame_support',partial)
    deferred_alignment.propose(a,b,rows,.01,search_state=state)
    state.failures[0]['offset'][0]+=.04
    result=continue_registration(a,b,.01,state)
    assert calls[1]=={}
    assert result['status']=='registered'
    assert result['translation_B_to_A_mm']==pytest.approx([-1000.,0.,0.])


def test_cancelled_cli_keeps_diagnostics_without_publishing_result(tmp_path,monkeypatch):
    a,b,rows,state=scene(monkeypatch)
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p.name=='a.step' else b)
    monkeypatch.setattr(deferred_alignment,'frame_support',lambda *a,**kw:(_ for _ in ()).throw(native_guard.NativeGeometryFailure('fixture worker died')))
    pa=tmp_path/'a.step';pb=tmp_path/'b.step';pa.write_text('old');pb.write_text('new');out=tmp_path/'out'
    with pytest.raises(InterruptedError):
        cli.process(pa,pb,out,step=False,diff_step=False,full_bom=False,revision_style=True,
                    auto_align=True,alignment_approval=lambda p:'cancel',progress=None)
    data=json.loads((out/'WYROWNANIE_DIAGNOSTYKA.json').read_text())
    assert 'worker died' in data['pending_hypotheses'][0]['last_error']
    assert not (out/'PODSUMOWANIE.json').exists()


def test_pending_exact_pose_is_retried_even_after_nearby_pose_completed(monkeypatch):
    a,b,rows,state=scene(monkeypatch);native=deferred_alignment.frame_support;calls=[]
    pairs=[(i,i) for i in range(8)];volume=sum(p.volume for p in a)
    near=cad_pose_search.Pose(np.eye(3),np.array([-999.996,0.,0.]),pairs,volume,'near_fixture')
    correct=cad_pose_search.Pose(np.eye(3),np.array([-1000.,0.,0.]),pairs,volume,'correct_fixture')
    monkeypatch.setattr(cad_pose_search,'hypotheses',lambda *a,**kw:[] if kw.get('rotations') else [near,correct])
    def transient(left,right,*args,**kwargs):
        offset=right[0].center[0]-b[0].center[0]
        if abs(offset+999.996)<1e-6:
            calls.append(1)
            if len(calls)==1:raise native_guard.NativeGeometryFailure('fixture near pose interrupted')
        return native(left,right,*args,**kwargs)
    monkeypatch.setattr(deferred_alignment,'frame_support',transient)
    first=deferred_alignment.propose(a,b,rows,.01,search_state=state)
    assert first['status']=='registered' and state.failures
    assert continue_registration(a,b,.01,state)['status']=='registered'
    assert len(calls)>=2 and not state.failures


def test_medium_shift_24_24_extends_budget_for_full_proof_and_competing_pose(monkeypatch):
    """40 real TopoDS bodies: 24 completed positives may consume 28/30 sec.

    Native evidence still has to finish 38/40 real assignments AND reject a
    competitive pose. Old 80-body threshold made this a false UNRESOLVED.
    The synthetic clock models a slow STEP re-export; it never fakes a
    B-Rep verdict in production.
    """
    from dsac29 import unique_anchors
    from dsac29.cad_pose_search import Pose
    a,b=parts(count=40),parts(count=40,shift=1000)
    rows=([Record(i,None,'REMOVED','') for i in range(40)] +
          [Record(None,j,'ADDED','') for j in range(40)])
    state=RegistrationSearch()
    state.bind(a,b,.01)
    state.features=(np.array([p.center for p in a]),
                    np.array([p.center for p in b]))
    time_now=[100.]
    monkeypatch.setattr(cad_registration,'monotonic',lambda:time_now[0])
    monkeypatch.setattr(unique_anchors,'proven_translations',
                        lambda *_args,**_kwargs:[])
    original=Pose(np.eye(3),np.array([-1000.,0.,0.]),
                  [(i,i) for i in range(38)],
                  sum(p.volume for p in a[:38]),'verified_frame')
    rival=Pose(np.eye(3),np.array([-500.,0.,0.]),
               [(i,i) for i in range(38)],
               sum(p.volume for p in a[:38]),'unverified_rival')
    monkeypatch.setattr(cad_pose_search,'hypotheses',
                        lambda *_args,**_kwargs:[original,rival])
    calls=[]
    def slow_native(_left,_right,_tolerance,proofs=8,verify_all=False,
                    proof_cache=None,**_kwargs):
        correct=np.linalg.norm(
            np.array(_right[0].center)-np.array(_left[0].center))<.01
        calls.append((correct,verify_all,time_now[0]))
        if not correct:
            return {'count':38,'checked':24,'proofs':0}
        if verify_all:
            time_now[0]+=5.
            for i in range(38):
                proof_cache.results[i,i]=True
            return {'count':38,'checked':38,'proofs':38,
                    'pairs':[(i,i) for i in range(38)]}
        time_now[0]+=28.
        for i in range(24):
            proof_cache.results[i,i]=True
        return {'count':38,'checked':24,'proofs':24}
    monkeypatch.setattr(cad_registration,'frame_support',slow_native)
    result=cad_registration.propose(a,b,rows,.01,search_state=state)
    assert result['status']=='registered',result
    assert result['votes']==38
    assert result['translation_B_to_A_mm']==pytest.approx([-1000.,0.,0.])
    assert any(not right for right,full,_ in calls),calls
    assert len(result['certified_pairs'])==38
    assert result['verification_scope']=='full_brep'
    assert state.sample_history[0]['world_proofs']==24


def test_small_assembly_does_not_relax_brep_acceptance_threshold(monkeypatch):
    """The time-budget fix must not convert descriptor votes into SAME."""
    import inspect
    source=inspect.getsource(cad_registration.propose)
    assert 'positive>=ceil(.80*checked)' in source
    assert 'cache.deadline=body_deadline' in source
    assert "if not complete:" in source
