"""21/24 positive is preliminary evidence, not a failed global frame.

A second 48-pair sample may tolerate revision differences only with complete,
independent, spatially diverse native B-Rep witnesses. No unproved pair is SAME.
"""
from types import SimpleNamespace
import numpy as np
from dsac29 import cad_registration, geometry


def _parts(n=100,types=6,collinear=False):
    return [SimpleNamespace(
        center=np.array([float(i)*10,0. if collinear else float(i%7)*3,
                         0. if collinear else float(i%5)*2]),
        kind=i%types) for i in range(n)]


def test_21_of_24_can_proceed_when_40_of_48_have_independent_native_proofs(monkeypatch):
    monkeypatch.setattr(geometry,'signature',lambda p:p.kind)
    a=_parts()
    proved=[(i,i) for i in range(40)]
    accepted,needs_confirmation,reason=cad_registration._sampled_frame_decision(
        48,40,92,proved,a,.01,24,21,0,100)
    assert accepted and needs_confirmation and 'Warunkowy' in reason
    assert len(proved)==40  # Only these pairs may be certified as SAME.


def test_21_of_24_never_authorizes_a_weak_second_sample(monkeypatch):
    monkeypatch.setattr(geometry,'signature',lambda p:p.kind)
    a=_parts()
    passed,weak,_=cad_registration._sampled_frame_decision(
        48,35,92,[(i,i) for i in range(35)],a,.01,24,21,0,100)
    assert not passed and not weak


def test_20_of_24_and_40_of_48_needs_user_confirmation(monkeypatch):
    monkeypatch.setattr(geometry,'signature',lambda p:p.kind)
    accepted,needs_confirmation,_=cad_registration._sampled_frame_decision(
        48,40,238,[(i,i) for i in range(40)],_parts(),.01,24,20,0,100)
    assert accepted and needs_confirmation


def test_20_of_24_does_not_override_weak_or_ambiguous_evidence(monkeypatch):
    monkeypatch.setattr(geometry,'signature',lambda p:p.kind)
    for parts,positive,pre in [(_parts(),35,20),(_parts(types=1),40,20),
                               (_parts(collinear=True),40,20),(_parts(),40,19)]:
        accepted,_,_=cad_registration._sampled_frame_decision(
            48,positive,92,[(i,i) for i in range(positive)],parts,.01,24,pre,0,100)
        assert not accepted


def test_21_of_24_never_authorizes_ambiguous_repeated_geometries(monkeypatch):
    monkeypatch.setattr(geometry,'signature',lambda p:p.kind)
    for parts in (_parts(types=1),_parts(collinear=True)):
        passed,weak,_=cad_registration._sampled_frame_decision(
            48,40,92,[(i,i) for i in range(40)],parts,.01,24,21,0,100)
        assert not passed and not weak


def test_local_movement_is_not_mistaken_for_global_frame(monkeypatch):
    monkeypatch.setattr(geometry,'signature',lambda p:p.kind)
    a=_parts()
    accepted,needs_confirmation,_=cad_registration._sampled_frame_decision(
        48,40,92,[(i,i) for i in range(40)],a,.01,24,21,90,100)
    assert not accepted and not needs_confirmation


def test_original_90_percent_threshold_is_unchanged(monkeypatch):
    monkeypatch.setattr(geometry,'signature',lambda p:p.kind)
    a=_parts(types=1,collinear=True)
    accepted,weak,_=cad_registration._sampled_frame_decision(
        48,44,92,[(i,i) for i in range(44)],a,.01,24,24,0,100)
    assert accepted and not weak

def test_conditional_consensus_is_not_discarded_by_legacy_weak_sample_veto():
    import inspect
    code=inspect.getsource(cad_registration.propose)
    assert 'if weak and not recovered_sample and (sampled or len(certified)!=votes):' in code
