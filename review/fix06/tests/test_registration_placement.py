from dataclasses import replace
import numpy as np
import pytest
from dsac29 import cad_registration as registration,alignment,cad_pose_search
from dsac29.registration_search import RegistrationSearch,continue_registration
from test_cad_pose_search import case,rotation


def test_fast_candidate_placement_preserves_rigid_invariants_without_integration(monkeypatch):
    a,_,_,_,_=case(n=1,rotated=False);part=a[0];r=rotation();t=np.array([1200.,-500.,300.])
    exact=alignment._relocate(part,r,t)
    monkeypatch.setattr(alignment,'describe',lambda *a,**k:pytest.fail('Repeated CAD integration'))
    placed=registration.place_for_proof(part,r,t)
    assert placed.volume==part.volume and placed.area==part.area
    assert placed.center==pytest.approx(exact.center,abs=1e-7)
    assert placed.inertia==pytest.approx(exact.inertia,rel=1e-7,abs=1e-5)
    assert np.abs(placed.axes.T@exact.axes)==pytest.approx(np.eye(3),abs=1e-7)
    assert np.all(np.asarray(placed.bbox)>=np.asarray(exact.bbox)-1e-6)
    assert placed.name==part.name and placed.path==part.path


@pytest.mark.parametrize('r',[np.diag([2.,1.,1.]),np.diag([-1.,1.,1.]),np.full((3,3),np.nan)])
def test_proof_placement_rejects_non_rigid_input_before_native_shape_access(r):
    with pytest.raises(ValueError):registration.place_for_proof(object(),r,np.zeros(3))


def test_rotation_of_380_candidate_solids_does_not_recompute_mass_properties(monkeypatch):
    a,b,records,r,t=case(n=18,outliers=362)
    monkeypatch.setattr(alignment,'describe',lambda *a,**k:pytest.fail('Candidate recalculated CAD properties'))
    proposal=registration.propose(a,b,records,.01)
    assert proposal['status']=='registered' and proposal['votes']==18
    assert np.asarray(proposal['rotation_B_to_A'])@r==pytest.approx(np.eye(3),abs=1e-6)


def test_expired_preparation_never_runs_native_proof_or_rejects_pose_permanently(monkeypatch):
    from time import monotonic
    a,b,records,_,_=case(n=18,rotated=False)
    state=RegistrationSearch();clock=[monotonic()];original=registration.place_for_proof;advanced=[False]
    monkeypatch.setattr(registration,'monotonic',lambda:clock[0])
    def place(*args):
        result=original(*args)
        if not advanced[0]:clock[0]+=61;advanced[0]=True
        return result
    monkeypatch.setattr(registration,'place_for_proof',place)
    def forbidden(*args,**kwargs):pytest.fail('Native proof started after preparation exhausted deadline')
    result=registration.propose(a,b,records,.01,search_state=state,support=forbidden)
    assert result['status']=='unresolved'
    assert not state.poses_completed and not state.failures
    # A larger explicit budget is allowed to evaluate the untested pose.
    result=registration.propose(a,b,records,.01,search_state=state,extended=True)
    assert result['status']=='registered' and result['votes']==18


def test_continuation_count_includes_rotations_as_well_as_translations():
    a,b,_,r,t=case(n=8,rotated=False)
    state=RegistrationSearch();state.bind(a,b,.01)
    state.completed=[np.array([-1200.,730.,-441.])]
    state.poses_completed=[(np.eye(3),state.completed[0]),(rotation(),np.array([1.,2.,3.]))]
    state.free_a=frozenset(range(8));state.free_b=frozenset(range(8));messages=[]
    continue_registration(a,b,.01,state,progress=messages.append)
    assert any('pomijam 2 wcześniej' in message for message in messages)


