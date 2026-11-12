"""One current registration search, continued after an explicit user request.

Completed hypotheses are not replayed by a separate legacy algorithm. Only
verified B-Rep results survive; no descriptor vote becomes a geometry proof.
"""
import numpy as np


class RegistrationSearch:
    def __init__(self):
        from .registration_gate import FrameProofCache
        self.binding=FrameProofCache()
        self.completed=[]
        self.features=None
        self.poses_completed=[]
        self.pose_winners=[]
        self.expanded=False
        self.failures=[]
        self.resolved_failures=[]
        self.sample_history=[]
        self.diagnostic_path=None
        self.stage1_records=[]
        self.free_a=frozenset()
        self.free_b=frozenset()

    def bind(self,a,b,tolerance):
        self.binding.bind(a,b,tolerance)

    def seen(self,offset,tolerance):
        return any(np.linalg.norm(offset-old)<=tolerance for old in self.completed)

    def summary(self):
        return {'algorithm':'cad_global_consensus_trimmed_refinement',
                'expanded':self.expanded,'completed_hypotheses':len(self.poses_completed) or len(self.completed),
                'failed_native_attempts':len(self.failures),
                'pending_hypotheses':[{
                    'translation_B_to_A_mm':f['offset'],
                    'rotation_B_to_A':f.get('rotation',np.eye(3).tolist()),
                    'candidate_count':f['count_upper_bound'],
                    'verified_pair_count':len(f.get('proven_pairs',())),
                    'completed_negative_pair_count':len(f.get('completed_negative_pairs',())),
                    'attempts':f.get('attempts',1),'last_pass':f.get('last_pass','unknown'),
                    'last_error':f['reason'],'pair_timeout_s':f.get('pair_timeout_s'),
                    'retryable':bool(f.get('pairs')), 'native_errors':f.get('native_errors',[])}
                    for f in self.failures[:16]],
                'resolved_incomplete_hypotheses':self.resolved_failures[-16:],
                'world_samples':self.sample_history[-32:],
                'surface_evidence':getattr(self,'surface_diagnostics',{}),
                'unique_anchor_evidence':getattr(self,'unique_anchor_diagnostics',{})}


    def checkpoint(self,proposal=None):
        if self.diagnostic_path is None:return
        import json
        from pathlib import Path
        from . import trace_r22 as trace
        path=Path(self.diagnostic_path)
        data=self.summary()
        if proposal is not None:
            data['result_status']=proposal.get('status')
            data['result_reason']=proposal.get('reason','')
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            temporary=path.with_suffix('.tmp')
            temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            temporary.replace(path)
        except OSError as exc:
            trace.mark('registration_diagnostics','WRITE_FAILED',error=str(exc))



def continue_registration(a,b,tolerance,state,progress=None,cancelled=None):
    """Explore additional current hypotheses once; never call align_assembly."""
    from .deferred_alignment import propose
    from .compare import Record
    state.bind(a,b,tolerance)
    if state.expanded:
        return {'status':'unresolved','reason':'Rozszerzone wyszukiwanie zostało już wykonane.'}
    state.expanded=True
    if progress:
        progress(f'Wyrównanie: rozszerzone wyszukiwanie bieżącego silnika; '
                 f'pomijam {state.summary()["completed_hypotheses"]} wcześniej sprawdzanych hipotez (translacje i obroty). '
                 'Sprawdzam dodatkowe hipotezy położenia i obrotu CAD.')
    records=list(state.stage1_records)
    records.extend(Record(i,None,'REMOVED','Etap 1') for i in state.free_a)
    records.extend(Record(None,j,'ADDED','Etap 1') for j in state.free_b)
    from .native_guard import NativeGeometryFailure
    try:
        proposal=propose(a,b,records,tolerance,progress,cancelled,
                         search_state=state,extended=True)
    except NativeGeometryFailure as exc:
        proposal={'status':'unresolved','reason':'Rozszerzone wyszukiwanie: '+str(exc)}
    if proposal is None:
        reason='Brak nowych hipotez położenia; wcześniej sprawdzone wyniki pozostają niepotwierdzone.'
        if state.sample_history:
            best=max(state.sample_history,key=lambda s:(s['world_proofs'],s['checked']))
            reason+=(f' Najlepsza próba: {best["world_proofs"]}/{best["checked"]} zgodnych położeń B-Rep, '
                     f'B→A {best["translation_B_to_A_mm"]} mm. Szczegóły: WYROWNANIE_DIAGNOSTYKA.json.')
        proposal={'status':'unresolved','reason':reason}
    proposal['search_diagnostics']=state.summary()
    state.checkpoint(proposal)
    return proposal
