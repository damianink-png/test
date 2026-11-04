"""Regression: two matching anchor parts must not authorise a shifted full assembly."""
import numpy as np
import pytest
from types import SimpleNamespace


def test_two_anchor_fallback_does_not_call_full_brep_when_other_parts_disagree(monkeypatch):
    from dsac29 import alignment,registration_gate,compare,step_reexport_tolerance
    a=[SimpleNamespace(center=np.array([float(i)*10,0.,0.])) for i in range(40)]
    b=[SimpleNamespace(center=np.array([float(i)*10+130.,280.,410.])) for i in range(40)]
    calls=[]
    def support(*args,**kwargs):
        calls.append(kwargs)
        if kwargs.get('verify_all'):raise AssertionError('full B-Rep verification should not start')
        return {'ratio':0.,'count':0,'checked':0,'proofs':0}
    monkeypatch.setattr(registration_gate,'frame_support',support)
    def impossible_sparse(*args,**kwargs):raise alignment.AlignmentUnavailable('no robust consensus')
    monkeypatch.setattr(alignment,'_align_sparse_translation',impossible_sparse)
    shifted=[SimpleNamespace(center=np.array([2000.+float(i)*10,0.,0.])) for i in range(40)]
    monkeypatch.setattr(alignment,'_align_anchors',lambda *a,**kw:(shifted,{'anchors':2,'votes':2}))
    monkeypatch.setattr(compare,'_spatial_index',lambda *args,**kwargs:{})
    monkeypatch.setattr(compare,'_nearby',lambda *args,**kwargs:[])
    with pytest.raises(alignment.AlignmentUnavailable,match='Dwie bazy'):
        alignment.align_assembly(a,b,0.01)
    assert not any(x.get('verify_all') for x in calls)


def test_failure_requires_an_explicit_original_choice():
    from dsac29.cli import confirm_original_after_failed_search
    questions=[]
    def choose(q):questions.append(q);return 'original'
    assert confirm_original_after_failed_search(choose,'2/2 only')=='original'
    assert questions==[{'status':'unresolved','search_failed':True,'reason':'2/2 only'}]
    with pytest.raises(InterruptedError,match='nie wybrano'):
        confirm_original_after_failed_search(lambda q:'search','2/2 only')
    with pytest.raises(InterruptedError,match='Nie potwierdzono'):
        confirm_original_after_failed_search(None,'2/2 only')
