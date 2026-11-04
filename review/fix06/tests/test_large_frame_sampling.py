"""Regression for a large, shifted STEP revision which previously crashed.

An approximate spatial match may propose a registration, but only real B-Rep
proofs may be inherited as certified pairs. Remaining parts must be checked
by the final revision comparator.
"""
import pytest
from dsac29.compare import Record
from dsac29 import deferred_alignment as reg
from test_r13_deferred_alignment import models


@pytest.mark.parametrize("sample_passes",[True,False])
def test_large_shift_never_launches_full_native_preverification(monkeypatch,sample_passes):
    a,b=models(count=601,stable=601,shift=1000)
    existing=[Record(i,None,"REMOVED","") for i in range(len(a))]
    existing.extend(Record(None,j,"ADDED","") for j in range(len(b)))
    requests=[]
    def fake_support(left,right,tolerance,proofs=8,verify_all=False,
                     proof_cache=None,**kwargs):
        assert not verify_all, "Large hypothesis must avoid a 601-part native preflight"
        requests.append(proofs)
        count=min(proofs,601)
        confirmed=count if sample_passes else 2
        if proof_cache is not None:
            for k in range(confirmed):
                index=k*(600)//max(1,count-1)
                proof_cache.results[(index,index)]=True
        return dict(count=601,ratio=1.,checked=count,
                    proofs=confirmed,pairs=[])
    monkeypatch.setattr(reg,"frame_support",fake_support)
    proposal=reg.propose(a,b,existing,.01)
    assert requests and max(requests)<=48,requests
    if sample_passes:
        assert proposal["status"]=="registered"
        assert proposal["verification_scope"]=="sample_then_final_compare"
        assert proposal["translation_B_to_A_mm"]==pytest.approx([-1000.,0.,0.])
        assert proposal["votes"]==601  # only positional support
        assert proposal["checked_sample_count"]==48
        assert proposal["verified_sample_count"]==48
        assert len(proposal["certified_pairs"])<=48
        assert set(proposal["certified_pairs"])<=set((i,i) for i in range(601))
        assert not proposal["full_pair_map"]
    else:
        assert proposal is None or proposal.get("status")!="registered"


def test_small_assembly_keeps_full_native_proof(monkeypatch):
    a,b=models(count=40,stable=40,shift=1000)
    existing=[Record(i,None,"REMOVED","") for i in range(len(a))]
    existing.extend(Record(None,j,"ADDED","") for j in range(len(b)))
    operations=[]
    def fake_support(left,right,tolerance,proofs=8,verify_all=False,
                     proof_cache=None,**kwargs):
        operations.append(bool(verify_all))
        if verify_all:
            return dict(count=40,ratio=1.,checked=40,proofs=40,
                        pairs=[(i,i) for i in range(40)])
        return dict(count=40,ratio=1.,checked=min(24,40),
                    proofs=min(24,40))
    monkeypatch.setattr(reg,"frame_support",fake_support)
    proposal=reg.propose(a,b,existing,.01)
    assert proposal["status"]=="registered"
    assert proposal["verification_scope"]=="full_brep"
    assert len(proposal["certified_pairs"])==40
    assert operations.count(True)>0
