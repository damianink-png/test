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
    ('Pokrywa_01','Pokrywa_02'),
    ('WSPORNIK_A1','WSPORNIK_B2'),
    ('PLATE_123_A2','plate_123_B3.step'),
    ('WSPORNIK_123_REWIZJA_A','WSPORNIK_123_REWIZJA_B'),
    ('12345_REV_A:1','12345_REV_B:8'),
    ('12345_R01','12345_R02'),
    ('12345_REV_A_001','12345_REV_B_002'),
    ('czesc1_afm0','czesc1_afm2'),
    ('czesc1_afm00','CZESC1_AFM02'),
    ('czesc1_afm0','czesc1_xyz2'),
    ('czesc1_afm0.step:1','czesc1_afm2.stp:8'),
    ('12345_REV_A.step:1','12345_REV_B.stp:8'),
])
def test_separated_revisions_share_whole_name_family(old,new):
    assert material_name_key(old)==material_name_key(new)
    assert material_name_key(old)


@pytest.mark.parametrize('old,new',[
    ('PART_100','PART_200'),
    ('BRACKET_100','BRACKET_200'),
    ('MODEL_01','MODEL_02'),
    ('MODEL_P1','MODEL_P2'),
    ('ABC123_REV_A','ABC1234_REV_B'),
    ('12345_LEFT','12345_RIGHT'),
    ('PART_RAIL','PART_REWORK'),
    ('12345_A','98765_A'),
    ('czesc1_afm0','czesc2_xyz2'),
    ('czesc1_afm100','czesc1_afm200'),
    ('czesc1afm0','czesc1afm2'),
    ('czesc1_afm0_REV_A','czesc1_afm2_REV_B'),
    ('12345_LEWY_afm0','12345_PRAWY_afm2'),
])
def test_similar_fragments_or_drawing_numbers_do_not_share_family(old,new):
    assert material_name_key(old)!=material_name_key(new)


def named(width,count,name):
    return [replace(p,name=name) for p in parts(width=width,count=count)]


def leftovers(a,b):
    return ([Record(i,None,'REMOVED','') for i in range(len(a))]+
            [Record(None,j,'ADDED','') for j in range(len(b))])


@pytest.mark.parametrize('old_name,new_name',[
    ('DRAWING_123_REV_A','DRAWING_123_REV_B'),
    ('czesc1_afm0','czesc1_afm2'),
    ('czesc1_afm0','czesc1_xyz2'),
])
def test_equal_eight_copies_with_revision_names_receive_verified_common(old_name,new_name):
    old=named(10,8,old_name)
    new=named(11,8,new_name)
    result,regions,stat=merge_material_revisions(old,new,leftovers(old,new))
    assert Counter(r.status for r in result)=={'CHANGED':8}
    assert len(regions)==8 and not stat.get('incomplete')
    assert stat['repeated_old_admitted']==stat['repeated_new_admitted']==8
    assert stat['boolean_checks']>=1
    assert all('Common' in r.confidence for r in result)


@pytest.mark.parametrize('count,name',[(7,'czesc1_afm2'),(8,'czesc2_xyz2')])
def test_afm_revisions_still_require_equal_populations_and_same_base(monkeypatch,count,name):
    old=named(10,8,'czesc1_afm0');new=named(11,count,name)
    def forbidden(*args,**kwargs):raise AssertionError('Blocked AFM family reached Common')
    monkeypatch.setattr('dsac29.native_guard.guarded_common',forbidden)
    result,regions,stat=merge_material_revisions(old,new,leftovers(old,new))
    assert Counter(r.status for r in result)=={'REMOVED':8,'ADDED':count}
    assert not regions and stat['boolean_checks']==0


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
    # The unique residual after confirmed stationary matches is allowed
    # to reach real Common/Cut even though whole-family quantities differ.
    assert policy.eligible({7},{6})==({7},{6})
    assert policy.allows(7,6)


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


def test_renamed_survivor_does_not_block_equal_named_revision_population():
    from dsac29.geometry_registry import GeometryRegistry
    old=named(10,2,'DRAWING_123_REV_A')
    new=[replace(old[0],name='OTHER_SURVIVING_DETAIL')]+named(11,2,'DRAWING_123_REV_B')
    saved=[Record(0,0,'SAME','verified'),Record(1,None,'REMOVED',''),
           Record(None,1,'ADDED',''),Record(None,2,'ADDED','')]
    result,regions,stat=merge_material_revisions(
        old,new,saved,geometry_context=GeometryRegistry())
    assert Counter(r.status for r in result)=={'SAME':1,'CHANGED':1,'ADDED':1}
    assert len(regions)==1 and stat['repeated_old_admitted']==1
    assert stat['removed_repeated_occurrences_excluded']==0


def test_unequal_populations_with_many_unmatched_repetitions_remain_blocked():
    old=named(10,8,'DRAWING_123_REV_A')
    new=named(11,7,'DRAWING_123_REV_B')
    policy=RepeatedMaterialPolicy(old,new,old_ids=set(range(8)),new_ids=set(range(7)))
    assert policy.eligible(set(range(8)),set(range(7)))==(set(),set())
    assert not policy.allows(0,0)


def test_unequal_populations_unique_residual_real_material_change():
    old=named(10,8,'DRAWING_123_REV_A')
    new=named(11,7,'DRAWING_123_REV_B')
    # Seven stationary/verified matches could leave exactly one potential
    # changed pair; full counts alone must not censor its Common operation.
    policy=RepeatedMaterialPolicy(old,new,old_ids={7},new_ids={6})
    assert policy.eligible({7},{6})==({7},{6})
    assert policy.allows(7,6)
