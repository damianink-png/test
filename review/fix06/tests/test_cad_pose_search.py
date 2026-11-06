"""Independent CAD pose cases: global rotation, outliers, repeats and symmetry."""
from dataclasses import replace
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.compare import Record
from dsac29 import cad_pose_search as search
from dsac29.deferred_alignment import propose,propose_from_stage1


def rotation():
    axis=np.array([1.,2.,3.]);axis/=np.linalg.norm(axis);angle=.63
    x,y,z=axis;k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    return np.eye(3)+np.sin(angle)*k+(1-np.cos(angle))*(k@k)


def case(n=18,repeated=False,rotated=True,noise=False,outliers=0):
    rng=np.random.default_rng(779)
    a=[]
    for i in range(n):
        d=0 if repeated else i
        shape=BRepPrimAPI_MakeBox(10+d,12+d*.3,8+d*.7).Shape()
        p=describe(shape,f'old_{i}','a')
        a.append(_relocate(p,np.eye(3),rng.uniform(-400,400,3)))
    r=rotation() if rotated else np.eye(3);t=np.array([1200.,-730.,441.])
    b=[_relocate(p,r,t) for p in a]
    if noise:
        b=[replace(p,center=p.center+rng.uniform(-.3,.3,3),
                   volume=p.volume*1.01,area=p.area*1.005,
                   eigenvalues=p.eigenvalues*1.02,name=f'new_{i}') for i,p in enumerate(b)]
    for i in range(outliers):
        p=describe(BRepPrimAPI_MakeBox(300+i,200,100).Shape(),'outlier','b')
        b.append(_relocate(p,np.eye(3),rng.uniform(2000,6000,3)))
    b=b[::-1]
    records=[Record(i,None,'REMOVED','') for i in range(len(a))]
    records += [Record(None,j,'ADDED','') for j in range(len(b))]
    return a,b,records,r,t


def test_landmarks_are_rigid_equivariant_and_ignore_integrated_mass_center():
    a,b,_,r,t=case(noise=True)
    aa,bb=search.landmarks(a),search.landmarks(b[::-1])
    assert bb==pytest.approx(aa@r.T+t,abs=1e-7)
    assert not np.allclose(bb,np.asarray([p.center for p in b[::-1]]),atol=.01)


@pytest.mark.parametrize('noise,outliers',[(False,0),(True,0),(True,6)])
def test_native_global_rotation_despite_reexport_drift_and_new_parts(noise,outliers):
    a,b,records,r,t=case(noise=noise,outliers=outliers)
    result=propose(a,b,records,.01)
    assert result and result['status']=='registered',result
    got=np.asarray(result['rotation_B_to_A']);offset=np.asarray(result['translation_B_to_A_mm'])
    assert got@r==pytest.approx(np.eye(3),abs=1e-7)
    assert got@t+offset==pytest.approx(np.zeros(3),abs=1e-6)
    assert result['votes']==len(a)
    assert len(result['certified_pairs'])==len(a)
    assert np.linalg.det(got)==pytest.approx(1.)


def test_repeated_parts_use_spatial_configuration_and_ignore_input_order():
    a,b,records,r,t=case(n=24,repeated=True)
    result=propose(a,b,records,.01)
    assert result and result['status']=='registered',result
    assert result['votes']==24
    assert np.asarray(result['rotation_B_to_A'])@r==pytest.approx(np.eye(3),abs=1e-7)


def test_global_translation_does_not_require_equal_occurrence_counts():
    a,b,records,_,t=case(n=24,rotated=False,noise=True,outliers=8)
    result=propose(a,b,records,.01)
    assert result and result['status']=='registered',result
    assert result['translation_B_to_A_mm']==pytest.approx(-t,abs=1e-7)
    assert result['votes']==24


def test_two_equally_proven_translations_remain_ambiguous():
    a,b,_,_,t=case(n=8,rotated=False)
    b += [_relocate(p,np.eye(3),np.array([3000.,0,0])) for p in b]
    records=[Record(i,None,'REMOVED','') for i in range(len(a))]
    records += [Record(None,j,'ADDED','') for j in range(len(b))]
    result=propose(a,b,records,.01)
    assert result and result['status']=='unresolved',result


