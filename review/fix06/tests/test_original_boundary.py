from math import tau
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


def _rational_cylinder_face(radius, stop):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.Convert import Convert_QuasiAngular
    from OCP.Geom import (Geom_Circle, Geom_RectangularTrimmedSurface,
                          Geom_SurfaceOfLinearExtrusion, Geom_TrimmedCurve)
    from OCP.GeomConvert import GeomConvert
    from OCP.gp import gp_Ax2, gp_Dir

    arc = Geom_TrimmedCurve(Geom_Circle(gp_Ax2(), radius), 0., stop)
    curve = GeomConvert.CurveToBSplineCurve_s(arc, Convert_QuasiAngular)
    surface = Geom_SurfaceOfLinearExtrusion(curve, gp_Dir(0., 0., 1.))
    trim = Geom_RectangularTrimmedSurface(surface, curve.FirstParameter(), curve.LastParameter(), 0., 10.)
    return BRepBuilderAPI_MakeFace(GeomConvert.SurfaceToBSplineSurface_s(trim), 1e-7).Face()


@pytest.mark.parametrize('end', [2.3, tau])
def test_cylindrical_surface_and_trims_match_different_rational_parameters(end):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.Geom import Geom_CylindricalSurface
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Ax3
    from dsac29.cylindrical_boundary import circular_edge_equal
    from dsac29.parametric_identity import prove

    cylinder = Geom_CylindricalSurface(gp_Ax3(), 5.)
    a = BRepBuilderAPI_MakeFace(cylinder, 0., end, 0., 10., 1e-7).Face()

    options = dict(strict_repair=False, surface_prover=surface_equal, edge_prover=circular_edge_equal)
    b = _rational_cylinder_face(5., end)
    assert surface_equal(a, b, .005)
    assert surface_equal(b, a, .005)
    assert prove(a,b,{0:0},[],.01,**options)
    assert not surface_equal(a, TopoDS.Face_s(b.Reversed()), .005)
    assert not surface_equal(a, _rational_cylinder_face(5.03, end), .005)
    changed_trim = _rational_cylinder_face(5., end-.2)
    assert surface_equal(a, changed_trim, .005)
    assert not prove(a,changed_trim,{0:0},[],.01,**options)


def test_closed_solid_cylindrical_reexport_is_proven_at_its_own_location():
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Trsf, gp_Vec
    from dsac29.parametric_identity import items

    source = BRepPrimAPI_MakeCylinder(5., 10.).Shape()
    _, *caps = items(source, TopAbs_FACE, TopoDS.Face_s)
    sewing = BRepBuilderAPI_Sewing(1e-6)
    for face in [_rational_cylinder_face(5., tau), *caps]:
        sewing.Add(face)
    sewing.Perform()
    assert sewing.NbFreeEdges() == 0
    target = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(sewing.SewedShape())).Solid()
    transform = gp_Trsf()
    transform.SetTranslation(gp_Vec(130., 280., 410.))
    location = TopLoc_Location(transform)
    assert equivalent(source.Moved(location), target.Moved(location), .01)
    transform.SetTranslation(gp_Vec(.05, 0., 0.))
    assert not equivalent(source, target.Moved(TopLoc_Location(transform)), .01)

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
    from dsac29 import cylindrical_boundary
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
    monkeypatch.setattr(cylindrical_boundary,'equivalent',lambda *args:False)
    cache=module.SurfaceCache()
    for _ in range(10):assert module.surface_equal(a,b,.01,cache)
    assert len(calls)==2
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(1,2,3))
    assert not module.surface_equal(a,TopoDS.Face_s(b.Moved(TopLoc_Location(tr))),.01,cache)
    assert len(calls)==3
    reversed_face=TopoDS.Face_s(b.Reversed())
    assert not module.surface_equal(a,reversed_face,.01,cache)
    assert len(calls)==4


