"""Fail-closed alternative for a concentric, chamfered through-bore revision.

OCCT Common(A,B) can create invalid shells for coincident analytic faces.
This module does NOT infer equality from bounding boxes, sample points, or
volume alone: it constructs the candidate changed material from exact analytic
cylindrical/conical faces, proves Cut(B,material) matches original A using the
existing full oriented surface-and-trim proof, and verifies independent Boolean
subset/disjointness predicates. All other cases return None, not a verdict.

This narrow method is a genuine analytic construction, not an OCCT exception
suppressor. Run it only inside a disposable native process (OCCT can crash).
"""
from __future__ import annotations
import collections
import math

class BoreNotProven(Exception):
    pass


def _require(ok, reason):
    if not ok:
        raise BoreNotProven(reason)


def _volume(shape):
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    p=GProp_GProps()
    BRepGProp.VolumeProperties_s(shape,p)
    v=float(p.Mass())
    _require(math.isfinite(v) and v>=0, 'invalid signed volume')
    return v


def _faces(shape):
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    ex=TopExp_Explorer(shape,TopAbs_FACE)
    out=[]
    def coord(p):return tuple(round(float(v),6) for v in p.Coord())
    while ex.More():
        f=TopoDS.Face_s(ex.Current());ex.Next()
        a=BRepAdaptor_Surface(f)
        typ=str(a.GetType()).rsplit('.',1)[-1]
        _require(typ in ('GeomAbs_Plane','GeomAbs_Cylinder','GeomAbs_Cone','GeomAbs_Torus','GeomAbs_Sphere'),
                 'non-analytic surface')
        item=dict(type=typ,face=f)
        if typ=='GeomAbs_Plane':
            p=a.Plane();key=(typ,coord(p.Location()),coord(p.Axis().Direction()))
        elif typ=='GeomAbs_Cylinder':
            p=a.Cylinder();key=(typ,round(p.Radius(),6),coord(p.Location()),coord(p.Axis().Direction()))
            item.update(radius=float(p.Radius()),axis=coord(p.Axis().Direction()),point=coord(p.Location()))
        elif typ=='GeomAbs_Cone':
            p=a.Cone();key=(typ,round(p.RefRadius(),6),round(p.SemiAngle(),6),coord(p.Location()),coord(p.Axis().Direction()))
        elif typ=='GeomAbs_Torus':
            p=a.Torus();key=(typ,round(p.MajorRadius(),6),round(p.MinorRadius(),6),coord(p.Location()),coord(p.Axis().Direction()))
        else:
            p=a.Sphere();key=(typ,round(p.Radius(),6),coord(p.Location()))
        item['key']=key
        out.append(item)
    return out


def _circle_edges(face):
    from OCP.TopAbs import TopAbs_EDGE,TopAbs_WIRE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRep import BRep_Tool
    wires=TopExp_Explorer(face,TopAbs_WIRE)
    _require(wires.More(), 'missing face wire')
    wires.Next()
    _require(not wires.More(), 'multiple wires on changed face')
    edges=TopExp_Explorer(face,TopAbs_EDGE)
    circles=[];lines=0
    while edges.More():
        e=TopoDS.Edge_s(edges.Current());edges.Next()
        _require(not BRep_Tool.Degenerated_s(e),'degenerate bore edge')
        curve=BRepAdaptor_Curve(e)
        typ=str(curve.GetType()).rsplit('.',1)[-1]
        if typ=='GeomAbs_Circle':
            c=curve.Circle()
            _require(abs((curve.LastParameter()-curve.FirstParameter())-2*math.pi)<1e-6,
                     'partial circular bore edge')
            d=c.Axis().Direction()
            _require(abs(abs(d.Z())-1)<1e-7,'bore not parallel to Z')
            pt=c.Location()
            circles.append((float(pt.Z()),float(c.Radius()),float(pt.X()),float(pt.Y())))
        elif typ=='GeomAbs_Line':lines+=1
        else:raise BoreNotProven('unexpected bore edge curve '+typ)
    _require(len(circles)==2 and lines==2,'unexpected bore edge count')
    return sorted(circles)


