import itertools
import random
from types import SimpleNamespace
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import transform
from dsac29.boundary_work import descriptor_scope, cached_faces, verified_face_owner


def test_descriptor_cache_is_request_local_and_placement_aware():
    shape=BRepPrimAPI_MakeBox(10,20,30).Shape()
    calls=[]
    def build(part):
        calls.append(part.shape)
        return len(calls)
    a=SimpleNamespace(shape=shape)
    moved=SimpleNamespace(shape=transform(shape,np.eye(3),np.array([130.,280.,410.])))
    reversed_part=SimpleNamespace(shape=shape.Reversed())
    with descriptor_scope():
        assert cached_faces(a,build)==cached_faces(a,build)==1
        assert cached_faces(moved,build)==2
        assert cached_faces(reversed_part,build)==3
        with descriptor_scope():
            assert cached_faces(a,build)==4
        assert cached_faces(a,build)==1
    with descriptor_scope():
        assert cached_faces(a,build)==5
    assert cached_faces(a,build)==6


def test_lazy_matching_avoids_unneeded_native_checks():
    n=40;calls=[]
    options=[[i]+[j for j in range(n) if j!=i] for i in range(n)]
    owner=verified_face_owner(options,lambda i,j:(calls.append((i,j)) or True))
    assert owner==dict(enumerate(range(n)))
    assert len(calls)==n  # Eager all-candidate proof performs n*n checks.


def test_augmenting_path_keeps_non_greedy_valid_assignment():
    calls=[]
    allowed={(0,0),(0,1),(1,0)}
    def verify(i,j):calls.append((i,j));return (i,j) in allowed
    assert verified_face_owner([[0,1],[0,1]],verify)=={0:1,1:0}
    assert len(calls)==len(set(calls))


def test_lazy_matching_agrees_with_exhaustive_bijections():
    rng=random.Random(6034)
    for n in range(1,6):
        for _ in range(40):
            options=[[j for j in range(n) if rng.random()<.7] for i in range(n)]
            allowed={(i,j) for i in range(n) for j in range(n) if rng.random()<.5}
            possible=any(all(j in options[i] and (i,j) in allowed for i,j in enumerate(order))
                         for order in itertools.permutations(range(n)))
            owner=verified_face_owner(options,lambda i,j:(i,j) in allowed)
            assert (owner is not None)==possible
            if owner is not None:
                assert len(owner)==len(set(owner.values()))==n
                assert all((i,j) in allowed for j,i in owner.items())


def test_real_face_descriptors_reused(monkeypatch):
    from dsac29 import step_reexport_tolerance as module
    a=SimpleNamespace(shape=BRepPrimAPI_MakeBox(10,20,30).Shape())
    native=module._faces_uncached;calls=[]
    def counted(part):calls.append(1);return native(part)
    monkeypatch.setattr(module,'_faces_uncached',counted)
    with descriptor_scope():
        first=module._faces(a)
        assert module._faces(a) is first
        assert len(first)==6
    assert len(calls)==1
    assert len(module._faces(a))==6
    assert len(calls)==2


def test_mixed_surface_types_skip_doomed_descriptor_stage(monkeypatch):
    from dsac29 import step_reexport_tolerance as module
    from dsac29.geometry import describe
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    shape=BRepPrimAPI_MakeBox(10,20,30).Shape()
    a=describe(shape,'a','a')
    b=describe(BRepBuilderAPI_NurbsConvert(shape,True).Shape(),'b','b')
    def forbidden(*args):raise AssertionError('Different face types cannot use this direct proof')
    monkeypatch.setattr(module,'_faces',forbidden)
    phases=[]
    assert not module.reexport_equivalent_world(a,b,.01,allow_boolean=False,progress=phases.append)
    assert phases[-1]=='surface_type_mismatch_requires_normalization'