def _cylindrical_solids():
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from dsac29.parametric_identity import items

    source = BRepBuilderAPI_NurbsConvert(BRepPrimAPI_MakeCylinder(5.,10.).Shape(), True).Shape()
    _, *caps = items(source, TopAbs_FACE, TopoDS.Face_s)
    sewing = BRepBuilderAPI_Sewing(1e-6)
    for face in [_rational_cylinder_face(5., tau), *caps]:
        sewing.Add(face)
    sewing.Perform()
    assert sewing.NbFreeEdges() == 0
    target = BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(sewing.SewedShape())).Solid()
    return source, target


def _cubic_cylinder_export(radius=5., tangent=None):
    """Four polynomial cubic arcs as used to approximate a circular profile."""
    from math import tan, pi
    import numpy as np
    from OCP.Geom import Geom_BSplineCurve
    from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal
    from OCP.TColgp import TColgp_Array1OfPnt
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge,BRepBuilderAPI_MakeWire,BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Pnt,gp_Vec,gp_Pln,gp_Dir

    points = np.array([(1.,0.),(0.,1.),(-1.,0.),(0.,-1.)])
    tangents = np.column_stack((-points[:,1],points[:,0]))
    handle = (4./3*tan(pi/8)) if tangent is None else tangent
    coords = [points[0]]
    for i in range(4):
        j = (i+1)%4
        coords.extend([points[i]+handle*tangents[i],points[j]-handle*tangents[j],points[j]])
    poles = TColgp_Array1OfPnt(1,len(coords))
    for i,(x,y) in enumerate(coords,1):
        poles.SetValue(i,gp_Pnt(x*radius,y*radius,0))
    knots = TColStd_Array1OfReal(1,5)
    mults = TColStd_Array1OfInteger(1,5)
    for i in range(1,6):
        knots.SetValue(i,i-1)
        mults.SetValue(i,4 if i in (1,5) else 3)
    curve = Geom_BSplineCurve(poles,knots,mults,3,False)
    wire = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(curve).Edge()).Wire()
    face = BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(),gp_Dir(0,0,1)),wire,True).Face()
    return BRepBuilderAPI_NurbsConvert(BRepPrimAPI_MakePrism(face,gp_Vec(0,0,10)).Shape(),True).Shape()


def _mixed_cylindrical_solids():
    return BRepPrimAPI_MakeCylinder(5.,10.).Shape(),_cubic_cylinder_export()


def test_cylinder_polynomial_export_requires_radius_and_orientation():
    from OCP.GeomAbs import GeomAbs_Cylinder,GeomAbs_BSplineSurface
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from dsac29.parametric_identity import items
    from dsac29.cylindrical_boundary import equivalent as cylinder_equal
    def side(s,kind):
        return next(f for f in items(s,TopAbs_FACE,TopoDS.Face_s)
                    if BRepAdaptor_Surface(f).GetType()==kind and
                    abs(BRepAdaptor_Surface(f).Value(0,0).Z()-BRepAdaptor_Surface(f).Value(0,1).Z())>.1)
    a,b = _mixed_cylindrical_solids()
    left,right = side(a,GeomAbs_Cylinder),side(b,GeomAbs_BSplineSurface)
    assert cylinder_equal(left,right,.005)
    assert cylinder_equal(right,left,.005)
    assert not cylinder_equal(left,TopoDS.Face_s(right.Reversed()),.005)
    assert not cylinder_equal(left,side(_cubic_cylinder_export(tangent=.63),GeomAbs_BSplineSurface),.005)
    assert not cylinder_equal(left,side(_cubic_cylinder_export(radius=5.02),GeomAbs_BSplineSurface),.005)


