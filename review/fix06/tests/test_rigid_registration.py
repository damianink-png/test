"""Rigid CAD alignment regression: rotations, revisions, symmetry, and native proof."""
import numpy as np
from types import SimpleNamespace
import pytest
from dsac29 import rigid_registration as rigid


def _sample(n=36):
    rng=np.random.default_rng(12345)
    return [SimpleNamespace(center=rng.uniform(-300,300,3),
                            volume=float(1000+i*131),area=0.0) for i in range(n)]


def _rot():
    return np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])


def test_ransac_kabsch_recovers_rotation_and_translation_from_revised_parts():
    old=_sample(50)
    rot=_rot()
    offset=np.array([720.,-1300.,240.])
    new=[SimpleNamespace(center=rot@p.center+offset,volume=p.volume,area=0.)
         for p in old[:35]]
    new.extend(SimpleNamespace(center=np.array([2000.+i*7,1000.+i*13,800.]),
                               volume=35000.+i*101,area=0.)
               for i in range(9))
    result=rigid.propose_rigid_hypotheses(old,new,.01)
    assert result and result[0].support>=35
    got=np.asarray(result[0].rotation)
    shift=np.asarray(result[0].translation)
    assert np.linalg.det(got)==pytest.approx(1.,abs=1e-10)
    assert got@rot==pytest.approx(np.eye(3),abs=1e-8)
    assert got@offset+shift==pytest.approx(np.zeros(3),abs=1e-7)


def test_ransac_finds_pose_with_repeated_definitions():
    old=_sample(48)
    for i,p in enumerate(old):p.volume=float(2000+(i%6)*137)
    rot=_rot()
    offset=np.array([300.,-900.,220.])
    new=[SimpleNamespace(center=rot@p.center+offset,volume=p.volume,area=0.)
         for p in old]
    result=rigid.propose_rigid_hypotheses(old,new,.01)
    assert result and result[0].support==48
    assert np.linalg.det(np.asarray(result[0].rotation))>0.9999


def test_reflected_nonplanar_assembly_does_not_get_positive_full_consensus():
    old=_sample(26)
    reflect=np.diag([-1.,1.,1.])
    new=[SimpleNamespace(center=reflect@p.center+np.array([300.,20.,-50.]),
                         volume=p.volume,area=0.) for p in old]
    result=rigid.propose_rigid_hypotheses(old,new,.01)
    assert not result or max(h.support for h in result)<len(old)


def test_collinear_anchors_are_not_sufficient_for_rotation():
    old=[SimpleNamespace(center=np.array([float(i)*25,0.,0.]),
                         volume=1000.+i*100,area=0.) for i in range(16)]
    new=[SimpleNamespace(center=p.center+np.array([500.,60.,30.]),
                         volume=p.volume,area=0.) for p in old]
    assert rigid.propose_rigid_hypotheses(old,new,.01)==[]
    assert not rigid._independent_anchors([(0,0),(1,1),(2,2)],old,.01)


def test_native_gate_rejects_point_votes_without_brep_proof(monkeypatch):
    from dsac29 import alignment, registration_gate
    old=_sample(14)
    new=_sample(14)
    identity=tuple(tuple(float(v) for v in row) for row in np.eye(3))
    proposal=rigid.Pose(identity,(100.,200.,300.),14,14,10000.)
    monkeypatch.setattr(rigid,'propose_rigid_hypotheses',
                        lambda *args,**kwargs:[proposal])
    monkeypatch.setattr(alignment,'_relocate',lambda p,*args:p)
    monkeypatch.setattr(registration_gate,'frame_support',
                        lambda *args,**kwargs:{'count':14,'checked':14,'proofs':0})
    result=rigid.propose_verified_rigid(old,new,0,.01)
    assert result['status']=='unresolved'


