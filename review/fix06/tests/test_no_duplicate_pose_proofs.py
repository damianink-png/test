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



def test_transient_native_failure_in_one_repeated_copy_can_recover_on_next(monkeypatch):
    """First timeout must not automatically reject 5 identical occurrences."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from dsac29.alignment import _relocate
    from dsac29.geometry import describe
    import numpy as np
    base_a=describe(BRepPrimAPI_MakeBox(15,12,10).Shape(),'A','A')
    base_b=describe(BRepPrimAPI_MakeBox(15,12,10).Shape(),'B','B')
    a=[_relocate(base_a,np.eye(3),np.array([i*47.,0.,0.])) for i in range(6)]
    b=[_relocate(base_b,np.eye(3),np.array([i*47.,0.,0.])) for i in range(6)]
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *args:False)
    monkeypatch.setattr(GeometryRegistry,'exact_digest',lambda *args:None)
    tries=[]
    def transient(*args,**kwargs):
        tries.append(1)
        if len(tries)==1:
            raise native_guard.NativeGeometryFailure('simulated transient OCC interruption')
        return True
    monkeypatch.setattr(native_guard,'guarded_registered_world',transient)
    cache=FrameProofCache()
    cache.deadline=monotonic()+30.
    result=frame_support(a,b,.01,verify_all=True,proof_cache=cache)
    assert result['count']>=5,result
    assert len(tries)==2, 'One failure must not poison later occurrences'
    assert not cache.skipped_repeat_failures
