import json
from dataclasses import replace
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.geometry import describe
from dsac29.geometry_registry import GeometryRegistry
from dsac29.repeated_geometry import geometry_populations,RepeatedMaterialPolicy
from dsac29.compare import Record
from dsac29.revision_overlap import merge_material_revisions
from dsac29.progress_events import ProgressEvents


def baked(count,depth=5,name='SAME'):
    return [describe(BRepPrimAPI_MakeBox(gp_Pnt(i*57.,0,0),10,20,depth).Shape(),name,str(i)) for i in range(count)]


def test_common_does_not_recount_unrelated_unchanged_families(monkeypatch):
    a=baked(30);b=baked(30)
    a+=baked(1,7,'DRAWING_123_REV_A');b+=baked(1,8,'DRAWING_123_REV_B')
    from dsac29 import native_guard
    monkeypatch.setattr(native_guard,'guarded_rigid',lambda *a,**kw:pytest.fail('Unrelated SAME population rechecked'))
    rows=[Record(i,i,'SAME','known fixture') for i in range(30)]+[Record(30,None,'REMOVED',''),Record(None,30,'ADDED','')]
    result,regions,stat=merge_material_revisions(a,b,rows,geometry_context=GeometryRegistry())
    assert sum(r.status=='SAME' for r in result)==30
    assert sum(r.status=='CHANGED' for r in result)==1 and len(regions)==1


def test_focused_counts_include_copies_already_matched_in_full_revisions():
    a=baked(8,7,'DRAWING_123_REV_A');b=baked(7,8,'DRAWING_123_REV_B')
    policy=RepeatedMaterialPolicy(a,b,old_ids={7},new_ids={6})
    assert policy.sizes_a[7]==8 and policy.sizes_b[6]==7
    assert not policy.allows(7,6)
    assert policy.eligible({7},{6})==(set(),set())


def test_focused_and_full_policy_agree_for_requested_operands():
    a=baked(4,7,'DRAWING_123_REV_A')+baked(3,9,'OTHER_REV_A')
    b=baked(4,8,'DRAWING_123_REV_B')+baked(3,10,'OTHER_REV_B')
    full=RepeatedMaterialPolicy(a,b);focused=RepeatedMaterialPolicy(a,b,old_ids={3},new_ids={3})
    assert focused.sizes_a[3]==full.sizes_a[3]==4
    assert focused.sizes_b[3]==full.sizes_b[3]==4
    assert focused.allows(3,3)==full.allows(3,3)
    assert not focused.allows(0,0)
    with pytest.raises(ValueError):focused.eligible({0},{0})


def test_completed_negative_rigid_proof_is_not_repeated_and_tolerance_is_separate(monkeypatch):
    from dsac29 import native_guard
    a=baked(2);ctx=GeometryRegistry();calls=[]
    monkeypatch.setattr(native_guard,'guarded_rigid',lambda *args,**kw:(calls.append(1) or (False,None,None)))
    assert len(geometry_populations(a,.01,ctx))==2
    assert len(geometry_populations(a,.01,ctx))==2
    assert len(calls)==1
    assert len(geometry_populations(a,.02,ctx))==2
    assert len(calls)==2


def test_native_unknown_is_not_cached_as_false_or_repeat(monkeypatch):
    from dsac29 import native_guard
    a=baked(2);ctx=GeometryRegistry();calls=[]
    def unknown(*args,**kwargs):calls.append(1);raise native_guard.NativeGeometryFailure('fixture timeout')
    monkeypatch.setattr(native_guard,'guarded_rigid',unknown)
    assert len(geometry_populations(a,.01,ctx))==2
    assert len(geometry_populations(a,.01,ctx))==2
    assert len(calls)==2 and ctx.rigid_result(a[0],a[1],.01) is None


def test_preparation_progress_switches_away_from_movement_before_counting(tmp_path):
    a=baked(2,7,'DRAWING_123_REV_A');b=baked(2,8,'DRAWING_123_REV_B')
    path=tmp_path/'progress.jsonl';events=ProgressEvents(path)
    events('Etap transformacji: 2/2')
    rows=[Record(i,None,'REMOVED','') for i in range(2)]+[Record(None,j,'ADDED','') for j in range(2)]
    merge_material_revisions(a,b,rows,progress=events,geometry_context=GeometryRegistry())
    data=[json.loads(line) for line in path.read_text().splitlines()]
    start=next(r for r in data if 'przygotowanie Common' in r['tekst'])
    assert start['phase']=='Weryfikacja materiału'
    assert any('liczby wystąpień' in r['tekst'] for r in data)