def _bicubic_cap(offset):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.Geom import Geom_BSplineSurface
    from OCP.TColgp import TColgp_Array2OfPnt
    from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal
    from OCP.gp import gp_Pnt

    def knot_data(count):
        knots = TColStd_Array1OfReal(1, count)
        mults = TColStd_Array1OfInteger(1, count)
        for i in range(1, count+1):
            knots.SetValue(i, i-1)
            mults.SetValue(i, 4 if i in (1, count) else 1)
        return knots, mults

    uk, um = knot_data(21)
    vk, vm = knot_data(5)
    poles = TColgp_Array2OfPnt(1, 23, 1, 7)
    for i in range(23):
        for j in range(7):
            z = 10. + (offset if (i,j) == (11,3) else 0.)
            poles.SetValue(i+1, j+1, gp_Pnt(i*20./22, j*4./6, z))
    surface = Geom_BSplineSurface(poles, uk, vk, um, vm, 3, 3, False, False)
    return BRepBuilderAPI_MakeFace(surface, 1e-7).Face()


def _bicubic_solid(offset, excess=0.):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from dsac29.parametric_identity import items

    faces = items(BRepPrimAPI_MakeBox(20.,4.,10.).Shape(), TopAbs_FACE, TopoDS.Face_s)
    sewing = BRepBuilderAPI_Sewing(1e-6)
    cap = _bicubic_cap(offset)
    if excess:
        cap = _extended_face(BRepAdaptor_Surface(cap).BSpline(), excess)
    for face in [*faces[:-1], cap]:
        sewing.Add(face)
    sewing.Perform()
    assert sewing.NbFreeEdges() == 0
    return BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(sewing.SewedShape())).Solid()


def test_bicubic_surface_budget_checks_interior_and_orientation():
    from OCP.TopoDS import TopoDS
    from dsac29.nurbs_orientation import native_polynomial_equal

    a, b = _bicubic_cap(0.), _bicubic_cap(.015)
    assert not surface_equal(a, b, .005)
    assert native_polynomial_equal(a, b, .00875)
    assert not native_polynomial_equal(a, TopoDS.Face_s(b.Reversed()), .00875)
    assert not native_polynomial_equal(a, _bicubic_cap(.06), .01)
    assert not equivalent(_bicubic_solid(0.), _bicubic_solid(.06), .01)


def test_bicubic_surface_compares_original_trim_and_world_placement():
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Trsf, gp_Vec
    from dsac29.nurbs_orientation import native_polynomial_equal

    def trimmed(surface, u0, u1, v0=0., v1=4.):
        return BRepBuilderAPI_MakeFace(surface, u0, u1, v0, v1, 1e-7).Face()

    source = BRepAdaptor_Surface(_bicubic_cap(.06)).BSpline()
    face = trimmed(source, 5., 13.)
    other = source.Copy()
    other.ExchangeUV()
    swapped = TopoDS.Face_s(trimmed(other, 0., 4., 5., 13.).Reversed())
    assert native_polynomial_equal(face, swapped, .00875)
    assert not native_polynomial_equal(face, trimmed(source, 5., 14.), .00875)
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(.02, 0., 0.))
    shifted = TopoDS.Face_s(swapped.Moved(TopLoc_Location(trsf)))
    assert not native_polynomial_equal(face, shifted, .00875)


