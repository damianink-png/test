"""Assembly-level regression: low overlap is not a changed revision."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.compare import Record
from dsac29.geometry import describe
from dsac29 import revision_overlap
from types import SimpleNamespace

def test_nonfinite_common_never_becomes_revision_match():
    ref=SimpleNamespace(volume=1000.0)
    for bad in (float('nan'),float('inf'),float('-inf'),-1.0):
        assert revision_overlap._score(bad,ref,ref,True) is None
    assert revision_overlap._score(850.0,ref,ref,True) is not None


def part(x, length, name):
    return describe(BRepPrimAPI_MakeBox(gp_Pnt(x, 0, 0), length, 10, 10).Shape(), name, name)

def records(a, b):
    return ([Record(i, None, 'REMOVED', '') for i in range(len(a))] +
            [Record(None, j, 'ADDED', '') for j in range(len(b))])

def test_two_real_revisions_survive_unrelated_overlapping_parts():
    a = [part(0, 10, 'rev1_old'), part(100, 12, 'rev2_old'),
         part(200, 14, 'removed_part')]
    b = [part(0, 11, 'rev1_new'), part(100, 13, 'rev2_new'),
         part(207, 14, 'new_unrelated')]
    out, regions, stats = revision_overlap.merge_material_revisions(
        a, b, records(a, b), review_approval=lambda _: 'review')
    changed = {(r.a_index, r.b_index) for r in out if r.status == 'CHANGED'}
    assert changed == {(0, 0), (1, 1)}
    assert {(r.a_index, r.b_index, r.status) for r in out if r.status != 'CHANGED'} == {
        (2, None, 'REMOVED'), (None, 2, 'ADDED')}
    assert not stats.get('incomplete')
    assert len(regions) == 2
    assert stats['brep_calls_total'] >= stats['boolean_checks'] >= 2
    assert sum(stats['brep_calls_by_phase'].values()) == stats['brep_calls_total']
    assert set(stats['brep_seconds_by_phase']) == set(stats['brep_calls_by_phase'])
    assert all(v >= 0 for v in stats['brep_seconds_by_phase'].values())

def test_separate_budget_recovers_unchecked_real_revision(monkeypatch):
    a = [part(0, 10, 'old1'), part(100, 12, 'old2')]
    b = [part(0, 11, 'new1'), part(100, 13, 'new2')]
    monkeypatch.setattr(revision_overlap, 'MAX_CHECKS', 1)
    out, regions, stats = revision_overlap.merge_material_revisions(
        a, b, records(a, b), review_approval=lambda _: 'review')
    assert stats['boolean_checks'] == 1
    assert stats['retry_budget_attempted'] == 1
    assert stats['retry_budget_recovered'] == 1
    assert stats['brep_calls_by_phase'].get('revision_budget_retry_regions',0) == 1
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
    a=[part(50*i,10+2*i,'old_'+str(i)) for i in range(count)]
    b=[part(50*i,11+2*i,'new_'+str(i)) for i in range(count)]
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


def test_four_repeated_renamed_removed_parts_do_not_become_uncertain(monkeypatch):
    """Four duplicates of a confirmed survivor must bypass broken Common."""
    from dsac29 import native_guard
    a=[part(x,10,'DUPLICATE_A_'+str(k)) for k,x in enumerate([0,25,50,75,100])]
    b=[part(100,10,'DIFFERENT_STEP_LABEL'),part(0,11,'NEW_PART')]
    # Simulate independent B-Rep copies with exact definition proofs.
    group={id(p) for p in a}|{id(b[0])}
    class ExactContext:
        def has_rigid_proof(self,left,right,tolerance):return False
        def same_definition(self,left,right):
            return id(left) in group and id(right) in group
    saved=[Record(i,None,'REMOVED','') for i in range(4)]+[
        Record(4,0,'SAME','CAD matched this instance'),
        Record(None,1,'ADDED','')]
    def should_not_boolean(*args,**kwargs):
        raise AssertionError('A repeated, verified part should not enter Common')
    monkeypatch.setattr(native_guard,'guarded_common',should_not_boolean)
    result,regions,stat=revision_overlap.merge_material_revisions(
        a,b,saved,geometry_context=ExactContext(),review_approval=lambda _: 'review')
    assert len([x for x in result if x.status=='REMOVED'])==4
    assert len([x for x in result if x.status=='SAME'])==1
    assert len([x for x in result if x.status=='ADDED'])==1
    assert all(x.status!='UNCERTAIN' for x in result)
    assert stat['removed_repeated_occurrences_excluded']==4
    assert stat['repeated_signature_fallback_proofs']==4
    assert stat['boolean_checks']==0 and not stat.get('incomplete')
    assert not regions


def test_added_occurrences_of_surviving_geometry_dont_enter_material_common(monkeypatch):
    """A mirrored population change must not masquerade as a material revision."""
    from dsac29 import native_guard
    a=[part(100,10,'origin-name'),part(0,11,'unrelated-old')]
    b=[part(100,10,'surviving-new-name')]+[
        part(x,10,'fresh-step-name-'+str(k)) for k,x in enumerate([0,25,50,75])]
    group={id(a[0])}|{id(p) for p in b}
    class ExactContext:
        def has_rigid_proof(self,left,right,tolerance):return False
        def same_definition(self,left,right):
            return id(left) in group and id(right) in group
    saved=[Record(0,0,'RENAMED','proven'),Record(1,None,'REMOVED','')]
    saved.extend(Record(None,k,'ADDED','') for k in range(1,5))
    monkeypatch.setattr(native_guard,'guarded_common',
                        lambda *x,**kw:(_ for _ in ()).throw(AssertionError('unexpected Common')))
    result,regions,stat=revision_overlap.merge_material_revisions(
        a,b,saved,geometry_context=ExactContext(),review_approval=lambda _: 'review')
    assert len([r for r in result if r.status=='ADDED'])==4
    assert all(r.status!='UNCERTAIN' for r in result)
    assert stat['added_repeated_occurrences_excluded']==4
    assert stat['boolean_checks']==0 and not stat.get('incomplete')


def test_similar_signature_and_name_cannot_replace_exact_geometry_proof():
    """Never reclassify real changes merely because volume/signature resemble."""
    from dsac29 import native_guard
    a=[part(0,10,'A'),part(25,10,'B')]
    b=[part(25,10,'C'),part(0,11,'D')]
    class NoProof:
        def has_rigid_proof(self,left,right,tolerance):return False
        def same_definition(self,left,right):return False
    saved=[Record(0,None,'REMOVED',''),Record(1,0,'SAME',''),Record(None,1,'ADDED','')]
    result,regions,stat=revision_overlap.merge_material_revisions(
        a,b,saved,geometry_context=NoProof(),review_approval=lambda _: 'review')
    assert stat['removed_repeated_occurrences_excluded']==0
    assert stat['added_repeated_occurrences_excluded']==0
    # The unmatched pair remains eligible for independent Common/Cut.
    assert stat['boolean_checks']>=1


def test_repeat_uses_proven_surviving_pair_without_requiring_cross_step_brep_bytes():
    """A and B independently exported same geometry; only within-A copies are exact."""
    a=[part(x,10,'A_copy_'+str(k)) for k,x in enumerate([0,25,50,75,100])]
    b=[part(100,10,'B_exported_survivor'),part(0,11,'new_part')]
    within_a={id(p) for p in a}
    class IndependentExports:
        def has_rigid_proof(self,left,right,tolerance):return False
        def same_definition(self,left,right):
            # Neither A nor its duplicates are byte-equal to B's STEP B-Rep.
            return id(left) in within_a and id(right) in within_a
    existing=[Record(i,None,'REMOVED','') for i in range(4)]
    existing += [Record(4,0,'SAME','geometrically proven surviving pair'),
                 Record(None,1,'ADDED','')]
    result,regions,stat=revision_overlap.merge_material_revisions(
        a,b,existing,geometry_context=IndependentExports(),
        review_approval=lambda _: 'review')
    assert stat['removed_repeated_occurrences_excluded']==4
    assert stat['boolean_checks']==0 and not stat.get('incomplete')
    assert len([r for r in result if r.status=='REMOVED'])==4
    assert not any(r.status=='UNCERTAIN' for r in result)


def test_unverified_surviving_record_cannot_be_used_to_suppress_material_comparison():
    """A placeholder UNCERTAIN pair is not a positive reference for duplicates."""
    a=[part(0,10,'repeat'),part(100,10,'repeat')]
    b=[part(100,10,'repeat'),part(0,11,'revision')]
    class LocalCopy:
        def has_rigid_proof(self,left,right,tolerance):return False
        def same_definition(self,left,right):
            return id(left) in {id(a[0]),id(a[1])} and id(right) in {id(a[0]),id(a[1])}
    existing=[Record(0,None,'REMOVED',''),Record(1,0,'UNCERTAIN','not verified'),
              Record(None,1,'ADDED','')]
    result,regions,stat=revision_overlap.merge_material_revisions(
        a,b,existing,geometry_context=LocalCopy(),review_approval=lambda _: 'review')
    # The UNCERTAIN survivor remains unproven. Independent WITHIN-A
    # definition proofs now suffice to exclude the repeated removed detail.
    assert stat['removed_repeated_occurrences_excluded']==1
    assert stat['boolean_checks']==0
    assert any(r.status=='UNCERTAIN' for r in result)


def test_dominated_failed_candidate_cannot_erase_a_proven_renamed_revision(monkeypatch):
    """An unrelated Common error must not taint a decisive verified alternative."""
    from dsac29 import native_guard
    from dsac29.geometry import _precise_world_bounds
    a=[part(0,10,'old_repeated')]
    b=[part(0,11,'renamed_revised'),part(2,10.9,'unrelated_second')]
    real_common=native_guard.guarded_common
    real_regions=revision_overlap.calculate
    def broken_wrong_candidate(sa,sb,*args,**kwargs):
        if _precise_world_bounds(sb)[0]>=1:
            raise native_guard.NativeGeometryFailure('OCCT Common failed on unrelated candidate')
        return real_common(sa,sb,*args,**kwargs)
    def broken_wrong_regions(left,right,*args,**kwargs):
        if right.name=='unrelated_second':
            raise native_guard.NativeGeometryFailure('Unrelated isolated Cut also failed')
        return real_regions(left,right,*args,**kwargs)
    monkeypatch.setattr(native_guard,'guarded_common',broken_wrong_candidate)
    monkeypatch.setattr(revision_overlap,'calculate',broken_wrong_regions)
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,[Record(0,None,'REMOVED',''),Record(None,0,'ADDED',''),Record(None,1,'ADDED','')],
        review_approval=lambda _:'review')
    assert {(r.a_index,r.b_index,r.status) for r in out}=={
        (0,0,'CHANGED'),(None,1,'ADDED')}
    assert stat['dominated_failed_candidates']>=1
    assert stat['accepted']==1 and not stat['incomplete']


def test_unresolved_candidate_is_not_discarded_by_weak_alternative(monkeypatch):
    from dsac29 import native_guard
    a=[part(0,10,'old')]
    b=[part(2,11,'renamed_new')]
    def fail(*args,**kwargs):
        raise native_guard.NativeGeometryFailure('Native OCC failed')
    monkeypatch.setattr(native_guard,'guarded_common',fail)
    monkeypatch.setattr(revision_overlap,'calculate',fail)
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')],
        review_approval=lambda _:'review')
    assert stat['incomplete'] is True
    assert {r.status for r in out}=={'UNCERTAIN'}


def test_repeated_renamed_changed_definition_bypasses_automatic_common():
    """Changed copies remain visible as removed old and added new geometry."""
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    def make_occurrences(length,prefix):
        prototype=BRepPrimAPI_MakeBox(length,10,10).Shape()
        parts=[]
        for number in range(4):
            tr=gp_Trsf()
            tr.SetTranslation(gp_Vec(float(number*40),0,0))
            parts.append(describe(prototype.Moved(TopLoc_Location(tr)),
                                  prefix+str(number),prefix+'/'+str(number)))
        return parts
    a=make_occurrences(10,'old')
    b=make_occurrences(11,'renamed_new')
    records=([Record(i,None,'REMOVED','') for i in range(4)]+
             [Record(None,j,'ADDED','') for j in range(4)])
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,records,review_approval=lambda _:'review')
    assert {r.status for r in out}=={'REMOVED','ADDED'}
    assert stat['accepted']==0 and not stat.get('incomplete')
    assert stat['boolean_checks']==0 and not regions


def test_repeated_material_timeout_is_not_retried_on_unchanged_operands(monkeypatch):
    import subprocess
    from dsac29 import native_guard
    old=[part(0,10,'same_old')]
    new=[part(0,11,'same_new')]
    called=[]
    def timeout(*args,**kwargs):
        called.append(1)
        try: raise subprocess.TimeoutExpired(cmd='material',timeout=120)
        except subprocess.TimeoutExpired as native:
            raise native_guard.NativeGeometryFailure('OCCT material timeout') from native
    monkeypatch.setattr(revision_overlap,'calculate',timeout)
    records=[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')]
    out,regions,stat=revision_overlap.merge_material_revisions(
        old,new,records,review_approval=lambda _:'review')
    assert len(called)==1
    assert stat['region_retry_skipped_timeout']==1
    assert stat['incomplete']
    assert {r.status for r in out}=={'UNCERTAIN'}


def _distinct_occurrence(length, position, name):
    """Separate TopoDS definitions, identical LOCAL geometry, different placement."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.TopLoc import TopLoc_Location
    shape=BRepPrimAPI_MakeBox(float(length),10.,10.).Shape()
    tr=gp_Trsf()
    tr.SetTranslation(gp_Vec(float(position),0,0))
    return describe(shape.Moved(TopLoc_Location(tr)),name,f'{name}/{position}')


