import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeBox
from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
from OCP.BRepTools import BRepTools
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf,gp_Vec
from dsac29.nurbs_boundary import equivalent
from dsac29.geometry import describe
from dsac29.step_reexport_tolerance import reexport_equivalent_world


def nurbs(s):return BRepBuilderAPI_NurbsConvert(s,True).Shape()


@pytest.mark.parametrize('reverse',[False,True])
def test_analytic_and_nurbs_boundaries_match_without_booleans(monkeypatch,reverse):
    from dsac29 import step_reexport_tolerance
    a=BRepPrimAPI_MakeCylinder(5.,10.).Shape();b=nurbs(a)
    if reverse:a,b=b,a
    assert not reexport_equivalent_world(describe(a,'a','a'),describe(b,'b','b'),.01,allow_boolean=False)
    def forbidden(*args,**kw):raise AssertionError('Must not need Boolean differences')
    monkeypatch.setattr(step_reexport_tolerance,'_verified_difference_empty',forbidden)
    assert equivalent(a,b,.01)


def test_representation_conversion_does_not_hide_movement_or_material_change():
    a=BRepPrimAPI_MakeCylinder(5.,10.).Shape()
    assert not equivalent(a,nurbs(BRepPrimAPI_MakeCylinder(5.1,10.).Shape()),.01)
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(0.,0.,1.))
    assert not equivalent(a,nurbs(a).Moved(TopLoc_Location(tr)),.01)


def test_original_shapes_and_placements_are_unchanged(tmp_path):
    a=BRepPrimAPI_MakeBox(10.,20.,30.).Shape();b=nurbs(a)
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(130.,280.,410.))
    a=a.Moved(TopLoc_Location(tr));b=b.Moved(TopLoc_Location(tr))
    before=tmp_path/'before.brep';after=tmp_path/'after.brep'
    BRepTools.Write_s(a,str(before))
    assert equivalent(a,b,.01)
    BRepTools.Write_s(a,str(after))
    assert before.read_bytes()==after.read_bytes()


def test_isolated_worker_proves_nurbs_pair(monkeypatch):
    from dsac29.native_guard import guarded_registered_world
    from dsac29 import trace_r22
    events=[]
    monkeypatch.setattr(trace_r22,'mark',lambda *args,**kw:events.append(kw))
    a=BRepPrimAPI_MakeCylinder(5.,10.).Shape()
    assert guarded_registered_world(describe(a,'a','a'),describe(nurbs(a),'b','b'),.01)
    assert any(e.get('phase')=='nurbs_boundary_proven' and e.get('match') is True for e in events)


def test_exact_conversion_does_not_apply_additional_repair_tolerance_reduction():
    a=BRepPrimAPI_MakeCylinder(5.,10.).Shape()
    assert equivalent(a,nurbs(BRepPrimAPI_MakeCylinder(5.001,10.).Shape()),.01)
    assert not equivalent(a,nurbs(BRepPrimAPI_MakeCylinder(5.011,10.).Shape()),.01)