def _bore_profile(faces,center,tol):
    _require(len(faces)==3,'not one cylinder with two conical chamfers')
    cyl=[f for f in faces if f['type']=='GeomAbs_Cylinder']
    cones=[f for f in faces if f['type']=='GeomAbs_Cone']
    _require(len(cyl)==1 and len(cones)==2,'changed bore surface types')
    x,y=center
    def centered(c):return abs(c[2]-x)<=tol/20 and abs(c[3]-y)<=tol/20
    c0,c1=_circle_edges(cyl[0]['face'])
    _require(centered(c0) and centered(c1),'cylinder axis mismatch')
    _require(abs(c0[1]-c1[1])<=tol/20 and c1[0]-c0[0]>tol,'cylinder edge radii or length mismatch')
    _require(abs(c0[1]-cyl[0]['radius'])<=tol/20,'cylinder radius mismatch')
    cone_edges=[_circle_edges(f['face']) for f in cones]
    all_circles=[e for pair in cone_edges for e in pair]
    _require(all(centered(c) for c in all_circles),'cone coaxiality mismatch')
    def matches(a,b):return abs(a[0]-b[0])<=tol/20 and abs(a[1]-b[1])<=tol/20
    low=[pair for pair in cone_edges if any(matches(c,c0) for c in pair)]
    high=[pair for pair in cone_edges if any(matches(c,c1) for c in pair)]
    _require(len(low)==len(high)==1 and low[0] is not high[0],'ambiguous chamfer faces')
    cap_low=next((c for c in low[0] if not matches(c,c0)),None)
    cap_high=next((c for c in high[0] if not matches(c,c1)),None)
    _require(cap_low is not None and cap_high is not None,'missing cap circles')
    _require(cap_low[0]<c0[0]-tol/10 and cap_high[0]>c1[0]+tol/10,'incorrect chamfer directions')
    _require(cap_low[1]>c0[1] and cap_high[1]>c1[1],'not outward chamfers')
    return [(cap_low[0],cap_low[1]),(c0[0],c0[1]),(c1[0],c1[1]),(cap_high[0],cap_high[1])]


def _construct_ring(old_profile,new_profile,x,y):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol
    from OCP.gp import gp_Pnt,gp_Ax1,gp_Dir
    poly=BRepBuilderAPI_MakePolygon()
    for z,r in old_profile+new_profile[::-1]:
        poly.Add(gp_Pnt(x+r,y,z))
    poly.Close()
    _require(poly.IsDone(),'cannot close radial profile')
    face=BRepBuilderAPI_MakeFace(poly.Wire())
    _require(face.IsDone(),'invalid radial profile face')
    revol=BRepPrimAPI_MakeRevol(face.Face(),gp_Ax1(gp_Pnt(x,y,0),gp_Dir(0,0,1)),2*math.pi,True)
    revol.Build()
    _require(revol.IsDone(),'revolution failed')
    return revol.Shape()


def _bool(optype,a,b):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Common
    from OCP.BRepCheck import BRepCheck_Analyzer
    op={'cut':BRepAlgoAPI_Cut,'common':BRepAlgoAPI_Common}[optype](a,b)
    op.SetNonDestructive(True)
    op.SetUseOBB(True)
    op.SetFuzzyValue(0.0001)
    op.Build()
    _require(op.IsDone(),'Boolean '+optype+' failed')
    result=op.Shape()
    _require(not result.IsNull() and BRepCheck_Analyzer(result).IsValid(),'Boolean '+optype+' invalid topology')
    return result