def test_separately_exported_repeated_revisions_bypass_automatic_common():
    from dsac29.geometry_registry import GeometryRegistry
    a=[_distinct_occurrence(10,x,'old_ring') for x in (0,40,80,120)]
    b=[_distinct_occurrence(11,x,'renamed_ring') for x in (0,40,80,120)]
    assert not a[0].shape.IsPartner(a[1].shape)
    assert GeometryRegistry().same_definition(a[0],a[1])
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,records(a,b),review_approval=lambda _:'review')
    assert {r.status for r in out}=={'REMOVED','ADDED'}
    assert stat['boolean_checks']==0
    assert not regions and not stat.get('incomplete')
    assert stat['repeated_old_population']==stat['repeated_new_population']==4


def test_full_brep_proof_reuse_rejects_wrong_relative_placement_and_geometry():
    a=[_distinct_occurrence(10,x,'old') for x in (0,40)]
    b=[_distinct_occurrence(11,x,'renamed') for x in (0,40)]
    saved=revision_overlap._TranslatedProofIndex()
    saved.save(a[0],b[0],123.0)
    assert saved.find(a[1],b[1])[2]==123.0
    assert saved.find(a[0],b[1]) is None
    other=_distinct_occurrence(12,40,'renamed_but_other_geometry')
    assert saved.find(a[1],other) is None