def _reported_cap(old, offset=0.):
    """Recorded UV ranges/orientations; synthetic knots and control points."""
    import numpy as np
    from OCP.Geom import Geom_BSplineSurface
    from OCP.TColStd import TColStd_Array1OfInteger, TColStd_Array1OfReal
    from OCP.TColgp import TColgp_Array2OfPnt
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt

    bounds = ((-.00018445272065421535,2.339643364298939,-.0063301236956363575,1.6001413635270016)
              if old else (-.00018235991749899097,2.3396433642989387,-.023357329638431637,1.5830458494965853))
    first_span = .00018445272065421535/.0270682
    def axis(knots):
        k = TColStd_Array1OfReal(1,len(knots))
        m = TColStd_Array1OfInteger(1,len(knots))
        for i,value in enumerate(knots,1):
            k.SetValue(i,value)
            m.SetValue(i,4 if i in (1,len(knots)) else 1)
        flat = np.r_[[knots[0]]*3,knots,[knots[-1]]*3]
        triples = [flat[i+1:i+4] for i in range(len(flat)-4)]
        return k,m,triples

    uk,um,us = axis(np.r_[0.,np.linspace(first_span,2.378167391356,20)])
    vk,vm,vs = axis(np.linspace(-.09956341465096,1.676343957654,5))
    poles = TColgp_Array2OfPnt(1,len(us),1,len(vs))
    for i,u in enumerate(us):
        x = 20.*(np.mean(u)-bounds[0])/(bounds[1]-bounds[0])
        for j,v in enumerate(vs):
            v = (v-bounds[2])/(bounds[3]-bounds[2])
            y = 4.*np.mean(v)
            # Blossom of 4*v*(1-v) leaves the actual trim edges in z=0.
            arch = 4.*(np.mean(v)-(v[0]*v[1]+v[1]*v[2]+v[0]*v[2])/3.)
            z = offset*arch if i==11 else 0.
            poles.SetValue(i+1,j+1,gp_Pnt(x,y if old else 4.-y,z))
    face = _rectangular_pcurves(Geom_BSplineSurface(poles,uk,vk,um,vm,3,3,False,False),bounds)
    return TopoDS.Face_s(face.Reversed()) if old else face


def _reported_solids():
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from dsac29.parametric_identity import items

    box = BRepPrimAPI_MakeBox(20.,4.,10.).Shape()
    faces = items(box,TopAbs_FACE,TopoDS.Face_s)
    solids = []
    for cap in (_reported_cap(True,.35),_reported_cap(False,.35)):
        sewing = BRepBuilderAPI_Sewing(1e-6)
        for face in [*faces[:4],cap,faces[-1]]:
            sewing.Add(face)
        sewing.Perform()
        assert sewing.NbFreeEdges() == 0
        solids.append(BRepBuilderAPI_MakeSolid(TopoDS.Shell_s(sewing.SewedShape())).Solid())
    return solids


def test_reported_sixth_face_checks_reflected_trim_rectangles():
    from OCP.TopoDS import TopoDS
    from dsac29.nurbs_orientation import native_polynomial_equal
    a,b = _reported_cap(True),_reported_cap(False,.012)
    for left,right in ((a,b),(b,a)):
        details = {}
        assert native_polynomial_equal(left,right,.00875,details)
        assert details['max_overhang_spans'] == pytest.approx(.0270682)
        assert 0. < details['certified'] <= .00875
    assert not native_polynomial_equal(a,TopoDS.Face_s(b.Reversed()),.00875)
    assert not native_polynomial_equal(a,_reported_cap(False,.09),.00875)


def _torus_exports():
    from OCP.BRep import BRep_Builder
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeSolid
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeTorus
    from OCP.Convert import Convert_QuasiAngular
    from OCP.Geom import Geom_Circle, Geom_SurfaceOfRevolution
    from OCP.GeomConvert import GeomConvert
    from OCP.TopoDS import TopoDS_Shell
    from OCP.gp import gp_Ax1, gp_Ax2, gp_Pnt, gp_Dir

    axes = gp_Ax2(gp_Pnt(10,0,0),gp_Dir(0,-1,0),gp_Dir(1,0,0))
    meridian = GeomConvert.CurveToBSplineCurve_s(Geom_Circle(axes,2.),Convert_QuasiAngular)
    surface = Geom_SurfaceOfRevolution(meridian,gp_Ax1(gp_Pnt(),gp_Dir(0,0,1)))
    spline = GeomConvert.SurfaceToBSplineSurface_s(surface)
    builder, shell = BRep_Builder(), TopoDS_Shell()
    builder.MakeShell(shell)
    builder.Add(shell,BRepBuilderAPI_MakeFace(spline,1e-7).Face())
    return BRepPrimAPI_MakeTorus(10.,2.).Shape(),BRepBuilderAPI_MakeSolid(shell).Solid()


