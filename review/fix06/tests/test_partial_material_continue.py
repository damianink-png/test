"""One broken CAD pair must not invalidate an independently proven revision."""
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29 import native_guard,revision_overlap,material_deltas
from dsac29.compare import Record
from dsac29.geometry import describe

def part(x,length,name):
    return describe(BRepPrimAPI_MakeBox(gp_Pnt(x,0,0),length,10,10).Shape(),name,name)

def dataset():
    a=[part(0,10,'bad_old'),part(100,10,'good_old')]
    b=[part(0,11,'bad_new'),part(100,11,'good_new')]
    return a,b,[Record(0,None,'REMOVED',''),Record(1,None,'REMOVED',''),
                Record(None,0,'ADDED',''),Record(None,1,'ADDED','')]

def test_recover_only_failed_pair(monkeypatch):
    a,b,records=dataset()
    checks=[]
    def common(old,new,tol):
        from dsac29.geometry import _precise_world_bounds
        x=_precise_world_bounds(old)[0];checks.append(x)
        if x<50:raise native_guard.NativeGeometryFailure('single failed native Common')
        return material_deltas.operate(material_deltas.BRepAlgoAPI_Common,old,new,tol)
    monkeypatch.setattr(native_guard,'guarded_common',common)
    def alternative(old,new,tol,**kwargs):
        if old.name=='bad_old':
            raise native_guard.NativeGeometryFailure('alternative cannot prove bad pair')
        return material_deltas.calculate(old,new,tol,**kwargs)
    monkeypatch.setattr(revision_overlap,'calculate',alternative)
    proposals=[]
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,records,review_approval=lambda p:proposals.append(p) or 'review')
    assert len(checks)==3 and len(proposals)==1
    assert stat['retry_failure_attempted']==1
    assert stat['retry_failure_failed']==1
    assert stat['accepted']==1 and stat['incomplete']
    assert stat['unverified_A']==stat['unverified_B']==1
    assert stat['failed_pair']=={'a_index':0,'b_index':0}
    assert [(r.a_index,r.b_index,r.status) for r in out]==[
        (None,0,'UNCERTAIN'),(1,1,'CHANGED'),(0,None,'UNCERTAIN')]
    assert regions[1].regions.common_mm3>900
    assert {r.a_index for r in out if r.a_index is not None}=={0,1}
    assert {r.b_index for r in out if r.b_index is not None}=={0,1}

def test_strict_and_refused_review(monkeypatch):
    a,b,records=dataset()
    def fail(*args,**kwargs):raise native_guard.NativeGeometryFailure('bad')
    monkeypatch.setattr(native_guard,'guarded_common',fail)
    monkeypatch.setattr(revision_overlap,'calculate',fail)
    with pytest.raises(native_guard.NativeGeometryFailure,match='bad'):
        revision_overlap.merge_material_revisions(a,b,records)
    with pytest.raises(InterruptedError,match='raportu częściowego'):
        revision_overlap.merge_material_revisions(a,b,records,review_approval=lambda p:'cancel')

def test_unchecked_candidates_are_not_labeled_as_new(monkeypatch):
    a,b,records=dataset()
    monkeypatch.setattr(revision_overlap,'MAX_CHECKS',0)
    proposals=[]
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,records,review_approval=lambda p:proposals.append(p) or 'review')
    assert stat['budget_exceeded'] and stat['incomplete']
    assert stat['boolean_checks']==0 and not regions
    assert {r.status for r in out}=={'UNCERTAIN'} and len(proposals)==1


def test_alternative_shared_filler_recovers_single_native_common_failure(monkeypatch):
    a,b,records=dataset()
    def failed_common(*args,**kwargs):
        raise native_guard.NativeGeometryFailure('OCCT Common returned impossible signed volume -791 mm3')
    monkeypatch.setattr(native_guard,'guarded_common',failed_common)
    monkeypatch.setattr(revision_overlap,'calculate',material_deltas.calculate)
    result,regions,stat=revision_overlap.merge_material_revisions(a,b,records)
    assert stat['alternative_region_recovery']==2
    assert stat['accepted']==2 and not stat['incomplete']
    assert {r.status for r in result}=={'CHANGED'}
    assert len(regions)==2
    assert all(x.regions.common_mm3>900 for x in regions.values())


def test_negative_only_screen_never_excludes_genuine_changed_parts():
    from dsac29.common_exclusion import screen
    a,b,_=dataset()
    proof=screen(a[0].shape,b[0].shape,.01,.68*max(a[0].volume,b[0].volume))
    assert not proof['excluded']
