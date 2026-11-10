"""Regression: shape fingerprint only ranks native proof candidates."""
from types import SimpleNamespace
import math
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.gp import gp_Pnt
from dsac29.geometry import describe
from dsac29.fingerprint_priority import FingerprintPriority

def model(volume=100.,area=140.,eigen=(5.,7.,9.),center=(0.,0.,0.)):
    return SimpleNamespace(volume=volume,area=area,
                           eigenvalues=np.asarray(eigen,float),
                           center=np.asarray(center,float))


def test_shared_store_reused_across_common_and_alignment():
    context=SimpleNamespace()
    left=FingerprintPriority.shared(context)
    right=FingerprintPriority.shared(context)
    assert left is right
    original=model()
    other=model()
    left.distance(original,other)
    assert right.descriptors_computed==2
    right.distance(original,other)
    assert right.descriptors_computed==2


def test_curved_surface_radius_changes_soft_order_but_never_filters():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeTorus
    old=describe(BRepPrimAPI_MakeTorus(28.,3.).Shape(),'old','A')
    wrong=describe(BRepPrimAPI_MakeTorus(28.,6.).Shape(),'wrong','B')
    matching=describe(BRepPrimAPI_MakeTorus(28.,3.1).Shape(),'new','B')
    fp=FingerprintPriority()
    assert fp.surface(old)[2]
    assert fp.distance(old,matching,with_surface=True)<fp.distance(old,wrong,with_surface=True)
    assert fp.surface_analyses==3
    all_candidates=[(-.90,0),(-.89,1)]
    ordered=fp.common_ties(old,all_candidates,[wrong,matching])
    assert set(ordered)==set(all_candidates)
    assert fp.surface_pair_rankings>=2


def test_curved_features_reuse_xcaf_definitions_at_different_placements():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from dsac29.alignment import _relocate
    shape=describe(BRepPrimAPI_MakeCylinder(3.,80.).Shape(),'pipe','old')
    shape.step_definition_key=('source_file','OCAF_label',1)
    moved=_relocate(shape,np.eye(3),np.array([100.,200.,300.]))
    moved.step_definition_key=shape.step_definition_key
    fp=FingerprintPriority()
    first=fp.surface(shape)
    assert first is not None
    assert fp.surface(moved)==first
    assert fp.surface_analyses==1
    assert fp.surface_reuses>=1


def test_different_number_of_faces_is_not_a_false_negative():
    s=BRepPrimAPI_MakeBox(20.,10.,2.).Shape()
    first=BRepPrimAPI_MakeBox(gp_Pnt(0.,0.,0.),10.,10.,2.).Shape()
    second=BRepPrimAPI_MakeBox(gp_Pnt(10.,0.,0.),10.,10.,2.).Shape()
    f=BRepAlgoAPI_Fuse(first,second);f.Build()
    assert f.IsDone()
    a=describe(s,'source','old')
    b=describe(f.Shape(),'repartition','new')
    fp=FingerprintPriority()
    assert fp.distance(a,b)<1.e-6
    assert fp.distance(a,b,with_surface=True)<1.e-6


def test_world_equal_location_prioritizes_correct_fingerprint():
    ref=model()
    wrong=model(area=200.,eigen=(6.,25.,31.))
    right=model()
    rank=FingerprintPriority()
    assert rank.world_ties(ref,[0,1],[wrong,right],.01)==[1,0]
    assert rank.tie_groups==1
    assert rank.descriptors_computed==3
    assert rank.world_ties(ref,[0,1],[wrong,right],.01)==[1,0]
    assert rank.descriptors_computed==3

def test_world_clear_placement_precedes_even_perfect_descriptor():
    ref=model()
    near=model(area=200.,eigen=(5.,8.,10.),center=(0.,0.,0.))
    far=model(center=(2.,0.,0.))
    rank=FingerprintPriority()
    assert rank.world_ties(ref,[0,1],[near,far],.01)==[0,1]
    assert rank.tie_groups==0 and rank.descriptors_computed==0

def test_common_reorders_only_close_overlap_and_never_rejects_any_candidate():
    ref=model()
    wrong=model(area=181.,eigen=(5.,15.,20.))
    right=model(area=140.2,eigen=(5.,7.1,9.))
    poor=model(area=140.,eigen=(5.,7.,9.))
    rank=FingerprintPriority()
    original=[(-.82,0),(-.80,1),(-.50,2)]
    out=rank.common_ties(ref,original,[wrong,right,poor])
    assert out==[(-.80,1),(-.82,0),(-.50,2)]
    assert sorted(out)==sorted(original)
    assert rank.tie_groups==1

def test_bad_shape_properties_cannot_drop_or_prove_any_candidate():
    ref=model()
    damaged=model(area=float('nan'))
    valid=model()
    rank=FingerprintPriority()
    assert rank.world_ties(ref,[0,1],[damaged,valid],.01)==[1,0]
    assert rank.distance(ref,damaged)==float('inf')
    assert len(rank.common_ties(ref,[(-1.,0),(-.99,1)],[damaged,valid]))==2

def test_split_faces_same_material_remains_equal_under_fingerprint():
    original=BRepPrimAPI_MakeBox(20.,10.,2.).Shape()
    one=BRepPrimAPI_MakeBox(gp_Pnt(0,0,0),10.,10.,2.).Shape()
    two=BRepPrimAPI_MakeBox(gp_Pnt(10,0,0),10.,10.,2.).Shape()
    f=BRepAlgoAPI_Fuse(one,two);f.Build()
    assert f.IsDone()
    pair=describe(original,'A','A'),describe(f.Shape(),'B','B')
    rank=FingerprintPriority()
    assert rank.distance(*pair)<1e-6
    # Even a mismatched descriptor never replaces the native B-Rep check.

def test_feature_order_never_treats_same_volume_as_geometry_proof():
    a=model(volume=200,area=150,eigen=(2.,3.,4.))
    b=model(volume=200,area=150,eigen=(2.,3.,4.))
    rank=FingerprintPriority()
    assert rank.distance(a,b)==0.
    # A ranking value is just a float; the native verifier remains mandatory.
