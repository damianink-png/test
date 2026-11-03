"""Assembly-level regression: low overlap is not a changed revision."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.compare import Record
from dsac29.geometry import describe
from dsac29 import revision_overlap

def part(x, length, name):
    return describe(BRepPrimAPI_MakeBox(gp_Pnt(x, 0, 0), length, 10, 10).Shape(), name, name)

def records(a, b):
    return ([Record(i, None, 'REMOVED', '') for i in range(len(a))] +
            [Record(None, j, 'ADDED', '') for j in range(len(b))])

def test_two_real_revisions_survive_unrelated_overlapping_parts():
    a = [part(0, 10, 'rev1_old'), part(100, 10, 'rev2_old'),
         part(200, 10, 'removed_part')]
    b = [part(0, 11, 'rev1_new'), part(100, 11, 'rev2_new'),
         part(207, 10, 'new_unrelated')]
    out, regions, stats = revision_overlap.merge_material_revisions(
        a, b, records(a, b), review_approval=lambda _: 'review')
    changed = {(r.a_index, r.b_index) for r in out if r.status == 'CHANGED'}
    assert changed == {(0, 0), (1, 1)}
    assert {(r.a_index, r.b_index, r.status) for r in out if r.status != 'CHANGED'} == {
        (2, None, 'REMOVED'), (None, 2, 'ADDED')}
    assert not stats.get('incomplete')
    assert len(regions) == 2

def test_separate_budget_recovers_unchecked_real_revision(monkeypatch):
    a = [part(0, 10, 'old1'), part(100, 10, 'old2')]
    b = [part(0, 11, 'new1'), part(100, 11, 'new2')]
    monkeypatch.setattr(revision_overlap, 'MAX_CHECKS', 1)
    out, regions, stats = revision_overlap.merge_material_revisions(
        a, b, records(a, b), review_approval=lambda _: 'review')
    assert stats['boolean_checks'] == 1
    assert stats['retry_budget_attempted'] == 1
    assert stats['retry_budget_recovered'] == 1
    assert stats['accepted'] == 2 and not stats['incomplete']
    assert {r.status for r in out} == {'CHANGED'}
    assert len(regions) == 2


def test_failed_common_in_large_scan_is_retried_in_fresh_isolated_process(monkeypatch):
    """A real CHANGED pair must not become UNCERTAIN after one transient failure."""
    from dsac29 import native_guard
    from dsac29.native_guard import NativeGeometryFailure
    a=[part(0,10,'old_revision')]
    b=[part(0,11,'new_revision')]
    actual_common=native_guard.guarded_common
    actual_regions=revision_overlap.calculate
    attempts={'common':0,'regions':0}
    def transient_common(*args,**kwargs):
        attempts['common']+=1
        if attempts['common']==1:
            raise NativeGeometryFailure('transient full-assembly Common failure')
        return actual_common(*args,**kwargs)
    def transient_regions(*args,**kwargs):
        attempts['regions']+=1
        if attempts['regions']==1:
            raise NativeGeometryFailure('transient full-assembly regions failure')
        return actual_regions(*args,**kwargs)
    monkeypatch.setattr(native_guard,'guarded_common',transient_common)
    monkeypatch.setattr(revision_overlap,'calculate',transient_regions)
    out,regions,stats=revision_overlap.merge_material_revisions(
        a,b,records(a,b),review_approval=lambda _: 'review')
    assert [r.status for r in out]==['CHANGED']
    assert stats['retry_failure_attempted']==1
    assert stats['retry_failure_recovered']==1
    assert stats['retry_failure_failed']==0
    assert not stats['incomplete']
    assert attempts['common']>=2
    assert len(regions)==1


def test_retries_failed_final_cut_without_cached_common(monkeypatch):
    """A transient final material split must not leave a correctly paired part UNCERTAIN."""
    from dsac29.native_guard import NativeGeometryFailure
    a=[part(0,10,'revised_part')]
    b=[part(0,11,'revised_part')]
    actual=revision_overlap.calculate
    seen=[]
    def flaky_final_regions(*args,**kwargs):
        seen.append(kwargs)
        if len(seen)==1:
            raise NativeGeometryFailure('final Cut failed during assembly analysis')
        return actual(*args,**kwargs)
    monkeypatch.setattr(revision_overlap,'calculate',flaky_final_regions)
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,records(a,b),review_approval=lambda _: 'review')
    assert [r.status for r in out]==['CHANGED']
    assert stat['region_retry_attempted']==1
    assert stat['region_retry_recovered']==1
    assert stat['region_retry_failed']==0
    assert len(seen)==2
    assert 'common_shape' not in seen[1]  # no stale Common in the retry
    assert not stat['incomplete'] and len(regions)==1


def test_removed_duplicate_is_not_misclassified_as_changed_revision():
    """A removed occurrence of a surviving shared part stays REMOVED, not CHANGED."""
    class KnownGeometry:
        def has_rigid_proof(self,one,two,tolerance):
            return one.name==two.name and abs(one.volume-two.volume)<tolerance
    a=[part(0,10,'repeat'),part(100,10,'repeat')]
    b=[part(100,10,'repeat'),part(0,11,'different_part')]
    existing=[Record(0,None,'REMOVED',''),
              Record(1,0,'SAME',''),
              Record(None,1,'ADDED','')]
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,existing,geometry_context=KnownGeometry(),review_approval=lambda _: 'review')
    assert {(r.a_index,r.b_index,r.status) for r in out}=={
        (0,None,'REMOVED'),(1,0,'SAME'),(None,1,'ADDED')}
    assert stat['removed_repeated_occurrences_excluded']==1
    assert stat['boolean_checks']==0
    assert not regions and not stat.get('incomplete')


def test_retry_budget_handles_more_than_original_sixteen_pair_limit(monkeypatch):
    """Correctly matched independent revisions past the 16th candidate get a retry."""
    count=18
    a=[part(50*i,10,'old_'+str(i)) for i in range(count)]
    b=[part(50*i,11,'new_'+str(i)) for i in range(count)]
    monkeypatch.setattr(revision_overlap,'MAX_CHECKS',1)
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,records(a,b),review_approval=lambda _: 'review')
    assert stat['retry_budget_attempted']==count-1
    assert stat['retry_budget_recovered']==count-1
    assert stat['accepted']==count and not stat['incomplete']
    assert {r.status for r in out}=={'CHANGED'}
    assert len(regions)==count


def test_removed_duplicate_uses_exact_definition_without_cached_rigid_proof():
    """Exact native/B-Rep definition may be known although no pairwise proof was cached."""
    a=[part(0,10,'repeat'),part(100,10,'repeat')]
    b=[part(100,10,'repeat'),part(0,11,'new_other')]
    known={id(a[0]),id(a[1]),id(b[0])}
    class ExactDefinitions:
        def has_rigid_proof(self,left,right,tolerance):
            return False  # no preceding A-to-A comparisons
        def same_definition(self,left,right):
            return id(left) in known and id(right) in known
    existing=[Record(0,None,'REMOVED',''),
              Record(1,0,'SAME',''),
              Record(None,1,'ADDED','')]
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,existing,geometry_context=ExactDefinitions(),review_approval=lambda _: 'review')
    assert {(r.a_index,r.b_index,r.status) for r in out}=={
        (0,None,'REMOVED'),(1,0,'SAME'),(None,1,'ADDED')}
    assert stat['removed_repeated_occurrences_excluded']==1
    assert stat['boolean_checks']==0 and not regions


def test_removed_repeat_with_renamed_survivor_is_not_a_material_change():
    """Renaming a still-present identical occurrence must not revive a removed duplicate."""
    a=[part(0,10,'repeat'),part(100,10,'repeat')]
    b=[part(100,10,'renamed_survivor'),part(0,11,'unrelated')]
    same_group={id(a[0]),id(a[1]),id(b[0])}
    class ExactDefinitions:
        def has_rigid_proof(self,left,right,tolerance):return False
        def same_definition(self,left,right):
            return id(left) in same_group and id(right) in same_group
    previous=[Record(0,None,'REMOVED',''),
              Record(1,0,'RENAMED',''),
              Record(None,1,'ADDED','')]
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,previous,geometry_context=ExactDefinitions(),review_approval=lambda _: 'review')
    assert {(r.a_index,r.b_index,r.status) for r in out}=={
        (0,None,'REMOVED'),(1,0,'RENAMED'),(None,1,'ADDED')}
    assert stat['removed_repeated_occurrences_excluded']==1
    assert stat['boolean_checks']==0 and not regions


def test_spatial_interval_index_never_drops_possible_brep_candidate():
    """Broad-phase must conservatively match brute force, including tolerance."""
    import numpy as np
    rng=np.random.default_rng(12345)
    bounds={}
    for j in range(600):
        origin=rng.uniform(-3000,3000,size=3)
        length=rng.uniform(0.001,500,size=3)
        bounds[j]=np.concatenate((origin,origin+length))
    index=revision_overlap._XIntervalIndex(bounds)
    for _ in range(140):
        origin=rng.uniform(-3000,3000,size=3)
        length=rng.uniform(0.001,500,size=3)
        query=np.concatenate((origin,origin+length))
        for tol in (0.0,0.01,2.5):
            observed=list(index.candidates(query,tol))
            expected=[j for j,v in bounds.items()
                      if v[0]<=query[3]+tol and v[3]+tol>=query[0]]
            assert len(observed)==len(set(observed))
            assert set(observed)==set(expected)


def test_spatial_interval_index_handles_touching_and_large_sparse_assemblies():
    import numpy as np
    bounds={j:np.array([float(j*100),0,0,float(j*100+10),10,10])
            for j in range(2500)}
    index=revision_overlap._XIntervalIndex(bounds)
    touched=np.array([10010.0,0,0,10100.0,10,10])
    assert list(index.candidates(touched,0.0))==[100,101]
    query=np.array([123510.006,0,0,123520,10,10])
    assert list(index.candidates(query,0.01))==[1235]
    assert list(index.candidates(query,0.0))==[]
    assert list(index.candidates(np.array([-1000,0,0,-500,10,10]),.01))==[]
