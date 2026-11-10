from dataclasses import replace
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.compare import Record
from dsac29 import unique_anchors,cad_pose_search,cad_registration
from dsac29.registration_search import RegistrationSearch
from dsac29.native_session import world_session


def scene():
    a=[]
    # Largest unique body deliberately last; repeated fasteners first.
    for i in range(20):
        a.append(_relocate(describe(BRepPrimAPI_MakeBox(5,6,7).Shape(),'unrelated_name','old'),np.eye(3),np.array([i*41.,i*i*3.,i%3*40.])))
    for i,dim in enumerate([(23,17,11),(37,26,16),(123,85,13)]):
        a.append(_relocate(describe(BRepPrimAPI_MakeBox(*dim).Shape(),'old_name','old'),np.eye(3),np.array([i*150.,-170.-i*40.,i*80.])))
    shift=np.array([1950.,-375.,82.])
    b=[replace(_relocate(p,np.eye(3),shift),name='new_completely_different_name') for p in a][::-1]
    records=[Record(i,None,'REMOVED','') for i in range(len(a))]+[Record(None,j,'ADDED','') for j in range(len(b))]
    return a,b,records,shift



def test_spatially_diverse_anchor_order_never_loses_a_candidate():
    from dsac29.unique_anchors import prioritize_unique_anchors
    parts=[]
    for i,x in enumerate((0.,1.,2.,1800.,-1600.)):
        s=describe(BRepPrimAPI_MakeBox(25.-i,10.,10.).Shape(),'ANCHOR','x')
        parts.append(_relocate(s,np.eye(3),np.array([x,0.,0.])))
    pairs=[(i,i) for i in range(len(parts))]
    result=prioritize_unique_anchors(parts,pairs)
    assert result[0]==(0,0)
    assert set(result)==set(pairs)
    assert result[1] in ((3,3),(4,4))


def test_largest_bilateral_unique_body_first_despite_order_names_and_repeats():
    a,b,_,_=scene();pairs=list(unique_anchors.unique_pairs(a,b))
    assert pairs[0]==(22,0)
    assert [a[i].volume for i,j in pairs]==sorted([a[i].volume for i,j in pairs],reverse=True)
    assert len(pairs)==3


def test_central_principal_inertia_is_translation_invariant():
    a,b,_,_=scene()
    assert a[-1].eigenvalues==pytest.approx(b[0].eigenvalues,rel=1e-9)
    assert unique_anchors.descriptor_match(a[-1],b[0])
    assert not unique_anchors.descriptor_match(a[-1],replace(b[0],eigenvalues=b[0].eigenvalues*1.2))


def test_largest_native_anchor_recovers_shift_when_general_hypotheses_are_empty(monkeypatch):
    a,b,rows,shift=scene();state=RegistrationSearch();messages=[]
    monkeypatch.setattr(cad_pose_search,'hypotheses',lambda *a,**kw:[])
    result=cad_registration.propose(a,b,rows,.01,search_state=state,progress=messages.append)
    assert result['status']=='registered',result
    assert result['search_algorithm']=='unique_largest_inertia_anchor'
    assert result['translation_B_to_A_mm']==pytest.approx(-shift,abs=1e-6)
    assert result['votes']==len(a)
    assert len(result['certified_pairs'])==len(a)
    evidence=result['search_diagnostics']['unique_anchor_evidence']
    assert evidence['anchors'][0]['a']==22
    assert any('geometria potwierdzona' in s for s in messages)


def test_fake_equal_volume_and_moments_do_not_certify_geometry():
    from time import monotonic
    a,b,_,_=scene();a=[a[-1]];other=describe(BRepPrimAPI_MakeBox(10,10,10).Shape(),'fake','x')
    b=[replace(b[0],shape=other.shape)]
    state=RegistrationSearch();state.bind(a,b,.01)
    with world_session(True):
        offsets=unique_anchors.proven_translations(a,b,.01,state,monotonic()+20)
    assert offsets==[]
    assert state.unique_anchor_diagnostics['proven']==0


def test_individual_anchor_move_does_not_establish_global_frame(monkeypatch):
    a,b,rows,_=scene();b=[_relocate(p,np.eye(3),np.array([-1950.,375.,-82.])) for p in b]
    b[0]=_relocate(b[0],np.eye(3),np.array([500.,0.,0.]))
    from dsac29 import surface_registration
    monkeypatch.setattr(surface_registration,'propose',lambda *a,**kw:None)
    monkeypatch.setattr(cad_pose_search,'hypotheses',lambda *a,**kw:[])
    result=cad_registration.propose(a,b,rows,.01)
    assert result is None or result['status']!='registered'


def test_unknown_native_result_is_retryable_and_not_a_geometry_proof(monkeypatch):
    from time import monotonic
    from dsac29 import native_guard
    a,b,_,_=scene();state=RegistrationSearch();state.bind(a,b,.01)
    monkeypatch.setattr(native_guard,'guarded_registered_world',lambda *a,**kw:(_ for _ in ()).throw(native_guard.NativeGeometryFailure('synthetic timeout')))
    with world_session(True):
        result=unique_anchors.proven_translations(a,b,.01,state,monotonic()+20)
    assert result==[] and state.unique_anchor_cache=={}
    assert state.unique_anchor_diagnostics['unknown']>0


def test_periodic_in_place_shortcut_uses_unique_vector_even_without_general_search(monkeypatch):
    from dsac29.deferred_alignment import _periodic_global_offset_possible
    # A translated finite row already has 19 screw instances matching in place,
    # while its unique large anchor establishes the missing one-pitch shift.
    a=[]
    for i in range(20):
        a.append(_relocate(describe(BRepPrimAPI_MakeBox(5,6,7).Shape(),'SCREW','x'),np.eye(3),np.array([i*41.,0.,0.])))
    a.append(describe(BRepPrimAPI_MakeBox(123,85,13).Shape(),'UNIQUE','x'))
    b=[_relocate(p,np.eye(3),np.array([41.,0.,0.])) for p in a]
    monkeypatch.setattr(cad_pose_search,'hypotheses',lambda *a,**kw:[])
    assert _periodic_global_offset_possible(a,b,.01,len(a),baseline=19)


def test_changed_largest_candidate_does_not_hide_next_unchanged_unique_anchor(monkeypatch):
    a,b,rows,shift=scene()
    # Largest candidate has a small real dimensional revision. Its numerical
    # descriptors admit lookup, but native geometry must reject it.
    changed=describe(BRepPrimAPI_MakeBox(124,85,13).Shape(),'new_revision','new')
    b[0]=_relocate(changed,np.eye(3),np.array([300.,-250.,160.])+shift)
    assert unique_anchors.descriptor_match(a[-1],b[0])
    monkeypatch.setattr(cad_pose_search,'hypotheses',lambda *a,**kw:[])
    state=RegistrationSearch()
    result=cad_registration.propose(a,b,rows,.01,search_state=state)
    assert result['status']=='registered',result
    assert result['votes']==22
    assert result['translation_B_to_A_mm']==pytest.approx(-shift,abs=1e-6)
    evidence=result['search_diagnostics']['unique_anchor_evidence']
    assert evidence['anchors'][0]['a']==21
    assert any(key[0]==22 and value is False for key,value in state.unique_anchor_cache.items())
