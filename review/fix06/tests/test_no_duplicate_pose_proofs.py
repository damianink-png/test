"""Same pose 24->48 proofs do not re-run completed negative B-Rep tests."""
from time import monotonic
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.registration_gate import FrameProofCache,frame_support
from dsac29.geometry_registry import GeometryRegistry
from dsac29 import native_guard


def test_completed_no_match_is_not_recomputed_in_48_sample(monkeypatch):
    a=[describe(BRepPrimAPI_MakeBox(10,12,20).Shape(),'A','a')]
    b=[describe(BRepPrimAPI_MakeBox(10,12,20).Shape(),'B','b')]
    cache=FrameProofCache()
    cache.deadline=monotonic()+30
    cache.pair_timeout=5
    # Force independent native verification, despite exactly identical
    # parameters and the possibility of local serialization equality.
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *args:False)
    monkeypatch.setattr(GeometryRegistry,'exact_digest',lambda *args:None)
    calls=[]
    def completed_not_proven(*args,**kwargs):
        calls.append(1)
        return False
    monkeypatch.setattr(native_guard,'guarded_registered_world',completed_not_proven)
    first=frame_support(a,b,.01,proofs=1,proof_cache=cache)
    second=frame_support(a,b,.01,proofs=48,proof_cache=cache)
    assert first['checked']==second['checked']==1
    assert first['proofs']==second['proofs']==0
    assert calls==[1], 'Do not call identical OCC test a second time'
    assert cache.negative_cache_hits>=1
    assert not cache.results, 'Negative is NEVER a certified pair'


def test_native_unknown_is_not_cached_as_completed_negative(monkeypatch):
    a=[describe(BRepPrimAPI_MakeBox(10,12,20).Shape(),'A','a')]
    b=[describe(BRepPrimAPI_MakeBox(10,12,20).Shape(),'B','b')]
    cache=FrameProofCache()
    cache.deadline=monotonic()+30
    cache.pair_timeout=5
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *args:False)
    monkeypatch.setattr(GeometryRegistry,'exact_digest',lambda *args:None)
    def unknown(*args,**kwargs):
        raise native_guard.NativeGeometryFailure('synthetic unknown')
    monkeypatch.setattr(native_guard,'guarded_registered_world',unknown)
    frame_support(a,b,.01,proofs=1,proof_cache=cache)
    assert not cache.results
    assert not cache.completed_negative_pairs
    assert cache.failed_pairs
