"""Moved STEP instances need full boundary proof, not equal mass descriptors."""
from pathlib import Path
import numpy as np
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Pnt
from dsac29.native_guard import _load_brep,guarded_rigid
from dsac29.geometry import describe,candidate
from dsac29.registered_rigid import prove_native_placement
from dsac29.compare import compare,Record
from dsac29.geometry_registry import GeometryRegistry
from dsac29.revision_rules import classify_revisions
from dsac29.revision_overlap import merge_material_revisions

ROOT=Path(__file__).parent/'fixtures/moved_reexport_insert'
def pair():return [describe(_load_brep(ROOT/(r+'.brep')),'insert','insert-'+r) for r in ('A','B')]

def test_real_reexport_insert_proves_original_boundaries_under_cad_placement():
    a,b=pair()
    assert not candidate(a,b,.01)
    assert abs(a.volume-b.volume)>.02
    ok,rotation,offset=guarded_rigid(a,b,.01,registered_reexport=True)
    assert ok and np.allclose(rotation.T@rotation,np.eye(3),atol=1e-9)
    assert abs(np.linalg.det(rotation)-1)<1e-9
    assert np.linalg.norm(a.center-b.center)>1

def test_registered_assembly_classifies_captured_insert_as_moved_not_material():
    a,b=pair();stable=describe(BRepPrimAPI_MakeBox(20.,20.,20.).Shape(),'base','base')
    old=[stable]*600+[a];new=[stable]*600+[b]
    context=GeometryRegistry()
    records=compare(old,new,.01,revision_only=True,certified_pairs=[(i,i) for i in range(600)],geometry_context=context)
    records=classify_revisions(old,new,records,.01,geometry_context=context,geometry_first=True)
    records,regions,stats=merge_material_revisions(old,new,records,.01,geometry_context=context)
    assert not regions and stats['boolean_checks']==0
    moved=[r for r in records if r.status=='MOVED']
    assert len(moved)==1 and moved[0].a_index==moved[0].b_index==600
    assert not any(r.status in ('ADDED','REMOVED','CHANGED','UNCERTAIN') for r in records)

def test_native_pose_never_hides_a_real_size_change():
    a,b=pair();tr=gp_Trsf();tr.SetScale(gp_Pnt(*map(float,b.center)),1.05)
    changed=describe(BRepBuilderAPI_Transform(b.shape,tr,True).Shape(),'changed','changed')
    assert not prove_native_placement(a,changed,.01)[0]

def test_population_change_keeps_separate_occurrences_without_material_common(monkeypatch):
    a,b=pair()
    assert prove_native_placement(a,b,.01)[0]
    context=GeometryRegistry()
    old=[a];new=[b,b]
    initial=[Record(0,0,'MOVED','original boundaries proven'),Record(None,1,'ADDED','extra occurrence')]
    records=classify_revisions(old,new,initial,.01,geometry_context=context,geometry_first=True)
    assert sum(r.status=='REMOVED' for r in records)==1
    assert sum(r.status=='ADDED' for r in records)==2
    from dsac29 import native_guard
    def forbidden(*args,**kwargs):
        raise AssertionError('Congruent definitions must not enter material Common')
    monkeypatch.setattr(native_guard,'guarded_common',forbidden)
    result,regions,stats=merge_material_revisions(old,new,records,.01,geometry_context=context)
    assert [vars(r) for r in result]==[vars(r) for r in records]
    assert not regions and stats['boolean_checks']==0 and stats['rigid_pairs_excluded']>0

def test_unproved_material_change_still_requires_common(monkeypatch):
    import pytest
    from dsac29 import native_guard
    a=describe(BRepPrimAPI_MakeBox(10.,10.,10.).Shape(),'old','old')
    b=describe(BRepPrimAPI_MakeBox(11.,10.,10.).Shape(),'new','new')
    def failed(*args,**kwargs):
        raise native_guard.NativeGeometryFailure('no material proof')
    monkeypatch.setattr(native_guard,'guarded_common',failed)
    with pytest.raises(native_guard.NativeGeometryFailure,match='no material proof'):
        merge_material_revisions([a],[b],[Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')],.01,geometry_context=GeometryRegistry())
