from collections import Counter
from dataclasses import replace
import weakref
import gc
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.compare import compare,Record,ShiftDetected
from dsac29.geometry_registry import GeometryRegistry
from dsac29.repeated_geometry import repeated_ids
from dsac29.revision_rules import classify_revisions
from dsac29.revision_overlap import merge_material_revisions
from dsac29.deferred_alignment import propose_from_stage1


def parts(width=10,shift=0,count=8,separate=False,baked=False,name_prefix="P"):
    prototype=BRepPrimAPI_MakeBox(20,width,7).Shape()
    result=[]
    for i in range(count):
        x,y=i*57+shift,i*i*3
        if baked:
            shape=BRepPrimAPI_MakeBox(gp_Pnt(float(x),float(y),0.),20,width,7).Shape()
            p=describe(shape,f'{name_prefix}{i}',f'assembly/{name_prefix}{i}')
        else:
            shape=BRepPrimAPI_MakeBox(20,width,7).Shape() if separate else prototype
            p=_relocate(describe(shape,f'{name_prefix}{i}',f'assembly/{name_prefix}{i}'),np.eye(3),np.array([x,y,0.]))
        result.append(p)
    return result


@pytest.mark.parametrize('mode',['native','separate','baked'])
def test_entire_revised_population_skips_common_without_survivor(monkeypatch,mode):
    old=parts(separate=mode=='separate',baked=mode=='baked')
    new=parts(11,separate=mode=='separate',baked=mode=='baked',name_prefix='Q')
    records=compare(old,new,revision_only=True,exact_serialization=True)
    records=classify_revisions(old,new,records,geometry_first=True)
    def forbidden(*args,**kwargs):raise AssertionError('Common must not run for repeated details')
    monkeypatch.setattr('dsac29.native_guard.guarded_common',forbidden)
    result,regions,stat=merge_material_revisions(old,new,records,review_approval=lambda _:'review')
    assert Counter(r.status for r in result)=={'REMOVED':8,'ADDED':8}
    assert not regions and stat['boolean_checks']==0 and not stat.get('incomplete')
    assert stat['removed_repeated_occurrences_excluded']==8
    assert stat['added_repeated_occurrences_excluded']==8


def test_four_heuristic_pairs_and_four_leftovers_are_consistent():
    old,new=parts(),parts(11,name_prefix="Q")
    records=[Record(i,None,'REMOVED','') for i in range(4)]
    records += [Record(None,j,'ADDED','') for j in range(4)]
    records += [Record(i,i,'UNCERTAIN','Ambiguous',confidence='Heurystyka — sprawdź parę') for i in range(4,8)]
    result=classify_revisions(old,new,records,geometry_first=True)
    assert Counter(r.status for r in result)=={'REMOVED':8,'ADDED':8}
    result,regions,stat=merge_material_revisions(old,new,result)
    assert Counter(r.status for r in result)=={'REMOVED':8,'ADDED':8}
    assert not regions and stat['boolean_checks']==0


def test_already_matched_copies_still_count_and_failure_stays_uncertain():
    old,new=parts(),parts(11,name_prefix="Q")
    records=[Record(i,i,'SAME','proof') for i in range(6)]
    records += [Record(6,6,'UNCERTAIN','Native failure',confidence='Błąd testu B-Rep — sprawdź parę'),
                Record(7,None,'REMOVED',''),Record(None,7,'ADDED','')]
    result=classify_revisions(old,new,records,geometry_first=True)
    result,regions,stat=merge_material_revisions(old,new,result)
    assert Counter(r.status for r in result)=={'SAME':6,'UNCERTAIN':1,'REMOVED':1,'ADDED':1}
    assert stat['boolean_checks']==0


def test_similar_descriptors_are_not_repeat_proof(monkeypatch):
    old=parts(count=1)+parts(width=12,count=1)
    old[1]=replace(old[1],volume=old[0].volume,area=old[0].area,eigenvalues=old[0].eigenvalues.copy())
    monkeypatch.setattr('dsac29.native_guard.guarded_rigid',lambda *a,**kw:(False,None,None))
    assert repeated_ids(old)==set()


