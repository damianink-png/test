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
    monkeypatch.setattr(alignment,'_align_repeated_translation',impossible_sparse)
    monkeypatch.setattr(alignment,'_align_global_centroid_translation',impossible_sparse)
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


def test_legacy_progress_does_not_call_two_anchors_a_completed_alignment():
    import inspect
    from dsac29 import alignment
    code=inspect.getsource(alignment._align_anchors)
    assert 'Kandydat B do A:' in code
    assert "Wyrównano B do A:" not in code


def test_pure_shift_of_identical_assembly_has_brep_verified_centroid_hypothesis():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt
    from dsac29.geometry import describe
    from dsac29.alignment import _relocate, _align_global_centroid_translation
    a=[]
    for i in range(16):
        shape=BRepPrimAPI_MakeBox(gp_Pnt(float(i*30),0.,0.),
                                 10.+i%5,12.,7.).Shape()
        a.append(describe(shape,f'part{i}',f'old/{i}'))
    offset=np.array([1000.,1300.,500.])
    b=[_relocate(p,np.eye(3),offset) for p in a]
    shifted,proposal=_align_global_centroid_translation(a,b,.01)
    assert proposal['status']=='registered'
    assert proposal['translation_B_to_A_mm']==pytest.approx(-offset)
    assert proposal['whole_assembly_support']['proofs']>=8
    assert (proposal['whole_assembly_support']['proofs'] ==
            proposal['whole_assembly_support']['checked'])
    assert len(proposal['certified_pairs'])>=8
    assert proposal['verification_scope']=='sample_then_final_compare'
    assert proposal['full_pair_map']==[]


def test_failed_two_base_sample_does_not_block_independent_hypotheses(monkeypatch):
    from dsac29 import alignment,registration_gate,compare,step_reexport_tolerance
    a=[SimpleNamespace(center=np.array([float(i)*10,0,0])) for i in range(40)]
    b=[SimpleNamespace(center=np.array([float(i)*10+300,200,500])) for i in range(40)]
    monkeypatch.setattr(alignment,'_align_global_centroid_translation',
        lambda *args,**kwargs: (_ for _ in ()).throw(alignment.AlignmentUnavailable('centroid failed')))
    monkeypatch.setattr(alignment,'_align_sparse_translation',
        lambda *args,**kwargs: (_ for _ in ()).throw(alignment.AlignmentUnavailable('sparse failed')))
    monkeypatch.setattr(alignment,'_align_anchors',
        lambda *args,**kwargs:(a,{'status':'registered','anchors':2,'votes':2}))
    calls=[]
    def frame(*args,**kwargs):
        calls.append(kwargs)
        return ({'ratio':0,'count':0,'checked':0,'proofs':0} if len(calls)==1
                else {'ratio':1,'count':241,'checked':8,'proofs':0})
    monkeypatch.setattr(registration_gate,'frame_support',frame)
    monkeypatch.setattr(compare,'_spatial_index',lambda *args,**kwargs:{})
    monkeypatch.setattr(compare,'_nearby',lambda *args,**kwargs:[0])
    monkeypatch.setattr(step_reexport_tolerance,'world_candidate',lambda *args,**kwargs:True)
    monkeypatch.setattr(alignment,'_align_repeated_translation',
        lambda *args,**kwargs:(b,{'status':'registered','method':'fallback_proven',
                                'translation_B_to_A_mm':[-300,-200,-500]}))
    out,proposal=alignment.align_assembly(a,b,0.01)
    assert out is b
    assert proposal['method']=='fallback_proven'
    assert not any(x.get('verify_all') for x in calls)


def test_centroid_shift_never_accepts_unproven_sample(monkeypatch):
    from dsac29 import alignment,registration_gate
    from dsac29.alignment import _align_global_centroid_translation
    a=[SimpleNamespace(center=np.array([float(i),0.,0.])) for i in range(20)]
    b=[SimpleNamespace(center=np.array([float(i)+100.,0.,0.])) for i in range(20)]
    monkeypatch.setattr(alignment,'_relocate',lambda p,*args:p)
    monkeypatch.setattr(registration_gate,'frame_support',
        lambda *a,**k:{'ratio':1,'count':20,'checked':8,'proofs':0})
    with pytest.raises(alignment.AlignmentUnavailable,match='0/8'):
        _align_global_centroid_translation(a,b,.01)