def test_exact_definitions_cannot_reuse_at_same_location_or_different_rotation():
    from OCP.gp import gp_Trsf, gp_Ax1, gp_Dir, gp_Pnt
    from OCP.TopLoc import TopLoc_Location
    from math import pi
    a0=_distinct_occurrence(10,0,'a0')
    b0=_distinct_occurrence(11,0,'b0')
    same_location_a=_distinct_occurrence(10,0,'copy')
    same_location_b=_distinct_occurrence(11,0,'copy')
    index=revision_overlap._TranslatedProofIndex()
    index.save(a0,b0,1.0)
    # Overlapping occurrences must not collapse into one-to-many aliases.
    assert index.find(same_location_a,same_location_b) is None
    shifted_a=_distinct_occurrence(10,50,'x')
    rotated_b=_distinct_occurrence(11,50,'x')
    rot=gp_Trsf()
    rot.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(0,0,1)),pi/2)
    from dsac29.geometry import describe
    rotated_b=describe(rotated_b.shape.Moved(TopLoc_Location(rot)),'rotated','rotated')
    assert index.find(shifted_a,rotated_b) is None


def test_repeated_cohort_bypasses_native_errors_in_every_occurrence(monkeypatch):
    """The complete repeated revision cohort never enters material Common."""
    from dsac29 import native_guard,common_exclusion
    from dsac29.native_guard import NativeGeometryFailure
    a=[_distinct_occurrence(10,x,'Entwurf_11067438_Oese.1') for x in (0,40,80,120)]
    b=[_distinct_occurrence(11,x,'Ringoese') for x in (0,40,80,120)]
    original_common=native_guard.guarded_common
    original_regions=revision_overlap.calculate
    called=[]
    def flaky_common(x,y,*args,**kwargs):
        called.append(1)
        if len(called)<=2:
            raise NativeGeometryFailure('synthetic OCCT native failure')
        return original_common(x,y,*args,**kwargs)
    def flaky_regions(old,new,*args,**kwargs):
        if old.path.endswith(('/0','/40')):
            raise NativeGeometryFailure('synthetic regions failure')
        return original_regions(old,new,*args,**kwargs)
    monkeypatch.setattr(native_guard,'guarded_common',flaky_common)
    monkeypatch.setattr(revision_overlap,'calculate',flaky_regions)
    def exclusion_failure(*args,**kwargs):
        raise NativeGeometryFailure('unproven exclusion')
    monkeypatch.setattr(common_exclusion,'guarded_exclusion',exclusion_failure)
    out,regions,stat=revision_overlap.merge_material_revisions(
        a,b,records(a,b),review_approval=lambda _:'review')
    assert called==[]  # Exclude the whole repeated cohort before any failure.
    assert stat.get('retry_failure_attempted',0)==0
    assert {r.status for r in out}=={'REMOVED','ADDED'}
    assert not regions and not stat.get('incomplete')


