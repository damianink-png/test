"""Real run 41059887556: fractional STEP shift, collapsed strips and mass drift."""
from pathlib import Path
from types import SimpleNamespace
import json
import numpy as np
import pytest
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf,gp_Pnt,gp_Vec
from dsac29 import parametric_identity as proof
from dsac29.native_guard import _load_brep,guarded_world_reexport,NativeGeometryFailure
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.step_reexport_tolerance import reexport_equivalent_world,world_candidate

ROOT=Path(__file__).parent/'fixtures'

def pair(name):
    return [_load_brep(ROOT/name/(r+'.brep')) for r in ('A','B')]

@pytest.mark.parametrize('index',[29,59,60])
def test_full_micro_cylinder_patch_and_both_edges_are_bounded(index):
    a,b=[proof.items(s,TopAbs_FACE,TopoDS.Face_s)[index] for s in pair('collapsed_cylinders')]
    assert proof.collapsed_cylinder_equal(a,b,.01)
    assert not proof.collapsed_cylinder_equal(a,b,.005)
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(0.,.02,0.))
    moved=TopoDS.Face_s(BRepBuilderAPI_Transform(b,tr,True).Shape())
    assert not proof.collapsed_cylinder_equal(a,moved,.01)
    tr=gp_Trsf();tr.SetScale(gp_Pnt(0,0,0),3.)
    large=[TopoDS.Face_s(BRepBuilderAPI_Transform(f,tr,True).Shape()) for f in (a,b)]
    assert not proof.collapsed_cylinder_equal(*large,.01)

def test_captured_full_solid_requires_every_other_surface_and_trim(monkeypatch):
    a,b=[describe(s,r,r) for r,s in zip(('A','B'),pair('collapsed_cylinders'))]
    assert reexport_equivalent_world(a,b,.01,allow_boolean=False,_original_boundary_only=True)
    assert not reexport_equivalent_world(a,b,.01,allow_boolean=False,_repair_boundary_only=True)
    monkeypatch.setattr(proof,'surface_equal',lambda *args:False)
    assert not reexport_equivalent_world(a,b,.01,allow_boolean=False,_original_boundary_only=True)

def test_fractional_shift_capture_runs_through_the_actual_isolated_worker():
    a,b=[describe(s,r,r) for r,s in zip(('A','B'),pair('collapsed_cylinders'))]
    assert guarded_world_reexport(a,b,.01,timeout_s=25)
    with pytest.raises(NativeGeometryFailure):
        guarded_world_reexport(a,_relocate(b,np.eye(3),np.array([.02,0.,0.])),.01,timeout_s=25)

def test_mass_profile_drift_is_only_a_candidate_not_a_geometric_verdict(monkeypatch):
    profile=json.loads((ROOT/'volume_reexport/PROVENANCE.json').read_text())['full_inputs']
    a,b=[SimpleNamespace(shape=s,volume=profile[r]['volume'],area=profile[r]['area'])
         for r,s in zip(('A','B'),pair('volume_reexport'))]
    assert abs(a.volume-b.volume)/a.volume>.02
    assert world_candidate(a,b,.01)
    assert reexport_equivalent_world(a,b,.01,allow_boolean=False)
    monkeypatch.setattr(proof,'prove',lambda *args,**kwargs:False)
    assert not reexport_equivalent_world(a,b,.01,allow_boolean=False)

def test_real_dimensional_change_is_not_accepted_despite_permissive_mass_filter():
    a=describe(BRepPrimAPI_MakeBox(10.,10.,10.).Shape(),'A','A')
    b=describe(BRepPrimAPI_MakeBox(10.05,10.,10.).Shape(),'B','B')
    assert world_candidate(a,b,.01)
    assert not reexport_equivalent_world(a,b,.01,allow_boolean=False)
