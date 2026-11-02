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
