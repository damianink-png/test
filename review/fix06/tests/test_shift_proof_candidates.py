"""Proof selection / rejected-frame regression for DS Compare Portable 0.6.3."""
from types import SimpleNamespace
import numpy as np
from dsac29 import registration_gate, rigid_registration, deferred_alignment


def test_sample_uses_rare_shapes_instead_of_twenty_four_repeated_screws(monkeypatch):
    parts=[]
    for i in range(230):
        kind='fastener' if i<210 else f'unique-{i}'
        parts.append(SimpleNamespace(kind=kind,center=np.array(
            [float(i)*9, float((i*11)%7),float((i*3)%13)]),
            volume=100. if i<210 else 10000.+i))
    monkeypatch.setattr(registration_gate,'signature',lambda p:p.kind)
    pairs=[(i,i) for i in range(len(parts))]
    selected=registration_gate._select_diverse_proof_pairs(pairs,parts,24)
    kinds=[parts[i].kind for i,j in selected]
    assert len(selected)==len(set(selected))==24
    assert sum(k!='fastener' for k in kinds)>=12
    assert selected==registration_gate._select_diverse_proof_pairs(pairs,parts,24)
    assert registration_gate._select_diverse_proof_pairs(pairs,parts,len(pairs))==pairs


def test_rejected_translation_is_not_brep_proved_twice(monkeypatch):
    identity=tuple(map(tuple,np.eye(3)))
    proposal=rigid_registration.Pose(identity,(800.,-400.,100.),241,28,90000.)
    parts=[SimpleNamespace(center=np.array([float(i),0.,0.]),volume=1.) for i in range(380)]
    monkeypatch.setattr(rigid_registration,'propose_rigid_hypotheses',
                        lambda *a,**k:[proposal])
    from dsac29 import alignment,registration_gate as gate
    monkeypatch.setattr(alignment,'_relocate',lambda *a,**k: (_ for _ in ()).throw(
       AssertionError('Do not relocate a native-disproved frame again')))
    monkeypatch.setattr(gate,'frame_support',lambda *a,**k: (_ for _ in ()).throw(
       AssertionError('Do not re-verify a native-disproved frame')))
    result=rigid_registration.propose_verified_rigid(
        parts,parts,0,.01,excluded_translations=[[800.,-400.,100.]])
    assert result is None


def test_stage1_does_not_replay_registration_in_an_independent_fallback(monkeypatch):
    parts=[SimpleNamespace(center=np.array([1.,2.,3.]),volume=10.)]
    monkeypatch.setattr(deferred_alignment,'propose',lambda *a,**k:{'status':'unresolved','reason':'native proof failed'})
    monkeypatch.setattr(rigid_registration,'propose_verified_rigid',
      lambda *a,**k:(_ for _ in ()).throw(AssertionError('Independent fallback replayed')))
    result=deferred_alignment.propose_from_stage1(parts,parts,[],{0},{0},.01)
    assert result['status']=='unresolved'


def test_progress_does_not_claim_coarse_pairs_as_native_proofs():
    import inspect
    source=inspect.getsource(registration_gate._frame_support)
    assert 'wstępnie sparowano' in source
    assert 'B-Rep niepotwierdzony' in source
    assert 'potwierdzono {len(owner)}' not in source