def test_native_brep_confirms_rotated_noncollinear_boxes():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt
    from dsac29.geometry import describe
    from dsac29.alignment import _relocate
    a=[]
    for i in range(12):
        p=BRepPrimAPI_MakeBox(gp_Pnt(float(i*47),float((i*i)%7*29),
                                     float(i%4*21)),10.+i,12.,8.).Shape()
        a.append(describe(p,f'item{i}',f'old/{i}'))
    rot=_rot()
    offset=np.array([1000.,-300.,200.])
    b=[_relocate(p,rot,offset) for p in a]
    result=rigid.propose_verified_rigid(a,b,0,.01)
    assert result and result['status']=='registered'
    assert result['verification_scope']=='full_brep'
    assert np.allclose(np.asarray(result['rotation_B_to_A']),rot.T,atol=1e-6)
    assert result['verified_sample_count']>=8
    assert len(result['certified_pairs'])>=8



def test_unchanged_repeated_parts_do_not_trigger_expensive_global_pose(monkeypatch):
    """Swerve regression: 92/251 existing B-Rep matches vs 101 centroid votes.

    This is not proof of a displaced assembly and must not launch Common/Cut.
    """
    from dsac29 import alignment,registration_gate
    old=_sample(251)
    new=_sample(251)
    identity=tuple(tuple(float(v) for v in row) for row in np.eye(3))
    pose=rigid.Pose(identity,(0.0,0.0,5.0),101,20,15000.)
    monkeypatch.setattr(rigid,'propose_rigid_hypotheses',
                        lambda *args,**kwargs:[pose])
    monkeypatch.setattr(alignment,'_relocate',
                        lambda *args,**kwargs: (_ for _ in ()).throw(
                            AssertionError('do not relocate for marginal votes')))
    monkeypatch.setattr(registration_gate,'frame_support',
                        lambda *args,**kwargs: (_ for _ in ()).throw(
                            AssertionError('do not B-Rep verify marginal pose')))
    assert rigid.propose_verified_rigid(old,new,92,.01) is None


def test_fully_checked_nonimproving_brep_pose_is_not_retried(monkeypatch):
    """A predicted win with no new actual CAD proof is rejected immediately."""
    from dsac29 import alignment,registration_gate
    old=_sample(251)
    new=_sample(251)
    identity=tuple(tuple(float(v) for v in row) for row in np.eye(3))
    pose=rigid.Pose(identity,(0.0,0.0,500.0),150,22,15000.)
    monkeypatch.setattr(rigid,'propose_rigid_hypotheses',
                        lambda *args,**kwargs:[pose])
    monkeypatch.setattr(alignment,'_relocate',lambda part,*args:part)
    calls=[]
    def support(*args,**kwargs):
        calls.append(kwargs)
        assert len(calls)==1, 'never retry a disproven frame'
        return {'count':120,'checked':120,'proofs':60}
    monkeypatch.setattr(registration_gate,'frame_support',support)
    assert rigid.propose_verified_rigid(old,new,60,.01)['status']=='unresolved'
    assert len(calls)==1


def test_large_clear_shift_still_enters_native_proof(monkeypatch):
    """Do not lose strong global translations when filtering weak hypotheses."""
    from dsac29 import alignment,registration_gate
    old=_sample(100)
    new=_sample(100)
    identity=tuple(tuple(float(v) for v in row) for row in np.eye(3))
    pose=rigid.Pose(identity,(250.,120.,-45.),91,41,50000.)
    monkeypatch.setattr(rigid,'propose_rigid_hypotheses',
                        lambda *args,**kwargs:[pose])
    monkeypatch.setattr(alignment,'_relocate',lambda part,*args:part)
    calls=[]
    def support(*args,**kwargs):
        calls.append(kwargs)
        return {'count':91,'checked':10,'proofs':0}
    monkeypatch.setattr(registration_gate,'frame_support',support)
    assert rigid.propose_verified_rigid(old,new,5,.01)['status']=='unresolved'
    assert len(calls)==1