def test_descriptor_collision_never_certifies_changed_geometry():
    a,b,records,_,_=case(rotated=False)
    b=[replace(p,shape=_relocate(describe(BRepPrimAPI_MakeBox(2,3,4).Shape(),'different','x'),
                       np.eye(3),p.center).shape) for p in b]
    result=propose(a,b,records,.01)
    assert result is None or result['status']=='unresolved'


def test_registration_never_scales_or_reflects_the_assembly():
    aa=np.array([[0.,0,0],[30,10,2],[4,40,7],[7,12,60]])
    reflected=aa@np.diag([-1.,1,1])
    r,t=search.fit(aa,reflected)
    assert np.linalg.det(r)==pytest.approx(1.)
    assert np.max(np.linalg.norm(aa-(reflected@r.T+t),axis=1))>1
    scaled=aa*1.1
    r,t=search.fit(aa,scaled)
    assert np.linalg.det(r)==pytest.approx(1.)
    assert np.max(np.linalg.norm(aa-(scaled@r.T+t),axis=1))>1


def test_candidate_spread_never_duplicates_coincident_landmarks():
    selected=search.spread(range(30),np.zeros((30,3)),12)
    assert len(selected)==len(set(selected))==12


def test_main_stage_uses_single_coordinator_not_legacy_fallbacks(monkeypatch):
    from dsac29 import alignment,rigid_registration
    monkeypatch.setattr(alignment,'align_assembly',lambda *a,**k:pytest.fail('legacy assembly engine'))
    monkeypatch.setattr(rigid_registration,'propose_verified_rigid',lambda *a,**k:pytest.fail('second independent engine'))
    a,b,_,_,_=case(noise=True)
    result=propose_from_stage1(a,b,[],range(len(a)),range(len(b)),.01)
    assert result['status']=='registered'
    assert result['method']=='cad_global_consensus_trimmed_refinement'


def test_native_timeout_uses_remaining_search_budget(monkeypatch):
    from dsac29.registration_gate import FrameProofCache,frame_support
    from dsac29.geometry_registry import GeometryRegistry
    from dsac29 import native_guard
    from time import monotonic
    a,b,_,_,_=case(n=80,rotated=False)
    b=[_relocate(p,np.eye(3),np.array([-1200.,730.,-441.])) for p in b[::-1]]
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *a:False)
    calls=[]
    def native(*args,**kwargs):calls.append(kwargs['timeout_s']);return True
    monkeypatch.setattr(native_guard,'guarded_world_reexport',native)
    cache=FrameProofCache();cache.deadline=monotonic()+3;cache.pair_timeout=12
    frame_support(a,b,.01,proofs=2,proof_cache=cache)
    assert calls and all(0<t<=3 for t in calls)


def test_original_cad_lookup_survives_mass_centroid_errors_larger_than_search_radius():
    from dsac29.compare import compare
    from dsac29.native_session import world_session
    a,b,records,_,t=case(n=80,rotated=False)
    b=[replace(p,center=p.center+np.array([3.,-2.,4.])) for p in b]
    result=propose(a,b,records,.01)
    assert result and result['status']=='registered'
    assert result['votes']==80
    aligned=[_relocate(p,np.eye(3),np.asarray(result['translation_B_to_A_mm'])) for p in b]
    with world_session(True):
        final=compare(a,aligned,.01,exact_serialization=True,revision_only=True,certified_pairs=result['certified_pairs'])
    assert len(final)==80 and all(r.status=='SAME' for r in final)