def test_registry_retains_occurrence_objects_and_rejects_stale_id():
    registry=GeometryRegistry()
    occurrences=parts()
    definition=registry.definition(occurrences[0])
    p=occurrences[1]
    assert registry.definition(p)==definition
    ref=weakref.ref(p)
    del occurrences,p
    gc.collect()
    assert ref() is not None
    different=parts(width=12,count=1)[0]
    registry._part_ids[id(different)]=(definition,ref())
    assert registry.definition(different)!=definition


@pytest.mark.parametrize('shift',[57,1000])
def test_reordered_repeated_assembly_shift(shift):
    old,new=parts(),list(reversed(parts(shift=shift)))
    hook=lambda rec,fa,fb:propose_from_stage1(old,new,rec,fa,fb,.01)
    with pytest.raises(ShiftDetected) as caught:
        compare(old,new,revision_only=True,exact_serialization=True,stage1_check=hook)
    proposal=caught.value.proposal
    assert np.allclose(proposal['translation_B_to_A_mm'],[-shift,0,0])
    assert len(proposal['certified_pairs'])==8


def test_single_solid_shift_is_verified():
    old,new=parts(count=1),parts(shift=500,count=1)
    proposal=propose_from_stage1(old,new,[],{0},{0},.01)
    assert proposal['status']=='registered'
    assert np.allclose(proposal['translation_B_to_A_mm'],[-500,0,0])


def test_local_move_does_not_shift_assembly():
    old,new=parts(),parts()
    new[-1]=_relocate(new[-1],np.eye(3),np.array([5.,0,0]))
    records=compare(old,new,revision_only=True,exact_serialization=True,
                    stage1_check=lambda rec,fa,fb:propose_from_stage1(old,new,rec,fa,fb,.01))
    assert Counter(r.status for r in records)=={'SAME':7,'MOVED':1}


def test_periodic_pitch_shift_cannot_hide_in_world_overlap():
    shape=BRepPrimAPI_MakeBox(20,10,7).Shape()
    old=[_relocate(describe(shape,'P','P'),np.eye(3),np.array([50.*i,0,0])) for i in range(35)]
    new=[_relocate(p,np.eye(3),np.array([50.,0,0])) for p in old]
    hook=lambda rec,fa,fb:propose_from_stage1(old,new,rec,fa,fb,.01)
    with pytest.raises(ShiftDetected) as caught:
        compare(old,new,revision_only=True,exact_serialization=True,stage1_check=hook)
    assert np.allclose(caught.value.proposal['translation_B_to_A_mm'],[-50,0,0])


def test_unchecked_competitive_translation_cannot_certify_unique_pose(monkeypatch):
    from dsac29 import deferred_alignment
    shape=BRepPrimAPI_MakeBox(20,10,7).Shape()
    old=[_relocate(describe(shape,'P','P'),np.eye(3),np.array([50.*i,0,0])) for i in range(40)]
    new=[_relocate(p,np.eye(3),np.array([10000.,0,0])) for p in old]
    records=[Record(i,None,'REMOVED','') for i in range(40)]
    records += [Record(None,j,'ADDED','') for j in range(40)]
    calls=[]
    def proof(*args,**kw):
        calls.append(kw)
        if not kw.get('verify_all'):
            return {'count':40,'checked':24,'proofs':24}
        return {'count':8,'checked':8,'proofs':8,'pairs':[(i,i) for i in range(8)]}
    monkeypatch.setattr(deferred_alignment,'frame_support',proof)
    result=deferred_alignment.propose(old,new,records,.01)
    assert result['status']=='unresolved'
    assert 'limit' in result['reason'].casefold()
    # The unified registration engine has a 12-hypothesis native budget.
    # A bounded, unfinished search must not announce a unique placement.
    assert sum(kw.get('verify_all',False) for kw in calls)==12