def test_torus_spline_certifies_complete_surface_and_respects_cuts():
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeTorus
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Vec
    from dsac29.parametric_identity import items,prove
    from dsac29.cylindrical_boundary import equivalent as carrier_equal,circular_edge_equal
    def face(shape):
        return items(shape,TopAbs_FACE,TopoDS.Face_s)[0]
    a,b = map(face,_torus_exports())
    d = {}
    assert carrier_equal(a,b,.005,d) and d['reason']=='torus_surface_proven'
    assert carrier_equal(b,a,.005)
    assert not carrier_equal(a,TopoDS.Face_s(b.Reversed()),.005)
    assert not carrier_equal(face(BRepPrimAPI_MakeTorus(10.03,2.).Shape()),b,.005)
    assert not carrier_equal(face(BRepPrimAPI_MakeTorus(10.,2.03).Shape()),b,.005)
    spline=BRepAdaptor_Surface(b).BSpline()
    trimmed=BRepBuilderAPI_MakeFace(spline,0.,1.5,0.,2.,1e-7).Face()
    assert carrier_equal(a,trimmed,.005)
    assert not prove(a,trimmed,{0:0},[],.01,strict_repair=False,
                     surface_prover=carrier_equal,edge_prover=circular_edge_equal)
    spline.SetPole(3,3,spline.Pole(3,3).Translated(gp_Vec(.3,.3,.3)))
    assert not carrier_equal(a,BRepBuilderAPI_MakeFace(spline,1e-7).Face(),.005)


@pytest.mark.parametrize('solids', [_cylindrical_solids, lambda: (_bicubic_solid(0.), _bicubic_solid(.015)),
                                     lambda: (_bicubic_solid(0.), _bicubic_solid(.015, 1e-9)), _reported_solids,_mixed_cylindrical_solids,_torus_exports],
                         ids=['rational-cylinder', 'polynomial-23x7','pcurve-outside-knots','reported-reflected-overhang','analytic-vs-cubic-cylinder','analytic-vs-spline-torus'])
def test_different_spline_exports_keep_the_53_stationary_occurrences(solids):
    from collections import Counter
    import numpy as np
    from dsac29.compare import compare
    from dsac29.geometry import describe
    from dsac29.alignment import _relocate

    source, target = solids()
    assert equivalent(source, target, .01)

    def occurrences(shape, name, positions):
        part = describe(shape, name, name)
        return [_relocate(part, np.eye(3), np.array([130.+i*30.,280.,410.])) for i in positions]

    old = occurrences(source, '04156745', range(75))
    new = occurrences(target, 'C04156745', [*range(53), *range(100,156)])
    from dsac29.revision_rules import classify_revisions
    rows = compare(old, new, revision_only=True, registered_frame=True)
    rows = classify_revisions(old, new, rows, geometry_first=True)
    assert Counter(row.status for row in rows) == {'SAME':53,'REMOVED':22,'ADDED':56}
    assert {(row.a_index,row.b_index) for row in rows if row.status=='SAME'} == {(i,i) for i in range(53)}


def _extended_face(support, excess):
    return _rectangular_pcurves(support,(-excess,20.,0.,4.))


def _rectangular_pcurves(support, bounds):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
    from OCP.BRepLib import BRepLib
    from OCP.GCE2d import GCE2d_MakeSegment
    from OCP.gp import gp_Pnt2d

    u0,u1,v0,v1 = bounds
    corners = [(u0,v0),(u1,v0),(u1,v1),(u0,v1)]
    wire = BRepBuilderAPI_MakeWire()
    for i, point in enumerate(corners):
        line = GCE2d_MakeSegment(gp_Pnt2d(*corners[i-1]),gp_Pnt2d(*point)).Value()
        wire.Add(BRepBuilderAPI_MakeEdge(line,support).Edge())
    face = BRepBuilderAPI_MakeFace(support,wire.Wire(),True).Face()
    BRepLib.BuildCurves3d_s(face)
    return face


