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
    from dsac29 import surface_registration
    # Isolate body-sample admission from independent preserved-face proofs.
    monkeypatch.setattr(surface_registration,'propose',lambda *a,**kw:None)
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
        assert 48<=len(proposal["certified_pairs"])<=72
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


def test_sparse_shift_requires_explicit_confirmation_even_with_all_brep_proofs():
    from test_r14_sparse_shift import case
    a,b,records=case()
    proposal=reg.propose(a,b,records,.01)
    assert proposal["status"]=="registered"
    assert proposal["requires_confirmation"] is True
    assert len(proposal["certified_pairs"])==8
    assert not proposal["full_pair_map"]


def test_logging_automatic_alignment_does_not_crash(tmp_path,monkeypatch):
    from dsac29 import cli
    from test_r14_stage1_shift import parts
    a,b=parts(n=40,stable=40,offset=1000)
    pa=tmp_path/"a.step";pb=tmp_path/"b.step"
    pa.write_text("x");pb.write_text("y")
    monkeypatch.setattr(cli,"load_step",lambda path,**kwargs:a if path==pa else b)
    out=tmp_path/"results";out.mkdir()
    messages=[]
    cli.process(pa,pb,out,step=False,diff_step=False,full_bom=False,
                revision_style=True,auto_align=True,progress=messages.append)
    assert any("Wyrównuję automatycznie" in m for m in messages)
    assert (out/"PODSUMOWANIE.json").exists()


def test_recycled_world_session_preserves_independent_pair_verdicts(monkeypatch):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from dsac29.geometry import describe
    from dsac29 import native_guard, native_session
    left = describe(BRepPrimAPI_MakeBox(8,7,9).Shape(), 'a', 'a')
    same = describe(BRepPrimAPI_MakeBox(8,7,9).Shape(), 'b', 'b')
    changed = describe(BRepPrimAPI_MakeBox(10,7,9).Shape(), 'c', 'c')
    starts = []
    original_start = native_session.WorldSession._start
    def counted_start(self):
        starts.append(1)
        return original_start(self)
    monkeypatch.setattr(native_session.WorldSession, '_start', counted_start)
    with native_session.world_session(True):
        assert native_guard.guarded_world_reexport(left, same, .01) is True
        assert native_guard.guarded_world_reexport(left, changed, .01) is False
        assert native_guard.guarded_world_reexport(left, same, .01) is True
    assert len(starts) == 1


def test_large_registered_final_comparison_uses_native_session():
    from dsac29 import cli
    import inspect
    source = inspect.getsource(cli.process)
    assert 'with world_session(max(len(a),len(b))>=80 or registered_frame)' in source
