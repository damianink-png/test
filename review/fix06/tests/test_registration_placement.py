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