def test_placed_hypothesis_retains_source_definition_and_strict_digest_only_when_same_tshape():
    from dsac29.compare import _location_matrix
    a,_,_,_,_=case(n=1,rotated=False)
    original=a[0]
    original.step_definition_key=('zw3d-source.step','0:1:1:5',1)
    original._dscompare_normalized_digest=b'x'*32
    original._dscompare_local_origin=(3.,4.,5.)
    t=np.array([-130.,-280.,-410.])
    moved=registration.place_for_proof(original,np.eye(3),t)
    assert moved.step_definition_key==original.step_definition_key
    if moved.shape.IsPartner(original.shape):
        assert moved._dscompare_normalized_digest==original._dscompare_normalized_digest
        assert np.allclose(np.asarray(_location_matrix(moved))[:,3]-
                           np.asarray(_location_matrix(original))[:,3],t)
    else:
        assert getattr(moved,'_dscompare_normalized_digest',None) is None
    # A direct TopLoc placement MUST keep the original native TShape and
    # allow safe transfer of a full local B-Rep certificate.
    from dataclasses import replace
    from OCP.TopLoc import TopLoc_Location
    partner=replace(original,shape=original.shape.Moved(TopLoc_Location()))
    assert partner.shape.IsPartner(original.shape)
    partner=registration._preserve_native_definition_evidence(original,partner)
    assert partner._dscompare_normalized_digest==original._dscompare_normalized_digest


def test_rotated_hypothesis_must_not_inherit_invalid_local_brep_digest():
    a,_,_,_,_=case(n=1,rotated=False)
    part=a[0]
    part.step_definition_key=('source.step','0:1:2',1)
    part._dscompare_normalized_digest=b'z'*32
    part._dscompare_local_origin=(9.,5.,3.)
    moved=registration.place_for_proof(part,rotation(),np.array([15.,-8.,4.]))
    assert moved.step_definition_key==part.step_definition_key
    if moved.shape.IsPartner(part.shape):
        assert moved._dscompare_normalized_digest==part._dscompare_normalized_digest
    else:
        assert getattr(moved,'_dscompare_normalized_digest',None) is None


def test_alignment_candidate_order_uses_existing_strict_digest_only_as_priority():
    from types import SimpleNamespace
    from dsac29.registration_gate import _prioritize_previously_proven_definition
    aa=[SimpleNamespace(_dscompare_normalized_digest=b'A'*32),
        SimpleNamespace(_dscompare_normalized_digest=b'B'*32)]
    target=SimpleNamespace(_dscompare_normalized_digest=b'B'*32)
    # The correct definition can be slightly farther owing to re-export
    # placement rounding. The *native* world B-Rep still has final authority.
    assert _prioritize_previously_proven_definition(
        [(.00001,0),(.00003,1),(.00002,1)],aa,target)==[1,0]
    # Without strict complete digests, preserve distance ordering.
    target=SimpleNamespace()
    assert _prioritize_previously_proven_definition(
        [(.00001,0),(.00003,1)],aa,target)==[0,1]



def test_final_registered_frame_keeps_xcaf_source_family_for_repeat_cache():
    from dsac29.cli import _use_confirmed_frame
    a,_,_,_,_=case(n=2,rotated=False)
    original=a[0]
    original.step_definition_key=('export-B-ap214.step','0:1:1:66',1)
    original._dscompare_normalized_digest=b'a'*32
    original._dscompare_local_origin=(3.,4.,5.)
    proposal=dict(status='registered',
                  rotation_B_to_A=np.eye(3).tolist(),
                  translation_B_to_A_mm=[-130.,-280.,-410.])
    shifted=_use_confirmed_frame([original],proposal,alignment._relocate)[0]
    assert shifted.step_definition_key==original.step_definition_key
    assert np.allclose(shifted.center-original.center,
                       np.array([-130.,-280.,-410.]))
    if shifted.shape.IsPartner(original.shape):
        assert shifted._dscompare_normalized_digest==original._dscompare_normalized_digest
    else:
        assert getattr(shifted,'_dscompare_normalized_digest',None) is None
