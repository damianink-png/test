import numpy as np
from dsac29.bernstein_partition import curves_equal,surfaces_equal

def test_rational_curve_subdivision_and_changed_middle():
    p=np.array([[0.,0,0],[4,8,1],[10,0,0]]);w=np.array([1.,.7,1.]);h=np.c_[p*w[:,None],w]
    t=.3;mid=(1-t)*h[:-1]+t*h[1:];tip=(1-t)*mid[0]+t*mid[1]
    a=np.array([h[0],mid[0],tip]);b=np.array([tip,mid[1],h[2]])
    pieces=[(x[:,:3]/x[:,3,None],x[:,3]) for x in (a,b)]
    assert curves_equal(('bezier',[(p,w)],[0.,1.]),('bezier',pieces,[0.,t,1.]),1e-6)
    pieces[1][0][1,2]+=.1
    assert not curves_equal(('bezier',[(p,w)],[0.,1.]),('bezier',pieces,[0.,t,1.]),.001)

def test_surface_refinement_degree_uv_scale_and_orientation():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.TColStd import TColStd_Array1OfReal
    shape=BRepBuilderAPI_NurbsConvert(BRepPrimAPI_MakeBox(10,20,30).Shape(),True).Shape()
    face=TopoDS.Face_s(TopExp_Explorer(shape,TopAbs_FACE).Current());a=BRepAdaptor_Surface(face).BSpline();b=a.Copy()
    u0,u1,v0,v1=b.Bounds();b.IncreaseDegree(3,4);b.InsertUKnot(u0+.3*(u1-u0),1,0.);b.InsertVKnot(v0+.7*(v1-v0),1,0.)
    knots=TColStd_Array1OfReal(1,b.NbUKnots())
    for i in range(1,b.NbUKnots()+1):knots.SetValue(i,100+7*b.UKnot(i))
    b.SetUKnots(knots)
    assert surfaces_equal(a,b,False,1e-6)
    b.UReverse();assert surfaces_equal(a,b,True,1e-6)
    assert not surfaces_equal(a,b,False,1e-6)
    pole=b.Pole(2,2);pole.SetZ(pole.Z()+1);b.SetPole(2,2,pole)
    assert not surfaces_equal(a,b,True,.001)


def test_native_edge_data_retains_real_partition_for_comparison():
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge,BRepBuilderAPI_NurbsConvert
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS
    from OCP.gp import gp_Pnt
    from dsac29.parametric_identity import edge_data,edge_equal
    a=TopoDS.Edge_s(BRepBuilderAPI_NurbsConvert(BRepBuilderAPI_MakeEdge(gp_Pnt(0,0,0),gp_Pnt(10,0,0)).Edge(),True).Shape())
    curve=BRepAdaptor_Curve(a).BSpline().Copy();curve.IncreaseDegree(3)
    lo,hi=curve.FirstParameter(),curve.LastParameter();curve.InsertKnot(lo+.37*(hi-lo),1,0.)
    b=BRepBuilderAPI_MakeEdge(curve).Edge()
    assert len(edge_data(a)[1])!=len(edge_data(b)[1])
    assert edge_equal(edge_data(a),edge_data(b),1e-6)
    p=curve.Pole(2);p.SetY(.2);curve.SetPole(2,p)
    assert not edge_equal(edge_data(a),edge_data(BRepBuilderAPI_MakeEdge(curve).Edge()),.001)
