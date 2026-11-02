"""An assembly-only Common failure must not lose a genuine CHANGED pair."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.compare import Record
from dsac29 import revision_overlap as overlap,native_guard

def test_retry_common_failure_falls_back_to_validated_regions(monkeypatch):
    a=[describe(BRepPrimAPI_MakeBox(10.,10.,10.).Shape(),'part','part')]
    b=[describe(BRepPrimAPI_MakeBox(11.,10.,10.).Shape(),'part','part')]
    records=[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')]
    real_calculate=overlap.calculate
    calls={'regions':0}
    def fail_common(*args,**kwargs):
        raise native_guard.NativeGeometryFailure('assembly-only Common failure')
    def flaky_regions(*args,**kwargs):
        calls['regions']+=1
        if calls['regions']==1:
            raise native_guard.NativeGeometryFailure('assembly resource context failure')
        return real_calculate(*args,**kwargs)
    monkeypatch.setattr(native_guard,'guarded_common',fail_common)
    monkeypatch.setattr(overlap,'calculate',flaky_regions)
    result,cache,stat=overlap.merge_material_revisions(a,b,records,review_approval=lambda _:'review')
    assert [r.status for r in result]==['CHANGED']
    assert stat['retry_budget_attempted']>=1
    assert stat['retry_budget_recovered']>=1
    assert calls['regions']>=2
    assert cache
