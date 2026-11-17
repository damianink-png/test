import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder,BRepPrimAPI_MakeBox
from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
from dsac29.original_boundary import equivalent

@pytest.mark.parametrize('shape',[lambda:BRepPrimAPI_MakeCylinder(5,10).Shape(),lambda:BRepPrimAPI_MakeBox(10,20,30).Shape()])
def test_analytic_export_matches_nurbs_without_replacing_original_wires(shape):
    a=shape();b=BRepBuilderAPI_NurbsConvert(a,True).Shape()
    assert equivalent(a,b,.01)

def test_different_material_rejected():
    assert not equivalent(BRepPrimAPI_MakeCylinder(5,10).Shape(),BRepPrimAPI_MakeCylinder(5.1,10).Shape(),.01)

def test_failed_topological_conversion_uses_original_boundary(monkeypatch):
    from dsac29 import nurbs_boundary
    a=BRepPrimAPI_MakeCylinder(5,10).Shape();b=BRepBuilderAPI_NurbsConvert(a,True).Shape()
    monkeypatch.setattr(nurbs_boundary,'_convert',lambda s:None)
    assert nurbs_boundary.equivalent(a,b,.01)


def test_local_move_and_changed_hole_are_not_hidden():
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Trsf,gp_Vec,gp_Pnt
    a=BRepPrimAPI_MakeBox(20,20,10).Shape()
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(0,0,1))
    b=BRepBuilderAPI_NurbsConvert(a,True).Shape().Moved(TopLoc_Location(tr))
    assert not equivalent(a,b,.01)
    a=BRepAlgoAPI_Cut(a,BRepPrimAPI_MakeCylinder(2,10).Shape().Moved(TopLoc_Location(tr))).Shape()
    b=BRepAlgoAPI_Cut(BRepPrimAPI_MakeBox(20,20,10).Shape(),BRepPrimAPI_MakeCylinder(3,10).Shape().Moved(TopLoc_Location(tr))).Shape()
    assert not equivalent(a,BRepBuilderAPI_NurbsConvert(b,True).Shape(),.01)


def test_source_brep_is_not_modified(tmp_path):
    from OCP.BRepTools import BRepTools
    a=BRepPrimAPI_MakeCylinder(5,10).Shape();b=BRepBuilderAPI_NurbsConvert(a,True).Shape()
    before=tmp_path/'before.brep';after=tmp_path/'after.brep'
    BRepTools.Write_s(a,str(before));assert equivalent(a,b,.01)
    BRepTools.Write_s(a,str(after));assert before.read_bytes()==after.read_bytes()


def test_nearby_faces_with_reversed_enumeration_match_by_proven_geometry():
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS_Shell,TopoDS_Solid,TopoDS
    from OCP.BRep import BRep_Builder
    from dsac29.parametric_identity import items
    a=BRepPrimAPI_MakeBox(.001,10,20).Shape()
    exported=BRepBuilderAPI_NurbsConvert(a,True).Shape()
    builder=BRep_Builder();shell=TopoDS_Shell();builder.MakeShell(shell)
    for face in reversed(items(exported,TopAbs_FACE,TopoDS.Face_s)):builder.Add(shell,face)
    b=TopoDS_Solid();builder.MakeSolid(b);builder.Add(b,shell)
    assert equivalent(a,b,.01)
