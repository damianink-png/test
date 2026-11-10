"""Regression for legacy safety gates that made large revisions UNCERTAIN."""
import numpy as np
from dsac29.assignment import assign
from dsac29 import deferred_alignment


def fake_parts(centers):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from dsac29.geometry import describe
    from dsac29.alignment import _relocate
    base=describe(BRepPrimAPI_MakeBox(1,2,3).Shape(),'repeat','repeat')
    return [_relocate(base,np.eye(3),np.array([float(x),0.,0.])-base.center) for x in centers]


def test_large_strict_rows_not_all_uncertain():
    n=65
    edges={(i,i):0. for i in range(n)}
    edges.update({(i,i+1):.35 for i in range(n-1)})
    edges.update({(i,i-1):.45 for i in range(1,n)})
    result=assign(edges)
    assert len(result)==n
    assert all(a==b and not uncertain and gap>.025 for a,b,uncertain,gap in result)


def test_large_equal_options_stay_uncertain():
    edges={(i,i):.2 for i in range(65)}
    edges.update({(i,(i+1)%65):.2 for i in range(65)})
    out=assign(edges)
    assert len(out)==65 and all(uncertain for _,_,uncertain,_ in out)


def test_large_global_conflict_stays_conservative():
    edges={(i,j):(0. if i==j else 1.) for i in range(65) for j in range(65)}
    edges.update({(0,0):.09,(0,1):.11,(1,0):.01,(1,1):.21})
    chosen=assign(edges)
    assert {(i,j) for i,j,*_ in chosen if i<2}=={(0,1),(1,0)}
    assert all(uncertain for _,_,uncertain,_ in chosen)


def test_unequal_repeats_do_not_trigger_global_shift(monkeypatch):
    a=fake_parts(range(100));b=fake_parts(list(range(1,100))+[150,180])
    assert not deferred_alignment._periodic_global_offset_possible(
        a,b,.01,100,free_a={0},free_b={99,100},baseline=99)


def test_periodic_one_pitch_shift_remains_detectable(monkeypatch):
    a=fake_parts([i*40 for i in range(30)])
    b=fake_parts([i*40+40 for i in range(30)])
    assert deferred_alignment._periodic_global_offset_possible(
        a,b,.01,30,free_a={0},free_b={29},baseline=29)


def test_unshifted_1482_of_1597_stays_in_world_frame(monkeypatch):
    a=fake_parts([i*30 for i in range(1597)])
    b=fake_parts([i*30 for i in range(1482)]+[100000+i*30 for i in range(115)])
    assert not deferred_alignment._periodic_global_offset_possible(
        a,b,.01,1597,free_a=set(range(1482,1597)),
        free_b=set(range(1482,1597)),baseline=1482)



def test_stationary_1597_part_majority_avoids_global_pose_search(monkeypatch):
    from dsac29 import cad_pose_search,unique_anchors
    a=fake_parts([i*30 for i in range(1597)])
    b=fake_parts([i*30 for i in range(1482)]+[100000+i*30 for i in range(115)])
    def forbidden(*args,**kwargs):
        raise AssertionError('Stationary median must avoid expensive pose generation')
    monkeypatch.setattr(cad_pose_search,'hypotheses',forbidden)
    monkeypatch.setattr(unique_anchors,'unique_pairs',forbidden)
    assert not deferred_alignment._periodic_global_offset_possible(
        a,b,.01,1597,free_a=set(range(1482,1597)),
        free_b=set(range(1482,1597)),baseline=1482)



def test_zw3d_same_frame_with_revised_parts_skips_shift_engine(monkeypatch):
    """Changed B-Rep representation or genuinely revised parts must not trigger
    global relocation when diverse stationary native matches cover the frame.
    """
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from dsac29.geometry import describe
    from dsac29.alignment import _relocate
    from dsac29.compare import Record
    a=[];b=[]
    for i in range(60):
        # Sizes form distinct geometric families; different names are irrelevant.
        shape=BRepPrimAPI_MakeBox(20+i,15+i*.12,10+i*.09).Shape()
        part=describe(shape,'REV_A','old')
        pos=np.array([i*53.,(i%7)*37.,(i%5)*25.])
        a.append(_relocate(part,np.eye(3),pos))
        shape_b=(shape if i<40 else
                 BRepPrimAPI_MakeBox(200+i,45+i,15).Shape())
        b.append(_relocate(describe(shape_b,'REV_B','new'),np.eye(3),pos))
    stationary=[Record(i,i,'SAME','independent native proof') for i in range(40)]
    def forbidden(*args,**kwargs):
        raise AssertionError('Do not re-run alignment when independent '
                             'stationary world evidence is already verified')
    monkeypatch.setattr(deferred_alignment,'propose',forbidden)
    assert deferred_alignment._stationary_unique_frame(a,b,stationary,.01)
    assert deferred_alignment.propose_from_stage1(
        a,b,stationary,range(40,60),range(40,60),.01) is None


def test_periodic_repeated_pitched_frame_is_not_skipped_by_unique_gate():
    from dsac29.compare import Record
    a=fake_parts([i*40. for i in range(30)])
    b=fake_parts([i*40.+40. for i in range(30)])
    matches=[Record(i+1,i,'SAME','independent native proof') for i in range(29)]
    assert not deferred_alignment._stationary_unique_frame(a,b,matches,.01)
    assert deferred_alignment._periodic_global_offset_possible(
        a,b,.01,30,free_a={0},free_b={29},baseline=29)


def test_unverified_geometry_never_triggers_stationary_world_skip():
    from dsac29.compare import Record
    a=fake_parts([i*40 for i in range(20)])
    b=fake_parts([i*40 for i in range(20)])
    suspects=[Record(i,i,'UNCERTAIN','native timeout') for i in range(18)]
    assert not deferred_alignment._stationary_unique_frame(a,b,suspects,.01)
