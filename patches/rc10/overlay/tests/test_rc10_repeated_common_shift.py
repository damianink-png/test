from collections import Counter
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from test_r7_alignment_preview import occurrence
from dsac29.compare import compare, Record, ShiftDetected
from dsac29.revision_rules import classify_revisions
from dsac29.revision_overlap import merge_material_revisions
from dsac29.deferred_alignment import propose_from_stage1
from dsac29.repetition import repeated_ids


def parts(width=10, shift=0, separate=False):
    shape=BRepPrimAPI_MakeBox(20,width,7).Shape()
    return [occurrence(BRepPrimAPI_MakeBox(20,width,7).Shape() if separate else shape,
                       f'P{i}',i*57+shift,i*i*3) for i in range(8)]


@pytest.mark.parametrize('separate',[False,True])
def test_eight_changed_copies_split_and_never_common(monkeypatch,separate):
    a,b=parts(separate=separate),parts(11,separate=separate)
    # Four leftovers plus four heuristic pairs reproduce mixed classification.
    records=[Record(i,None,'REMOVED','') for i in range(4)]
    records += [Record(None,i,'ADDED','') for i in range(4)]
    records += [Record(i,i,'UNCERTAIN','Podobne gabaryty',
                       confidence='Heurystyka — sprawdź parę') for i in range(4,8)]
    classified=classify_revisions(a,b,records)
    assert Counter(r.status for r in classified)=={'REMOVED':8,'ADDED':8}
    def forbidden(*args,**kwargs):raise AssertionError('Common on repeated parts')
    monkeypatch.setattr('dsac29.revision_overlap._precise_world_bounds',forbidden)
    result,regions,stats=merge_material_revisions(a,b,classified)
    assert result==classified and not regions and stats['boolean_checks']==0
    assert stats['repeated_old_skipped']==stats['repeated_new_skipped']==8


def test_full_comparison_of_changed_copies():
    a,b=parts(),parts(11)
    records=classify_revisions(a,b,compare(a,b,revision_only=True,exact_serialization=True))
    result,regions,stats=merge_material_revisions(a,b,records)
    assert Counter(r.status for r in result)=={'REMOVED':8,'ADDED':8}
    assert not regions and stats['boolean_checks']==0


def test_repetition_includes_already_matched_occurrences(monkeypatch):
    a,b=parts(),parts(11)
    records=[Record(i,i,'SAME','proof') for i in range(7)]
    records += [Record(7,None,'REMOVED',''),Record(None,7,'ADDED','')]
    result,regions,stats=merge_material_revisions(a,b,records)
    assert result==records and not regions
    assert stats['repeated_old_skipped']==stats['repeated_new_skipped']==1


def test_failure_and_proven_moves_remain_visible():
    a,b=parts(),parts(shift=500)
    records=[Record(i,i,'MOVED','B-Rep proof') for i in range(7)]
    records += [Record(7,7,'UNCERTAIN','failure',confidence='Błąd testu B-Rep — sprawdź parę')]
    result=classify_revisions(a,b,records)
    assert Counter(r.status for r in result)=={'MOVED':7,'UNCERTAIN':1}


@pytest.mark.parametrize('shift',[57,1000])
def test_shift_of_repeated_assembly_before_rigid(shift):
    a,b=parts(),parts(shift=shift)
    b=list(reversed(b))  # STEP occurrence order does not identify a part.
    hook=lambda rec,fa,fb:propose_from_stage1(a,b,rec,fa,fb,.01)
    with pytest.raises(ShiftDetected) as caught:
        compare(a,b,revision_only=True,exact_serialization=True,stage1_check=hook)
    proposal=caught.value.proposal
    assert np.allclose(proposal['translation_B_to_A_mm'],[-shift,0,0])
    assert len(proposal['certified_pairs'])==8


def test_single_solid_translation():
    a,b=parts()[:1],parts(shift=500)[:1]
    proposal=propose_from_stage1(a,b,[],{0},{0},.01)
    assert proposal['status']=='registered'
    assert np.allclose(proposal['translation_B_to_A_mm'],[-500,0,0])


def test_unique_names_do_not_hide_repeated_geometry():
    assert repeated_ids(parts(separate=True))==set(range(8))


def test_one_local_move_does_not_register_whole_assembly():
    a,b=parts(),parts()
    b[-1]=parts(shift=5)[-1]
    records=compare(a,b,revision_only=True,exact_serialization=True,
                    stage1_check=lambda rec,fa,fb:propose_from_stage1(a,b,rec,fa,fb,.01))
    assert Counter(r.status for r in records)=={'SAME':7,'MOVED':1}


def test_competitive_offsets_beyond_budget_cannot_certify_uniqueness(monkeypatch):
    from dsac29 import deferred_alignment
    shape=BRepPrimAPI_MakeBox(20,10,7).Shape()
    a=[occurrence(shape,'P',i*50,0) for i in range(40)]
    b=[occurrence(shape,'P',i*50+10000,0) for i in range(40)]
    records=[Record(i,None,'REMOVED','') for i in range(40)]
    records += [Record(None,i,'ADDED','') for i in range(40)]
    calls=[]
    def partial_proof(*args,**kwargs):
        calls.append(1)
        # Only eight pairs prove equal; the remaining coarse candidates fail.
        return {'count':8,'pairs':[(i,i) for i in range(8)]}
    monkeypatch.setattr(deferred_alignment,'frame_support',partial_proof)
    result=deferred_alignment.propose(a,b,records,.01)
    assert result['status']=='unresolved' and len(calls)==16
    assert 'Limit' in result['reason']