def test_assembly_wallclock_does_not_skip_later_native_pairs(monkeypatch):
    """Elapsed time is telemetry, never proof that later candidates were checked."""
    old=[part(0,10,'old_first'),part(100,12,'old_second')]
    new=[part(0,11,'new_first'),part(100,13,'new_second')]
    ticks=[0.0]
    def fake_clock():
        ticks[0]+=1000.0  # exceed the former 240-900 s shared budget
        return ticks[0]
    monkeypatch.setattr(revision_overlap,'perf_counter',fake_clock)
    result,regions,stats=revision_overlap.merge_material_revisions(
        old,new,records(old,new),review_approval=lambda _:'review')
    assert stats['guarded_budget_seconds'] is None
    assert stats['guarded_budget_mode']=='per_pair'
    assert stats['boolean_checks']==2
    assert not stats['budget_exceeded'] and not stats['incomplete']
    assert len(regions)==2 and {r.status for r in result}=={'CHANGED'}


def test_recovery_wallclock_does_not_starve_later_pairs(monkeypatch):
    """Each distinct unverified pair is retried despite earlier long operations."""
    old=[part(50*i,10+2*i,'old_'+str(i)) for i in range(4)]
    new=[part(50*i,11+2*i,'new_'+str(i)) for i in range(4)]
    monkeypatch.setattr(revision_overlap,'MAX_CHECKS',1)
    ticks=[0.0]
    def fake_clock():
        ticks[0]+=1000.0  # previously skipped the entire retry queue
        return ticks[0]
    monkeypatch.setattr(revision_overlap,'perf_counter',fake_clock)
    result,regions,stats=revision_overlap.merge_material_revisions(
        old,new,records(old,new),review_approval=lambda _:'review')
    assert stats['retry_budget_seconds'] is None
    assert stats['retry_budget_mode']=='per_pair'
    assert stats['retry_skipped_due_to_time']==0
    assert stats['retry_budget_attempted']==3
    assert stats['retry_budget_recovered']==3
    assert stats['accepted']==4 and not stats['incomplete']
    assert len(regions)==4 and {r.status for r in result}=={'CHANGED'}


