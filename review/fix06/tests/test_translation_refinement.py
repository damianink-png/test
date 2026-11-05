"""Native regression: integrated centroids drift, original geometry does not."""
from dataclasses import replace
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.compare import Record
from dsac29 import deferred_alignment as reg
from dsac29.translation_refinement import refine_translations


def assembly(count=12, changed=False):
    a=[];b=[]
    for i in range(count):
        shape=BRepPrimAPI_MakeBox(7+i*.2,8+i*.1,9+i*.3).Shape()
        left=_relocate(describe(shape,f'part_{i}_REV_A',str(i)),np.eye(3),
                       np.array([i*30.,(i%4)*40.,(i%3)*50.]))
        right=_relocate(left,np.eye(3),np.array([1000.,200.,-50.]))
        # Deliberately independent shape, as after a new STEP export.
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
        right=replace(right,shape=BRepBuilderAPI_Copy(right.shape).Shape(),
                      center=right.center+np.array([.18,-.08,.04]))
        if changed:
            # Equal metadata is deliberately untrustworthy. Native geometry
            # has a different depth and must never pass as unchanged.
            other=describe(BRepPrimAPI_MakeBox(7+i*.2,8+i*.1,10+i*.3).Shape(),'changed','b')
            other=_relocate(other,np.eye(3),np.array([1000+i*30.,200+(i%4)*40.,-50+(i%3)*50.]))
            right=replace(right,shape=other.shape)
        a.append(left);b.append(right)
    records=[Record(i,None,'REMOVED','') for i in range(count)]
    records += [Record(None,i,'ADDED','') for i in range(count)]
    return a,b,records


def test_refinement_recovers_true_translation_despite_integrated_centroid_drift():
    a,b,records=assembly()
    offset=np.mean([p.center for p in a],axis=0)-np.mean([p.center for p in b],axis=0)
    assert np.linalg.norm(offset-[-1000,-200,50])>.01
    refined=refine_translations(a,b,[offset],.01)
    assert any(np.linalg.norm(v-[-1000,-200,50])<1e-7 for v in refined)
    proposal=reg.propose(a,b,records,.01)
    assert proposal['status']=='registered'
    assert proposal['translation_B_to_A_mm']==pytest.approx([-1000,-200,50])
    assert len(proposal['certified_pairs'])==len(a)


def test_center_drift_reproduction_fails_without_refinement(monkeypatch):
    from dsac29 import cad_pose_search
    a,b,records=assembly()
    monkeypatch.setattr(cad_pose_search,'landmarks',lambda parts,*args:np.asarray([p.center for p in parts]))
    proposal=reg.propose(a,b,records,.01)
    assert proposal is None or proposal['status']!='registered'


def test_bad_geometry_cannot_be_accepted_by_bounds_or_centroid_hints():
    a,b,records=assembly(changed=True)
    proposal=reg.propose(a,b,records,.01)
    assert proposal is None or proposal['status']!='registered'


def test_refinement_honors_cancellation():
    from dsac29.compare import Cancelled
    a,b,_=assembly()
    with pytest.raises(Cancelled):
        refine_translations(a,b,[np.array([-1000.,-200.,50.])],.01,lambda:True)


def test_380_part_revision_refines_241_candidates_without_full_preflight(monkeypatch):
    a,b,_=assembly(count=241)
    for i in range(139):
        a.append(describe(BRepPrimAPI_MakeBox(300+i,20,30).Shape(),'old','old'))
        b.append(_relocate(describe(BRepPrimAPI_MakeBox(500+i,40,60).Shape(),'new','new'),
                           np.eye(3),np.array([9000.,9000.,9000.])))
    records=[Record(i,None,'REMOVED','') for i in range(380)]
    records += [Record(None,i,'ADDED','') for i in range(380)]
    actual=reg.frame_support
    def bounded(*args,**kwargs):
        assert not kwargs.get('verify_all'), 'Do not preverify all 241 candidates'
        assert kwargs.get('proofs',8)<=48
        return actual(*args,**kwargs)
    monkeypatch.setattr(reg,'frame_support',bounded)
    proposal=reg.propose(a,b,records,.01)
    assert proposal['status']=='registered'
    assert proposal['translation_B_to_A_mm']==pytest.approx([-1000,-200,50])
    assert proposal['votes']==241
    assert proposal['verified_sample_count']==48
    assert proposal['verification_scope']=='sample_then_final_compare'
    assert 48<=len(proposal['certified_pairs'])<241
    assert proposal['full_pair_map']==[]


def test_final_compare_verifies_every_unsampled_part_after_refinement():
    from dsac29.compare import compare
    a,b,records=assembly(count=80)
    proposal=reg.propose(a,b,records,.01)
    assert proposal['status']=='registered'
    aligned=[_relocate(p,np.eye(3),np.asarray(proposal['translation_B_to_A_mm'])) for p in b]
    final=compare(a,aligned,.01,exact_serialization=True,revision_only=True,
                  certified_pairs=proposal['certified_pairs'])
    assert len(final)==80
    assert all(r.status=='SAME' for r in final)
