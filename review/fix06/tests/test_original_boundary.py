import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder,BRepPrimAPI_MakeBox
from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
from dsac29.original_boundary import equivalent, surface_equal


def _planar_face(angle, *, width=12., height=8., offset=0.):
    from math import cos, sin
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
    from OCP.gp import gp_Ax3, gp_Dir, gp_Pln, gp_Pnt
    polygon = BRepBuilderAPI_MakePolygon()
    for x, y in ((0., 0.), (width, 0.), (width, height), (0., height)):
        polygon.Add(gp_Pnt(x, y, offset))
    polygon.Close()
    axis = gp_Ax3(gp_Pnt(0., 0., offset), gp_Dir(0., 0., 1.), gp_Dir(cos(angle), sin(angle), 0.))
    return BRepBuilderAPI_MakeFace(gp_Pln(axis), polygon.Wire(), True).Face()


@pytest.mark.parametrize('convert', [False, True])
def test_planar_surface_matches_rotated_uv_and_checks_original_trims(convert):
    from math import pi
    from OCP.TopoDS import TopoDS
    from dsac29.parametric_identity import prove

    def export(face):
        if not convert:
            return face
        return TopoDS.Face_s(BRepBuilderAPI_NurbsConvert(face, True).Shape())

    a = _planar_face(0.)
    b = export(_planar_face(pi/4))
    assert surface_equal(a, b, .005)
    assert surface_equal(b, a, .005)
    options = dict(strict_repair=False, surface_prover=surface_equal)
    assert prove(a, b, {0: 0}, [], .01, **options)
    assert not surface_equal(a, TopoDS.Face_s(b.Reversed()), .005)
    assert not surface_equal(a, export(_planar_face(pi/4, offset=.02)), .005)
    changed_trim = export(_planar_face(pi/4, width=11.))
    assert surface_equal(a, changed_trim, .005)
    assert not prove(a, changed_trim, {0: 0}, [], .01, **options)


def test_whole_solid_with_rotated_uv_and_trim_diagnostics():
    from math import pi
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Trsf, gp_Vec

    a, b = (BRepPrimAPI_MakePrism(_planar_face(angle), gp_Vec(0., 0., 10.)).Shape()
            for angle in (0., pi/4))
    b = BRepBuilderAPI_NurbsConvert(b, True).Shape()
    transform = gp_Trsf()
    transform.SetTranslation(gp_Vec(130., 280., 410.))
    location = TopLoc_Location(transform)
    assert equivalent(a.Moved(location), b.Moved(location), .01)
    assert not equivalent(a, b.Moved(location), .01)

    stages = []
    changed = BRepPrimAPI_MakeBox(12.02, 8., 10.).Shape()
    assert not equivalent(a, changed, .01, stages.append)
    assert any(stage.startswith('original_boundary_candidate_rejected_trims ') for stage in stages)

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


def test_surface_conversion_reused_without_reusing_movement_verdict(monkeypatch):
    from dsac29 import original_boundary as module
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Trsf,gp_Vec
    from OCP.TopLoc import TopLoc_Location
    from dsac29.parametric_identity import items
    shape=BRepPrimAPI_MakeCylinder(5,10).Shape()
    originals=items(shape,TopAbs_FACE,TopoDS.Face_s)
    export_by_face=items(BRepBuilderAPI_NurbsConvert(shape,True).Shape(),TopAbs_FACE,TopoDS.Face_s)
    index=next(i for i,face in enumerate(originals) if BRepAdaptor_Surface(face).GetType()==GeomAbs_Cylinder)
    a,b=originals[index],export_by_face[index]
    native=module._surface_face;calls=[]
    def counted(face):calls.append(face);return native(face)
    monkeypatch.setattr(module,'_surface_face',counted)
    cache=module.SurfaceCache()
    for _ in range(10):assert module.surface_equal(a,b,.01,cache)
    assert len(calls)==2
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(1,2,3))
    assert not module.surface_equal(a,TopoDS.Face_s(b.Moved(TopLoc_Location(tr))),.01,cache)
    assert len(calls)==3
    reversed_face=TopoDS.Face_s(b.Reversed())
    assert not module.surface_equal(a,reversed_face,.01,cache)
    assert len(calls)==4