def test_invalid_source_tolerance_does_not_repeat_native_probe(monkeypatch):
    """OpenArm: the original STEP cannot pass a lower tolerance on a retry."""
    from dsac29 import native_guard, common_exclusion
    a=[part(0,10,'bad_tolerance_old')]
    b=[part(0,11,'bad_tolerance_new')]
    calls={'common':0,'regions':0,'exclude':0}
    def invalid_common(*args,**kwargs):
        calls['common']+=1
        raise native_guard.NativeGeometryFailure(
            'UnprovenRepair: Original STEP stored tolerance exceeds CAD budget')
    def invalid_regions(*args,**kwargs):
        calls['regions']+=1
        raise native_guard.NativeGeometryFailure('INVALID_BREP_AFTER_REPAIR')
    def invalid_exclusion(*args,**kwargs):
        calls['exclude']+=1
        raise native_guard.NativeGeometryFailure('No exclusion proof')
    monkeypatch.setattr(native_guard,'guarded_common',invalid_common)
    monkeypatch.setattr(revision_overlap,'calculate',invalid_regions)
    monkeypatch.setattr(common_exclusion,'guarded_exclusion',invalid_exclusion)
    out,_,stat=revision_overlap.merge_material_revisions(
        a,b,records(a,b),review_approval=lambda _:'review')
    assert calls=={'common':1,'regions':1,'exclude':1}
    assert stat['retry_skipped_unproductive']==1
    assert stat['retry_failure_attempted']==0
    assert stat['failed_pairs'][0]['code']=='INVALID_INPUT_TOLERANCE'
    assert stat['incomplete'] and {r.status for r in out}=={'UNCERTAIN'}


