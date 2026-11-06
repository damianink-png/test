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
                'surface_evidence':getattr(self,'surface_diagnostics',{}),
                'unique_anchor_evidence':getattr(self,'unique_anchor_diagnostics',{})}


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
        proposal={'status':'unresolved','reason':
                  'Nie znaleziono dodatkowego przesunięcia potwierdzonego B-Rep.'}
    proposal['search_diagnostics']=state.summary()
    return proposal
