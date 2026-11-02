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