def test_both_native_timeouts_do_not_repeat_unchanged_pair(monkeypatch):
    """Once Common and the independent material fallback timed out, stop retrying."""
    from dsac29 import native_guard,common_exclusion
    a=[part(0,10,'timeout_old')]
    b=[part(0,11,'timeout_new')]
    calls={'common':0,'regions':0}
    def common_timeout(*args,**kwargs):
        calls['common']+=1
        raise native_guard.NativeGeometryFailure(
            'Timeout odizolowanej operacji Common — wynik rewizji niekompletny')
    def regions_timeout(*args,**kwargs):
        calls['regions']+=1
        raise native_guard.NativeGeometryFailure(
            'Obliczenie Common/Cut nieukończone (limit 180 s)')
    monkeypatch.setattr(native_guard,'guarded_common',common_timeout)
    monkeypatch.setattr(revision_overlap,'calculate',regions_timeout)
    monkeypatch.setattr(common_exclusion,'guarded_exclusion',
                        lambda *args,**kwargs: (_ for _ in ()).throw(
                            native_guard.NativeGeometryFailure('no proof')))
    out,_,stat=revision_overlap.merge_material_revisions(
        a,b,records(a,b),review_approval=lambda _:'review')
    assert calls=={'common':1,'regions':1}
    assert stat['retry_skipped_unproductive']==1
    assert stat['retry_failure_attempted']==0
    assert stat['failed_pairs'][0]['code']=='REPEATED_NATIVE_TIMEOUT'
    assert stat['incomplete'] and {r.status for r in out}=={'UNCERTAIN'}



def test_two_terminal_native_failures_skip_expensive_third_probe(monkeypatch):
    """A source-bound negative native result must stay UNCERTAIN, not be retried 3 times."""
    from dsac29.native_guard import NativeGeometryFailure
    a=[part(0,10,'REV_A')]
    b=[part(0,11,'REV_B')]
    records=[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')]
    calls={'common':0,'regions':0,'exclusion':0}
    def common(*args,**kwargs):
        calls['common']+=1
        raise NativeGeometryFailure(
            'Odizolowany OCC Common zakończył się błędem 70 RuntimeError: '
            'OCCT Boolean returned invalid or null topology')
    def regions(*args,**kwargs):
        calls['regions']+=1
        raise NativeGeometryFailure(
            'MATERIAL_BOOLEAN_UNVERIFIED: RuntimeError: '
            'OCCT Boolean returned invalid or null topology')
    def exclusion(*args,**kwargs):
        calls['exclusion']+=1
        raise AssertionError('Do not repeat deterministic invalid native topology')
    monkeypatch.setattr('dsac29.native_guard.guarded_common',common)
    monkeypatch.setattr(revision_overlap,'calculate',regions)
    monkeypatch.setattr('dsac29.common_exclusion.guarded_exclusion',exclusion)
    result,_,stat=revision_overlap.merge_material_revisions(
        a,b,records,review_approval=lambda _:'review')
    assert calls=={'common':1,'regions':1,'exclusion':0}
    assert stat['exclusion_skipped_terminal_failures']==1
    assert stat['retry_skipped_unproductive']==1
    assert stat['retry_failure_attempted']==0
    assert {r.status for r in result}=={'UNCERTAIN'}