def test_strict_signature_warning_does_not_block_native_registration(tmp_path,monkeypatch):
    from dsac29 import cli,similarity_gate
    a,b,_,_,_=case(n=8,noise=True)
    def heuristic(*args,**kwargs):raise similarity_gate.ModelsUnrelated('Strict descriptor mismatch')
    monkeypatch.setattr(similarity_gate,'check_related',heuristic)
    pa=tmp_path/'a.step';pb=tmp_path/'b.step';pa.write_text('old');pb.write_text('new')
    monkeypatch.setattr(cli,'load_step',lambda p,**kw:a if p==pa else b)
    def approval(proposal):
        assert not proposal.get('unrelated'), 'Heuristic warning blocked real CAD search'
        assert proposal.get('status')=='registered'
        return 'align'
    cli.process(pa,pb,tmp_path/'out',step=False,diff_step=False,full_bom=False,
                revision_style=True,auto_align=True,alignment_approval=approval,progress=None)
    import json
    data=json.loads((tmp_path/'out/PODSUMOWANIE.json').read_text())
    assert data['alignment']['applied'] and data['statuses']=={'SAME':8}


@pytest.mark.parametrize('count',[1,12])
def test_single_or_collinear_asymmetric_cad_uses_native_frame_proposals(count):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    notch=BRepAlgoAPI_Cut(BRepPrimAPI_MakeBox(10,20,30).Shape(),
                         BRepPrimAPI_MakeBox(3,5,7).Shape()).Shape()
    one=describe(notch,'notched','notched')
    a=[_relocate(one,np.eye(3),np.array([i*100.,0,0])) for i in range(count)]
    # Rotate about the component-center line so point triples stay collinear.
    angle=.63;r=np.array([[1.,0,0],[0,np.cos(angle),-np.sin(angle)],[0,np.sin(angle),np.cos(angle)]])
    t=np.array([1200.,-300.,200.]);b=[_relocate(p,r,t) for p in a]
    records=[Record(i,None,'REMOVED','') for i in range(count)]
    records += [Record(None,j,'ADDED','') for j in range(count)]
    result=propose(a,b,records,.01)
    assert result and result['status']=='registered',result
    assert np.asarray(result['rotation_B_to_A'])@r==pytest.approx(np.eye(3),abs=1e-6)
    assert result['votes']==count


def test_tiny_angular_change_far_from_origin_is_not_the_same_pose():
    angle=2e-8;r=np.array([[np.cos(angle),-np.sin(angle),0.],[np.sin(angle),np.cos(angle),0.],[0.,0.,1.]])
    assert np.linalg.norm(r-np.eye(3))<1e-7
    assert search.pose_distance(r,np.zeros(3),np.eye(3),np.zeros(3),np.array([[1e8,0.,0.]]))>1.9


@pytest.mark.parametrize('tolerance',[0.,float('nan'),float('inf')])
def test_invalid_tolerance_rejected_before_native_input(tolerance):
    with pytest.raises(ValueError):propose([],[],[],tolerance)


def test_many_false_grid_translations_do_not_starve_rotation_search():
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    shape=BRepAlgoAPI_Cut(BRepPrimAPI_MakeBox(10,20,30).Shape(),BRepPrimAPI_MakeBox(3,5,7).Shape()).Shape()
    one=describe(shape,'same_family','same_family')
    a=[_relocate(one,np.eye(3),np.array([i*100.,j*100.,0.])) for i in range(4) for j in range(4)]
    r=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    b=[_relocate(p,r,np.array([1000.,700.,200.])) for p in a][::-1]
    records=[Record(i,None,'REMOVED','') for i in range(16)]+[Record(None,j,'ADDED','') for j in range(16)]
    result=propose(a,b,records,.01)
    assert result and result['status']=='registered',result
    assert result['votes']==16
    assert np.asarray(result['rotation_B_to_A'])@r==pytest.approx(np.eye(3),abs=1e-6)


def test_permissive_search_gate_cannot_turn_one_small_local_move_into_global_motion():
    from dsac29.deferred_alignment import _periodic_global_offset_possible
    a,b,_,_,t=case(n=40,repeated=True,rotated=False)
    b=[_relocate(p,np.eye(3),-t) for p in b[::-1]]
    b[0]=_relocate(b[0],np.eye(3),np.array([.02,0,0]))
    assert not _periodic_global_offset_possible(a,b,.01,40,free_a={0},free_b={0},baseline=39)
