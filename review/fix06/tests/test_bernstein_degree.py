import numpy as np
from dsac29.parametric_identity import pole_bound
from dsac29.bernstein_degree import compatible_nets

def test_same_rational_curve_different_degrees():
    p=np.array([[0.,0,0],[3,7,2],[9,0,1]]);w=np.array([1.,.7,1.])
    h=np.c_[p*w[:,None],w];raised=np.array([h[0],h[0]/3+2*h[1]/3,2*h[1]/3+h[2]/3,h[2]])
    q=raised[:,:3]/raised[:,3,None];v=raised[:,3]
    assert pole_bound((p,w),(q,v))<1e-8
    q[1,2]+=.1
    assert pole_bound((p,w),(q,v))>.01

def test_native_surface_degree_elevation_preserves_proof():
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert,BRepBuilderAPI_MakeFace
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from dsac29.nurbs_orientation import oriented_surface_equal
    s=BRepBuilderAPI_NurbsConvert(BRepPrimAPI_MakeBox(10,20,30).Shape(),True).Shape()
    face=TopoDS.Face_s(TopExp_Explorer(s,TopAbs_FACE).Current())
    spline=BRepAdaptor_Surface(face).BSpline().Copy()
    spline.IncreaseDegree(4,5)
    other=BRepBuilderAPI_MakeFace(spline,1e-7).Face();other.Orientation(face.Orientation())
    assert oriented_surface_equal(face,other,.001)
    other.Reverse();assert not oriented_surface_equal(face,other,.001)
