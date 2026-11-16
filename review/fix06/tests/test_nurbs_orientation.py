import pytest
from OCP.gp import gp_Pnt
from OCP.TColgp import TColgp_Array2OfPnt
from OCP.Geom import Geom_BezierSurface
from OCP.GeomConvert import GeomConvert
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.TopoDS import TopoDS
from dsac29.nurbs_orientation import oriented_surface_equal


def surfaces():
    poles=TColgp_Array2OfPnt(1,3,1,2)
    for i in range(1,4):
        for j in range(1,3):poles.SetValue(i,j,gp_Pnt(i*3.,j*5.,(i==2)*.3))
    a=GeomConvert.SurfaceToBSplineSurface_s(Geom_BezierSurface(poles))
    return a,a.Copy()


@pytest.mark.parametrize('swap',[False,True])
@pytest.mark.parametrize('u,v',[(False,False),(True,False),(False,True),(True,True)])
def test_uv_reversal_requires_compensating_face_orientation(u,v,swap):
    a,b=surfaces()
    if swap:b.ExchangeUV()
    if u:b.UReverse()
    if v:b.VReverse()
    left=BRepBuilderAPI_MakeFace(a,1e-7).Face()
    right=BRepBuilderAPI_MakeFace(b,1e-7).Face()
    if swap^u^v:right=TopoDS.Face_s(right.Reversed())
    assert oriented_surface_equal(left,right,.001)
    assert not oriented_surface_equal(left,TopoDS.Face_s(right.Reversed()),.001)


def test_full_boundary_proof_retains_trimming_check():
    from dsac29.parametric_identity import prove
    from dsac29.step_reexport_tolerance import _faces
    from types import SimpleNamespace
    a,b=surfaces();b.UReverse()
    left=BRepBuilderAPI_MakeFace(a,1e-7).Face()
    right=TopoDS.Face_s(BRepBuilderAPI_MakeFace(b,1e-7).Face().Reversed())
    assert prove(left,right,{0:0},_faces(SimpleNamespace(shape=left)),.01,
                 strict_repair=False,allow_parametric_orientation=True)
    shorter=TopoDS.Face_s(BRepBuilderAPI_MakeFace(b,0.,.5,0.,1.,1e-7).Face().Reversed())
    assert not prove(left,shorter,{0:0},_faces(SimpleNamespace(shape=left)),.01,
                     strict_repair=False,allow_parametric_orientation=True)


def test_matching_corners_do_not_hide_changed_surface_interior():
    a,b=surfaces()
    b.SetPole(2,1,gp_Pnt(6.,5.,2.))
    left=BRepBuilderAPI_MakeFace(a,1e-7).Face()
    right=BRepBuilderAPI_MakeFace(b,1e-7).Face()
    assert not oriented_surface_equal(left,right,.001)


def test_isolated_worker_accepts_all_forward_export_without_boolean(monkeypatch):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.BRepBuilderAPI import (BRepBuilderAPI_NurbsConvert, BRepBuilderAPI_Sewing,
                                    BRepBuilderAPI_MakeSolid)
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from dsac29.brep_safety import is_valid
    from dsac29.native_guard import guarded_registered_world
    from dsac29.geometry import describe
    from dsac29 import trace_r22
    original=BRepPrimAPI_MakeBox(10.,20.,30.).Shape()
    converted=BRepBuilderAPI_NurbsConvert(original,True).Shape()
    sewing=BRepBuilderAPI_Sewing(1e-7)
    ex=TopExp_Explorer(converted,TopAbs_FACE)
    while ex.More():
        face=TopoDS.Face_s(ex.Current())
        surface=BRepAdaptor_Surface(face).BSpline().Copy()
        if int(face.Orientation())==1:surface.UReverse()
        sewing.Add(BRepBuilderAPI_MakeFace(surface,1e-7).Face())
        ex.Next()
    sewing.Perform()
    exported=BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(sewing.SewedShape())).Solid()
    assert is_valid(exported)
    ex=TopExp_Explorer(exported,TopAbs_FACE)
    while ex.More():
        assert int(ex.Current().Orientation())==0
        ex.Next()
    events=[]
    monkeypatch.setattr(trace_r22,'mark',lambda *args,**kw:events.append(kw))
    assert guarded_registered_world(describe(original,'old','old'),describe(exported,'new','new'),.01)
    assert any(e.get('phase')=='nurbs_boundary_proven' and e.get('match') is True for e in events)
    events.clear()
    assert guarded_registered_world(describe(converted,'old','old'),describe(exported,'new','new'),.01)
    assert any(e.get('phase')=='nurbs_boundary_proven' and e.get('match') is True for e in events)