def try_added_bore(old,new,tolerance=.01):
    """Return (Common, Added, Removed) ONLY after full proof; else None.

    The original B-Rep shapes remain unchanged. Never infer a material delta
    from an invalid or timed-out Boolean. This must run in an isolated worker.
    """
    try:
        from OCP.BRepCheck import BRepCheck_Analyzer
        from OCP.BRep import BRep_Builder
        from OCP.TopoDS import TopoDS_Compound
        from .geometry import describe
        from .step_reexport_tolerance import reexport_equivalent_world
        _require(0<float(tolerance)<=.01,'tolerance exceeds CAD limit')
        _require(BRepCheck_Analyzer(old).IsValid() and BRepCheck_Analyzer(new).IsValid(),'invalid source')
        va,vb=_volume(old),_volume(new)
        _require(va>0 and vb>va,'not an additive revision')
        fa,fb=_faces(old),_faces(new)
        _require(5<=len(fa)==len(fb)<=1000,'unsupported face count')
        ca=collections.Counter(f['key'] for f in fa)
        cb=collections.Counter(f['key'] for f in fb)
        aonly=list((ca-cb).elements());bonly=list((cb-ca).elements())
        _require(len(aonly)==len(bonly)==3,'not exactly three changed analytic faces')
        def unique(fs,keys):
            counter=collections.Counter(keys)
            return [f for f in fs if counter[f['key']]>0]
        changed_a=unique(fa,aonly);changed_b=unique(fb,bonly)
        _require(len(changed_a)==len(changed_b)==3,'ambiguous changed faces')
        cyl_a=[f for f in changed_a if f['type']=='GeomAbs_Cylinder']
        cyl_b=[f for f in changed_b if f['type']=='GeomAbs_Cylinder']
        _require(len(cyl_a)==len(cyl_b)==1,'not a cylinder revision')
        xa,ya,_=cyl_a[0]['point'];xb,yb,_=cyl_b[0]['point']
        _require(abs(xa-xb)<tolerance/20 and abs(ya-yb)<tolerance/20,'cylinder centers differ')
        _require(all(abs(abs(f['axis'][2])-1)<1e-7 for f in (cyl_a[0],cyl_b[0])),'not axial Z bores')
        x,y=(xa+xb)/2,(ya+yb)/2
        pa=_bore_profile(changed_a,(x,y),tolerance)
        pb=_bore_profile(changed_b,(x,y),tolerance)
        _require(all(abs(z1-z2)<tolerance/20 for (z1,_),(z2,_) in zip(pa,pb)),'chamfer axial bounds differ')
        _require(all(r1-r2>tolerance/100 for (_,r1),(_,r2) in zip(pa,pb)),'bore change not uniformly additive')
        ring=_construct_ring(pa,pb,x,y)
        _require(BRepCheck_Analyzer(ring).IsValid(),'candidate ring invalid')
        vr=_volume(ring)
        _require(abs((vb-va)-vr)<=max(1e-5,1e-8*vb),'volume mismatch')
        reconstructed=_bool('cut',new,ring)
        _require(abs(_volume(reconstructed)-va)<=max(1e-5,1e-8*va),'reconstruction volume mismatch')
        _require(reexport_equivalent_world(describe(old,'A','original'),
                describe(reconstructed,'A','reconstructed'),tolerance,
                allow_boolean=False,_original_boundary_only=True),'original oriented boundaries not proven')
        residual=_bool('cut',ring,new)
        common_a=_bool('common',old,ring)
        common_b=_bool('common',new,ring)
        epsilon=max(1e-6,tolerance**3)
        _require(_volume(residual)<=epsilon,'ring not subset of B')
        _require(_volume(common_a)<=epsilon,'ring overlaps A')
        _require(abs(_volume(common_b)-vr)<=max(1e-5,1e-8*vr),'ring not fully inside B')
        empty=TopoDS_Compound();BRep_Builder().MakeCompound(empty)
        return (old,ring,empty)
    except (BoreNotProven,ValueError,RuntimeError,OverflowError,ZeroDivisionError):
        return None
