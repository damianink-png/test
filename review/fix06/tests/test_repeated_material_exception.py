from collections import Counter
from dataclasses import replace
import pytest
from dsac29.material_names import material_name_key
from dsac29.repeated_geometry import RepeatedMaterialPolicy
from dsac29.compare import Record
from dsac29.revision_overlap import merge_material_revisions
from test_repeated_revision_policy import parts


@pytest.mark.parametrize('old,new',[
    ('12345_REV_A','12345_REV_B'),
    ('12345_rev.01','12345_rev.02'),
    ('12345_A','12345_B'),
    ('12345_01','12345_02'),
    ('PLATE_123_A2','plate_123_B3.step'),
    ('WSPORNIK_123_REWIZJA_A','WSPORNIK_123_REWIZJA_B'),
    ('12345_REV_A:1','12345_REV_B:8'),
    ('12345_R01','12345_R02'),
    ('12345_REV_A_001','12345_REV_B_002'),
])
def test_separated_revisions_share_whole_name_family(old,new):
    assert material_name_key(old)==material_name_key(new)
    assert material_name_key(old)


@pytest.mark.parametrize('old,new',[
    ('PART_100','PART_200'),
    ('MODEL_P1','MODEL_P2'),
    ('ABC123_REV_A','ABC1234_REV_B'),
    ('12345_LEFT','12345_RIGHT'),
    ('PART_RAIL','PART_REWORK'),
    ('12345_A','98765_A'),
])
def test_similar_fragments_or_drawing_numbers_do_not_share_family(old,new):
    assert material_name_key(old)!=material_name_key(new)


def named(width,count,name):
    return [replace(p,name=name) for p in parts(width=width,count=count)]


def leftovers(a,b):
    return ([Record(i,None,'REMOVED','') for i in range(len(a))]+
            [Record(None,j,'ADDED','') for j in range(len(b))])


def test_equal_eight_copies_with_revision_names_receive_verified_common():
    old=named(10,8,'DRAWING_123_REV_A')
    new=named(11,8,'DRAWING_123_REV_B')
    result,regions,stat=merge_material_revisions(old,new,leftovers(old,new))
    assert Counter(r.status for r in result)=={'CHANGED':8}
    assert len(regions)==8 and not stat.get('incomplete')
    assert stat['repeated_old_admitted']==stat['repeated_new_admitted']==8
    assert stat['boolean_checks']>=1
    assert all('Common' in r.confidence for r in result)


@pytest.mark.parametrize('count,name',[(7,'DRAWING_123_REV_B'),(8,'OTHER_123_REV_B')])
def test_unequal_count_or_unrelated_name_never_runs_common(monkeypatch,count,name):
    old=named(10,8,'DRAWING_123_REV_A')
    new=named(11,count,name)
    def forbidden(*args,**kw):raise AssertionError('Common on a blocked repeated pair')
    monkeypatch.setattr('dsac29.native_guard.guarded_common',forbidden)
    result,regions,stat=merge_material_revisions(old,new,leftovers(old,new))
    assert Counter(r.status for r in result)=={'REMOVED':8,'ADDED':count}
    assert not regions and stat['boolean_checks']==0


def test_counts_include_already_matched_occurrences():
    old=named(10,8,'DRAWING_123_REV_A')
    new=named(11,8,'DRAWING_123_REV_B')
    # Only one leftover on each side; the complete populations still have 8.
    policy=RepeatedMaterialPolicy(old,new)
    assert policy.allows(7,7)
    assert policy.eligible({7},{7})==({7},{7})
    # One free old / one free new must not hide a full-model 8 versus 7.
    policy=RepeatedMaterialPolicy(old,new[:7])
    assert not policy.allows(7,6)
    assert policy.eligible({7},{6})==(set(),set())


def test_equal_total_part_count_cannot_hide_wrong_named_family_counts():
    old=named(10,8,'DRAWING_123_REV_A')
    new=named(11,7,'DRAWING_123_REV_B')+named(11,1,'OTHER_123_REV_B')
    # Separate STEP imports may use distinct native definitions of the same
    # shape; grouping still must not make these distinct names interchangeable.
    policy=RepeatedMaterialPolicy(old,new)
    assert not any(policy.allows(i,j) for i in range(8) for j in range(8))


def test_pair_level_gate_blocks_wrong_family_even_if_both_are_eligible():
    old=named(10,2,'DRAWING_123_REV_A')+named(10,2,'OTHER_123_REV_A')
    new=named(11,2,'DRAWING_123_REV_B')+named(11,2,'OTHER_123_REV_B')
    policy=RepeatedMaterialPolicy(old,new)
    assert policy.eligible(set(range(4)),set(range(4)))==(set(range(4)),set(range(4)))
    assert policy.allows(0,0) and policy.allows(2,2)
    assert not policy.allows(0,2) and not policy.allows(2,0)


def test_technical_names_do_not_admit_repeated_parts():
    old=named(10,3,'NAUO_123')
    new=named(11,3,'NAUO_123')
    policy=RepeatedMaterialPolicy(old,new)
    assert policy.eligible({0,1,2},{0,1,2})==(set(),set())
