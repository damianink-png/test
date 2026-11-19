from collections import Counter
from dataclasses import replace
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from dsac29.geometry import describe,transform
from dsac29.compare import compare
from dsac29 import native_guard


def test_rigid_timeout_retains_verified_parts_and_bounds_repeat_attempts(monkeypatch):
    stable=[describe(BRepPrimAPI_MakeBox(1+i*.01,2,3).Shape(),'stable'+str(i),str(i)) for i in range(80)]
    old=list(stable);new=list(stable)
    left=BRepPrimAPI_MakeCylinder(5,10).Shape()
    right=BRepPrimAPI_MakeCylinder(5,10).Shape()
    for i in range(2):
        left=BRepPrimAPI_MakeCylinder(5+i,10).Shape()
        right=BRepPrimAPI_MakeCylinder(5+i,10).Shape()
        old.append(describe(transform(left,np.eye(3),np.array([i*30.,0.,0.])),'unique'+str(i),str(i)))
        part=describe(transform(right,np.eye(3),np.array([1000.+i*30.,0.,0.])),'unique'+str(i),str(i))
        new.append(replace(part,area=part.area+.01))
    moved=BRepPrimAPI_MakeBox(7,8,9).Shape()
    old.append(describe(moved,'moved','moved'))
    new.append(describe(transform(moved,np.eye(3),np.array([500.,0.,0.])),'moved','moved'))
    calls=[]
    def timeout(*args,**kwargs):
        calls.append(1)
        raise native_guard.NativeGeometryFailure('Przekroczono limit odizolowanego testu B-Rep 25 s')
    monkeypatch.setattr(native_guard,'guarded_rigid',timeout)
    result=compare(old,new,revision_only=True)
    assert Counter(r.status for r in result)=={'SAME':80,'MOVED':1,'UNCERTAIN':4}
    assert len(calls)==2
    assert all(r.status!='SAME' for r in result if r.a_index in (80,81))


def test_borderline_registration_extends_nested_sample_without_erasing_failures(monkeypatch):
    from dsac29 import cad_registration,cad_pose_search,unique_anchors,surface_registration
    from dsac29.compare import Record
    from dsac29.registration_search import RegistrationSearch
    old=[];new=[]
    for i in range(100):
        shape=BRepPrimAPI_MakeBox(10+i*.03,12,8).Shape()
        old.append(describe(transform(shape,np.eye(3),np.array([i*35.,(i%7)*80.,0.])),str(i),str(i)))
        new.append(describe(transform(old[-1].shape,np.eye(3),np.array([130.,280.,410.])),str(i),str(i)))
    state=RegistrationSearch();state.bind(old,new,.01)
    state.features=(np.array([p.center for p in old]),np.array([p.center for p in new]))
    pose=cad_pose_search.Pose(np.eye(3),np.array([-130.,-280.,-410.]),
        [(i,i) for i in range(100)],sum(p.volume for p in old),'diagnostic_reproduction')
    monkeypatch.setattr(unique_anchors,'proven_translations',lambda *a,**kw:[])
    monkeypatch.setattr(cad_pose_search,'hypotheses',lambda *a,**kw:[pose])
    monkeypatch.setattr(surface_registration,'propose',lambda *a,**kw:None)
    requests=[];unproven=set(range(20,24))|set(range(38,44))
    def native(a,b,tol,proofs=8,verify_all=False,proof_cache=None,**kw):
        assert not verify_all
        requests.append(proofs)
        ids=[i for i in range(proofs) if i not in unproven]
        for i in ids:proof_cache.results[i,i]=True
        return {'count':100,'checked':proofs,'proofs':len(ids)}
    rows=[Record(i,None,'REMOVED','') for i in range(100)]+[Record(None,i,'ADDED','') for i in range(100)]
    result=cad_registration.propose(old,new,rows,.01,search_state=state,support=native)
    assert requests[:3]==[24,48,64]
    assert max(requests)==64
    assert result['status']=='registered'
    assert result['checked_sample_count']==64
    assert result['verified_sample_count']==54
    assert not result['full_pair_map']
    assert all(i not in unproven for i,j in result['certified_pairs'])