def test_exported_pcurves_outside_native_knots_consume_world_distance_budget():
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from dsac29.nurbs_orientation import native_polynomial_equal

    cap = _bicubic_cap(0.)
    support = BRepAdaptor_Surface(cap).BSpline()
    details = {}
    assert native_polynomial_equal(cap, _extended_face(support, 1e-7), .00875, details)
    assert details['max_overhang_spans'] == pytest.approx(1e-7)
    assert 0. < details['certified'] <= .00875
    assert not native_polynomial_equal(cap, _extended_face(support, .005), .00875)
    details = {}
    assert not native_polynomial_equal(cap, _extended_face(support, .05), .00875, details)
    assert details['corner_gap_mm'] > .00875


def test_disk_with_a_new_seam_needs_its_full_oriented_circle():
    from math import cos, sin
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
    from OCP.Geom import Geom_Circle
    from OCP.GeomConvert import GeomConvert
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Ax2, gp_Pln, gp_Pnt, gp_Dir
    from dsac29.cylindrical_boundary import circular_edge_equal
    from dsac29.parametric_identity import prove

    def edge(angle, radius, spline):
        axes = gp_Ax2(gp_Pnt(),gp_Dir(0,0,1),gp_Dir(cos(angle),sin(angle),0))
        circle = Geom_Circle(axes,radius)
        return BRepBuilderAPI_MakeEdge(GeomConvert.CurveToBSplineCurve_s(circle) if spline else circle).Edge()

    def disk(trim):
        return BRepBuilderAPI_MakeFace(gp_Pln(gp_Pnt(),gp_Dir(0,0,1)), BRepBuilderAPI_MakeWire(trim).Wire(),True).Face()

    for spline in (True,False):
        a, b = edge(0.,5.,spline),edge(1.2,5.,True)
        assert circular_edge_equal(a,b,.005)
        assert prove(disk(a),disk(b),{0:0},[],.01,strict_repair=False,
                     surface_prover=surface_equal,edge_prover=circular_edge_equal)
        assert not circular_edge_equal(a,TopoDS.Edge_s(b.Reversed()),.005)
        assert not circular_edge_equal(a,edge(1.2,5.03,True),.005)


def test_cylinder_checks_the_terminal_span_outside_the_support():
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCP.Geom import Geom_CylindricalSurface
    from OCP.gp import gp_Ax3
    from dsac29.cylindrical_boundary import equivalent as cylinder_equal

    cylinder = Geom_CylindricalSurface(gp_Ax3(),5.)
    reference = BRepBuilderAPI_MakeFace(cylinder,0.,2.3,-.15,10.,1e-7).Face()
    spline = BRepAdaptor_Surface(_rational_cylinder_face(5.,2.3)).BSpline()
    u0,u1,_,_ = spline.Bounds()
    overhang = _rectangular_pcurves(spline,(u0,u1,-.15,10.))
    assert cylinder_equal(reference,overhang,.005)
    # Keep the support inside tolerance but let its sloped terminal patch
    # continue beyond it. Clamping V to the last knot would hide the change.
    for u in range(1,spline.NbUPoles()+1):
        point = spline.Pole(u,spline.NbVPoles())
        point.SetX(point.X()*1.0005)
        point.SetY(point.Y()*1.0005)
        spline.SetPole(u,spline.NbVPoles(),point)
    inside = _rectangular_pcurves(spline,(u0,u1,0.,10.))
    beyond = _rectangular_pcurves(spline,(u0,u1,0.,30.))
    assert cylinder_equal(reference,inside,.005)
    info = {}
    assert not cylinder_equal(reference,beyond,.005,info)
    assert info['reason']=='radial_bound'
    assert info['probe_radial_error_mm'] > .005
