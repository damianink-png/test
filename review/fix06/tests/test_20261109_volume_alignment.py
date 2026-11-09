"""Regression tests for the 2026-11-09 native error and wrong-Z report.

All matching outcomes remain fail-closed. The displacement scene is synthetic:
the real ZW3D export pair is required before calling the fix field-verified.
"""
import json
from types import SimpleNamespace

import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29 import native_guard, surface_registration, step_reexport_tolerance
from dsac29.alignment import _relocate
from dsac29 import cad_registration
from test_frame_with_local_moves import mixed_scene


def test_invalid_cut_volume_provides_direction_raw_and_geometry_state():
    solid=BRepPrimAPI_MakeBox(5,6,7).Shape()
    op=SimpleNamespace(IsDone=lambda:True)
    def fail(_shape):
        raise ValueError('Invalid material volume -12')
    with pytest.raises(ValueError,match='Invalid material volume') as captured:
        step_reexport_tolerance._ds_checked_cut_volume(
            solid,'B_minus_A',op,.01,volume_fn=fail)
    detail=str(captured.value)
    assert 'direction=B_minus_A' in detail
    assert 'raw=' in detail and 'valid=True' in detail
    assert 'orientation=' in detail and 'CutDone=True' in detail
    assert 'cause=Invalid material volume -12' in detail


@pytest.mark.parametrize('invalid',[-1.0,float('nan'),float('inf')])
def test_invalid_residual_never_becomes_zero_or_same(invalid):
    solid=BRepPrimAPI_MakeBox(5,6,7).Shape()
    op=SimpleNamespace(IsDone=lambda:True)
    with pytest.raises(ValueError,match='Invalid material volume'):
        step_reexport_tolerance._ds_checked_cut_volume(
            solid,'A_minus_B',op,.01,volume_fn=lambda shape:invalid)


def test_native_world_exception_publishes_unknown_and_forces_reset(tmp_path,monkeypatch):
    request=tmp_path/'req.json'
    reply=tmp_path/'reply.json'
    request.write_text(json.dumps({
        'operation':'world_reexport','a':'left.brep','b':'right.brep'}))
    reply.with_suffix('.phase').write_text('validated_solid_symmetric_difference')
    def error(*args,**kwargs):
        raise ValueError('Invalid material volume: direction=A_minus_B; raw=-9')
    monkeypatch.setattr(native_guard,'_worker_unchecked',error)
    class ExitCalled(Exception):pass
    def stop(code):
        assert code==70
        raise ExitCalled()
    monkeypatch.setattr(native_guard.os,'_exit',stop)
    with pytest.raises(ExitCalled):
        native_guard.worker(request,reply)
    payload=json.loads(reply.read_text(encoding='utf-8'))
    assert payload['ok'] is False and payload['status']=='UNVERIFIED'
    assert payload['error_code']=='INVALID_MATERIAL_VOLUME'
    assert payload['operation']=='world_reexport'
    assert payload['a']=='left.brep' and payload['b']=='right.brep'
    assert payload['stage']=='validated_solid_symmetric_difference'
    assert 'direction=A_minus_B' in payload['error']


def test_repeated_face_votes_are_not_independent_parent_parts():
    left=[SimpleNamespace(parent=p) for p in [0]*24+[1]*8+[2]*8+[3]*8]
    right=[SimpleNamespace(parent=p) for p in [0]*24+[1]*8+[2]*8+[3]*8]
    selected=surface_registration._independent_parent_matches(
        [(i,i) for i in range(48)],left,right)
    assert len(selected)==4
    assert {(left[i].parent,right[j].parent) for i,j in selected}=={(i,i) for i in range(4)}
    only_one=surface_registration._independent_parent_matches(
        [(i,i) for i in range(24)],left,right)
    assert len(only_one)==1


def test_user_reported_524mm_z_shift_with_two_local_movements():
    a,b,records,initial=mixed_scene(extra=0,local_mm=220.)
    wanted=np.array([130.,280.,524.])
    b=[_relocate(part,np.eye(3),wanted-initial) for part in b]
    proposal=cad_registration.propose(a,b,records,.01)
    assert proposal is not None and proposal['status']=='registered',proposal
    assert proposal['translation_B_to_A_mm']==pytest.approx(-wanted,abs=.001)
    assert len(proposal['certified_pairs'])>=6
    # A rival at -410 Z from repeated geometry must not replace -524.
    assert abs(proposal['translation_B_to_A_mm'][2]+410.)>100.
