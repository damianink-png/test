"""Geometric STEP identity: analytic surfaces / bounded Bezier control nets,
and ALL oriented trimming edges. No meshes, volume or area establish identity.
Unsupported or inconclusive cases fall back to solid Boolean verification.
"""
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Surface,BRepAdaptor_Curve
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE,TopAbs_WIRE,TopAbs_EDGE,TopAbs_VERTEX
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool
from OCP.Geom import Geom_TrimmedCurve
from OCP.GeomConvert import GeomConvert,GeomConvert_BSplineCurveToBezierCurve,GeomConvert_BSplineSurfaceToBezierSurface

def items(s,kind,cast):
 ex=TopExp_Explorer(s,kind);out=[]
 while ex.More():out.append(cast(ex.Current()));ex.Next()
 return out

def xyz(p):return np.array(p.Coord(),float)
def direction(a):return xyz(a.Direction())
def aligned(a,b):return b if np.dot(a,b)>=0 else -b

def pole_bound(a,b):
 p,w=a;q,v=b
 if p.shape!=q.shape or w.shape!=v.shape:return float('inf')
 if not all(np.all(np.isfinite(t)) for t in (p,q,w,v)) or min(w.min(),v.min())<=0:return float('inf')
 ratio=v/w
 if not np.all(np.isfinite(ratio)) or ratio.min()<=0:return float('inf')
 # Positive rational Bernstein weights: uniform bound over the ENTIRE patch.
 radius=np.linalg.norm(q-q.reshape(-1,q.shape[-1])[0],axis=-1).max()
 return np.linalg.norm(p-q,axis=-1).max()+(ratio.max()/ratio.min()-1)*radius+1e-10

def surface_equal(f,g,box,tol):
 a=BRepAdaptor_Surface(f);b=BRepAdaptor_Surface(g)
 if a.GetType()!=b.GetType():return False
 kind=str(a.GetType());center=(box[:3]+box[3:])/2;extent=np.linalg.norm(box[3:]-box[:3])/2
 if 'Plane' in kind:
  x,y=a.Plane(),b.Plane();n=direction(x.Axis());m=aligned(n,direction(y.Axis()))
  return abs(np.dot(center-xyz(x.Location()),n)-np.dot(center-xyz(y.Location()),m))+extent*np.linalg.norm(n-m)<=tol
 if 'Cylinder' in kind:
  x,y=a.Cylinder(),b.Cylinder();n=direction(x.Axis());m=aligned(n,direction(y.Axis()))
  u=xyz(x.Location());v=xyz(y.Location());u+=np.dot(center-u,n)*n;v+=np.dot(center-v,m)*m
  return np.linalg.norm(u-v)+extent*np.linalg.norm(n-m)+abs(x.Radius()-y.Radius())<=tol
 if 'Sphere' in kind:
  x,y=a.Sphere(),b.Sphere();return np.linalg.norm(xyz(x.Location())-xyz(y.Location()))+abs(x.Radius()-y.Radius())<=tol
 if 'Torus' in kind:
  x,y=a.Torus(),b.Torus();n=direction(x.Axis());m=aligned(n,direction(y.Axis()))
  return np.linalg.norm(xyz(x.Location())-xyz(y.Location()))+abs(x.MajorRadius()-y.MajorRadius())+abs(x.MinorRadius()-y.MinorRadius())+2*(x.MajorRadius()+x.MinorRadius())*np.linalg.norm(n-m)<=tol
 if 'Cone' in kind:
  x,y=a.Cone(),b.Cone();n=direction(x.Axis());m=direction(y.Axis());u=xyz(x.Apex());v=xyz(y.Apex())
  angle_x=float(x.SemiAngle());angle_y=float(y.SemiAngle())
  # The same cone nappe may use a reversed axis AND signed semi-angle.
  # Canonicalization preserves the exact surface; oriented trims are
  # independently checked below. This does not relax the CAD tolerance.
  if np.dot(n,m)<0:
   m=-m
   angle_y=-angle_y
  radius=np.linalg.norm(center-u)+extent;angle=max(abs(angle_x),abs(angle_y))
  if angle>=1.4:return False
  return np.linalg.norm(u-v)+2*radius*(np.linalg.norm(n-m)+abs(angle_x-angle_y))/(np.cos(angle)**2)<=tol
 if 'BSpline' in kind:
  x=GeomConvert_BSplineSurfaceToBezierSurface(a.BSpline());y=GeomConvert_BSplineSurfaceToBezierSurface(b.BSpline())
  if (x.NbUPatches(),x.NbVPatches())!=(y.NbUPatches(),y.NbVPatches()):return False
  if x.NbUPatches()*x.NbVPatches()>10000:return False
  def net(p):return np.array([[p.Pole(i,j).Coord() for j in range(1,p.NbVPoles()+1)] for i in range(1,p.NbUPoles()+1)]),np.array([[p.Weight(i,j) for j in range(1,p.NbVPoles()+1)] for i in range(1,p.NbUPoles()+1)])
  return all(pole_bound(net(x.Patch(i,j)),net(y.Patch(i,j)))<=tol for i in range(1,x.NbUPatches()+1) for j in range(1,x.NbVPatches()+1))
 return False

def edge_data(e):
 if BRep_Tool.Degenerated_s(e):
  vs=items(e,TopAbs_VERTEX,TopoDS.Vertex_s)
  return ('point',xyz(BRep_Tool.Pnt_s(vs[0])))
 a=BRepAdaptor_Curve(e);first,last=a.FirstParameter(),a.LastParameter();reverse=int(e.Orientation())==1
 start,end=xyz(a.Value(last if reverse else first)),xyz(a.Value(first if reverse else last))
 kind=str(a.GetType())
 if 'Line' in kind:return ('line',start,end)
 if 'Circle' in kind:
  c=a.Circle();axis=direction(c.Axis())*(-1 if reverse else 1)
  return ('circle',start,end,xyz(c.Location()),c.Radius(),axis,last-first)
 curve=a.Curve().Curve().Transformed(a.Trsf())
 s=GeomConvert.CurveToBSplineCurve_s(Geom_TrimmedCurve(curve,first,last))
 if reverse:s.Reverse()
 split=GeomConvert_BSplineCurveToBezierCurve(s)
 if split.NbArcs()>10000:raise ValueError('Curve budget')
 out=[]
 for k in range(1,split.NbArcs()+1):
  p=split.Arc(k);out.append((np.array([p.Pole(i).Coord() for i in range(1,p.NbPoles()+1)]),np.array([p.Weight(i) for i in range(1,p.NbPoles()+1)])))
 return ('bezier',out)

def edge_equal(a,b,tol):
 if a[0]!=b[0]:return False
 if a[0]=='point':return np.linalg.norm(a[1]-b[1])<=tol
 if a[0]=='line':return max(np.linalg.norm(a[1]-b[1]),np.linalg.norm(a[2]-b[2]))<=tol
 if a[0]=='circle':
  bound=np.linalg.norm(a[3]-b[3])+abs(a[4]-b[4])+2*max(a[4],b[4])*np.linalg.norm(a[5]-b[5])
  if bound>tol or max(a[6],b[6])>2*np.pi+1e-10:return False
  if abs(a[6]-b[6])*max(a[4],b[4])>tol:return False
  full=abs(a[6]-2*np.pi)*a[4]<=tol and abs(b[6]-2*np.pi)*b[4]<=tol
  return full or max(np.linalg.norm(a[1]-b[1]),np.linalg.norm(a[2]-b[2]))+bound<=tol
 return len(a[1])==len(b[1]) and all(pole_bound(x,y)<=tol for x,y in zip(a[1],b[1]))

def perfect(options):
 # Iterative augmenting paths also handle wires with thousands of edges.
 owner={};reverse={}
 for first in sorted(range(len(options)),key=lambda i:len(options[i])):
  queue=[first];seen_left={first};seen_right=set();parent={};free=None
  for i in queue:
   for j in options[i]:
    if j in seen_right:continue
    seen_right.add(j);parent[j]=i
    if j not in owner:free=j;break
    other=owner[j]
    if other not in seen_left:seen_left.add(other);queue.append(other)
   if free is not None:break
  if free is None:return False
  # Follow the alternating path back to the new unmatched left vertex.
  while True:
   i=parent[free];old=reverse.get(i);owner[free]=i;reverse[i]=free
   if old is None:break
   free=old
 return True

def edge_options(left,right,tol):
 """Spatial prefilter only; every accepted edge still needs edge_equal.

 Each edge type has an anchor whose distance <= tol is a NECESSARY
 condition of edge_equal, including full circles and rational Beziers.
 No sampling, rounded geometry equality or relaxed tolerance is used.
 """
 from collections import defaultdict
 from itertools import product
 from math import floor
 def anchor(d):
  if d[0] in ('point','line'):return d[1]
  if d[0]=='circle':return d[3]
  if d[0]=='bezier' and d[1]:return d[1][0][0][0]
  return None
 buckets=defaultdict(list);unindexed=[]
 for j,d in enumerate(right):
  p=anchor(d)
  if p is None or not np.isfinite(p).all():unindexed.append(j);continue
  buckets[(d[0],*(floor(float(v)/tol) for v in p))].append(j)
 options=[]
 for d in left:
  p=anchor(d)
  if p is None or not np.isfinite(p).all():candidates=range(len(right))
  else:
   cell=tuple(floor(float(v)/tol) for v in p);candidates=list(unindexed)
   for delta in product((-1,0,1),repeat=3):
    candidates.extend(buckets.get((d[0],*(cell[k]+delta[k] for k in range(3))),()))
  options.append([j for j in sorted(candidates) if edge_equal(d,right[j],tol)])
 return options

def collapsed_strip_orientation(f,g,tolerance):
 """Prove both complete positive-weight NURBS surfaces lie in one thin tube.

 This is a uniform convex-hull bound, never a point sample or area heuristic.
 Diameter of the common tube consumes at most half the supplied tolerance;
 the independent surface/trim proof retains the other half. Only the tolerant
 world-proof path may use it; original-to-repair proofs remain strict.
 """
 try:
  if int(f.Orientation())==int(g.Orientation()):return False
  if {int(f.Orientation()),int(g.Orientation())}!={0,1}:return False
  nets=[]
  for face in (f,g):
   adaptor=BRepAdaptor_Surface(face)
   if 'BSpline' not in str(adaptor.GetType()):return False
   surface=adaptor.BSpline()
   if surface.IsUPeriodic() or surface.IsVPeriodic():return False
   if surface.NbUPoles()*surface.NbVPoles()>256:return False
   u0,u1,v0,v1=surface.Bounds()
   if not np.isfinite([u0,u1,v0,v1]).all():return False
   if (adaptor.FirstUParameter()<u0 or adaptor.LastUParameter()>u1
       or adaptor.FirstVParameter()<v0 or adaptor.LastVParameter()>v1):return False
   net=[]
   for u in range(1,surface.NbUPoles()+1):
    for v in range(1,surface.NbVPoles()+1):
     weight=surface.Weight(u,v)
     if not np.isfinite(weight) or weight<=0:return False
     net.append(surface.Pole(u,v).Coord())
   nets.extend(net)
  poles=np.asarray(nets,dtype=float)
  if not len(poles) or not np.isfinite(poles).all():return False
  _,_,axes=np.linalg.svd(poles-poles.mean(axis=0),full_matrices=False)
  axis=axes[0];axis=axis/np.linalg.norm(axis)
  # B-spline basis functions are nonnegative and sum to one. Positive
  # weights therefore keep the ENTIRE surface in the convex control hull.
  # A cylinder is convex, so checking every pole bounds every surface point.
  radius=float(np.linalg.norm(np.cross(poles-poles[0],axis),axis=1).max())
  roundoff=1e-10+64*np.finfo(float).eps*max(1.,float(np.abs(poles).max()))
  return bool(radius+roundoff<=float(tolerance)/4.)
 except Exception:return False


def collapsed_cylinder_equal(f,g,tolerance):
 """Uniform two-way bound for a micro-cylinder bounded by two full lines.

 STEP can collapse its angular domain while retaining two axial line edges.
 Each complete analytic patch is enclosed in either a full circle disk or
 an arc ball, extruded over its entire V interval. Map every such point to
 an actual line edge of the other face. Convexity bounds the axial mapping
 by its endpoints; analytic arc bounds cover every U. No samples/areas.
 """
 try:
  descriptions=[]
  for face in (f,g):
   surface=BRepAdaptor_Surface(face)
   if 'Cylinder' not in str(surface.GetType()):return False
   radius=float(surface.Cylinder().Radius())
   if not 0<radius<=float(tolerance):return False
   u0,u1,v0,v1=(float(surface.FirstUParameter()),float(surface.LastUParameter()),
                 float(surface.FirstVParameter()),float(surface.LastVParameter()))
   if not np.isfinite([u0,u1,v0,v1]).all() or not 0<=u1-u0<=2*np.pi+1e-12 or v1<=v0:return False
   wires=items(face,TopAbs_WIRE,TopoDS.Wire_s)
   if len(wires)!=1:return False
   edges=items(wires[0],TopAbs_EDGE,TopoDS.Edge_s)
   if len(edges)!=2:return False
   lines=[edge_data(edge) for edge in edges]
   if any(d[0]!='line' or not np.isfinite(np.asarray(d[1:])).all() for d in lines):return False
   cylinder=surface.Cylinder();origin=xyz(cylinder.Location());axis=direction(cylinder.Axis())
   balls=[(origin+axis*v0,origin+axis*v1,radius),
          (xyz(surface.Value((u0+u1)/2,v0)),xyz(surface.Value((u0+u1)/2,v1)),
           2*radius*np.sin(min(2*np.pi,u1-u0)/4))]
   descriptions.append((balls,lines))
  magnitude=max(1.,*[float(np.abs(d[1:]).max()) for _,lines in descriptions for d in lines])
  roundoff=1e-10+128*np.finfo(float).eps*magnitude
  def mapped_segment(p,q,x,y):
   return min(max(np.linalg.norm(p-x),np.linalg.norm(q-y)),
              max(np.linalg.norm(p-y),np.linalg.norm(q-x)))
  for (balls,lines),(_,targets) in (descriptions,descriptions[::-1]):
   # Entire surface patch -> an actual edge of the other face.
   if min(mapped_segment(p,q,d[1],d[2])+r for p,q,r in balls for d in targets)+roundoff>tolerance:return False
   # Also cover every actual 3-D edge, even if a malformed STEP p-curve
   # places it slightly off the nominal cylinder support.
   if any(min(mapped_segment(d[1],d[2],e[1],e[2]) for e in targets)+roundoff>tolerance for d in lines):return False
  return True
 except Exception:return False


def prove(a,b,owner,face_data,tolerance,*,strict_repair=True,allow_original_micro_degenerate=False,allow_strip_orientation=False,allow_micro_cylinders=False):
 """Only for already validated solids; require all surfaces and boundary wires."""
 try:
  fa=items(a,TopAbs_FACE,TopoDS.Face_s);fb=items(b,TopAbs_FACE,TopoDS.Face_s);tol=tolerance/(8 if strict_repair else 2)
  if len(fa)!=len(fb) or len(owner)!=len(fa):return False
  if (strict_repair or not (allow_strip_orientation or allow_micro_cylinders)) and any(
      int(fa[i].Orientation())!=int(fb[j].Orientation()) for j,i in owner.items()):return False
  cache={}
  def data(e):
   key=(hash(e),int(e.Orientation()))
   for saved,d in cache.get(key,()):
    if saved.IsEqual(e):return d
   d=edge_data(e);cache.setdefault(key,[]).append((e,d));return d
  # Precompute each wire's native edges and exact-geometry bounds once.
  # Only a full edge-by-edge proof may yield True.
  from OCP.Bnd import Bnd_Box
  from OCP.BRepBndLib import BRepBndLib
  def wire_bounds(w):
   # Add_s inflates analytic arcs by their stored edge tolerance. STEP can
   # change that tolerance without changing the curve, so it is unsuitable
   # for this tight lookup filter. Every admitted wire still needs the full
   # oriented edge proof below at the original CAD tolerance.
   bb=Bnd_Box();BRepBndLib.AddOptimal_s(w,bb,False,False)
   return np.asarray(bb.Get(),dtype=float)
  def tiny_edge_cleanup(edges):
   if not strict_repair:return edges  # Half-budget proof cannot discard micro-seams
   # Some STEP re-exports insert one or two ~10-nm seam fragments. An edge
   # may be ignored ONLY if its *entire* conservative CAD AABB fits within
   # tolerance/4, the sum of removed spans is <=tolerance/2, and two full
   # edges remain. All other edges must pass the original exact-curve proof.
   # Micro-edge budgets are independent of the normal/repair proof tolerance.
   if len(edges)<3:return edges
   spans=[]
   for edge in edges:
    bounds=Bnd_Box();BRepBndLib.Add_s(edge,bounds)
    if bounds.IsVoid() or bounds.IsOpen():return edges
    coords=np.asarray(bounds.Get(),float)
    if not np.isfinite(coords).all():return edges
    spans.append(float(np.linalg.norm(coords[3:]-coords[:3])))
   tiny=[k for k,span in enumerate(spans) if span<=tolerance/4]
   if not tiny or len(tiny)>8 or sum(spans[k] for k in tiny)>tolerance/2:return edges
   remaining=[e for k,e in enumerate(edges) if k not in tiny]
   return remaining if len(remaining)>=2 else edges
  def _point_seam_variants(edges,count):
   # Only true zero-dimensional seams anchored to retained boundary vertices.
   # The retained oriented curves and their supporting surfaces are ALL proved.
   from itertools import combinations
   def vertices(edge):
    return items(edge,TopAbs_VERTEX,TopoDS.Vertex_s)
   if count not in (1,2):return []
   eligible=[]
   for k,edge in enumerate(edges):
    if not BRep_Tool.Degenerated_s(edge):continue
    # A real 3D curve, however small, cannot use this topological shortcut.
    if BRep_Tool.Curve_s(edge,0.,0.) is not None:continue
    points=vertices(edge)
    if (BRep_Tool.Tolerance_s(edge)>tol/8. or not points
        or any(not np.isfinite(xyz(BRep_Tool.Pnt_s(v))).all() for v in points)):continue
    eligible.append(k)
   if len(eligible)<count or len(eligible)>8:return []
   variants=[]
   for combo in combinations(eligible,count):
    omitted=set(combo);kept=[e for k,e in enumerate(edges) if k not in omitted]
    if len(kept)<2:continue
    native_anchors=[v for e in kept for v in vertices(e)]
    anchors=[xyz(BRep_Tool.Pnt_s(v)) for v in native_anchors]
    if not anchors:continue
    # Reuse the exact retained TopoDS vertex, not merely a nearby point.
    # Removing this duplicated zero-length seam adds no displacement budget.
    if all(all(any(v.IsSame(anchor) for anchor in native_anchors) and
               min(np.linalg.norm(xyz(BRep_Tool.Pnt_s(v))-p) for p in anchors)<=tol/64.
               for v in vertices(edges[k])) for k in omitted):
     variants.append(kept)
   return variants

  def wires_equal(ex,ey):
   ex=tiny_edge_cleanup(ex);ey=tiny_edge_cleanup(ey)
   left,right=[ex],[ey]
   strip_pair=bool(allow_strip_orientation and not strict_repair and
                   collapsed_strip_orientation(fa[i],fb[j],tolerance))
   if len(ex)!=len(ey) and (allow_original_micro_degenerate or strip_pair) and not strict_repair:
    # No area, centroid or AABB decides equality. The omitted edges have
    # NO 3D curve and only exact retained native vertices. Every remaining
    # oriented curve, every wire and the complete surface still need proof.
    if len(ex)>len(ey):left=_point_seam_variants(ex,len(ex)-len(ey))
    else:right=_point_seam_variants(ey,len(ey)-len(ex))
   for x in left:
    for y in right:
     if len(x)==len(y) and x and perfect(edge_options([data(e) for e in x],[data(e) for e in y],tol)):
      return True
   return False
  for j,i in owner.items():
   if not strict_repair and allow_micro_cylinders and collapsed_cylinder_equal(fa[i],fb[j],tolerance):
    continue  # Complete patch AND both real line edges were uniformly bounded.
   if int(fa[i].Orientation())!=int(fb[j].Orientation()):
    if (strict_repair or not allow_strip_orientation or
        not collapsed_strip_orientation(fa[i],fb[j],tolerance)):return False
   if not surface_equal(fa[i],fb[j],face_data[i][4],tol):return False
   wa=items(fa[i],TopAbs_WIRE,TopoDS.Wire_s);wb=items(fb[j],TopAbs_WIRE,TopoDS.Wire_s)
   if len(wa)!=len(wb) or not wa:return False
   edges_a=[items(w,TopAbs_EDGE,TopoDS.Edge_s) for w in wa]
   edges_b=[items(w,TopAbs_EDGE,TopoDS.Edge_s) for w in wb]
   bounds_a=np.asarray([wire_bounds(w) for w in wa])
   bounds_b=np.asarray([wire_bounds(w) for w in wb])
   # Four times the per-edge tolerance covers endpoint and OCC bound slack.
   slack=max(4*tol,1.e-6)
   options=[]
   for k,ex in enumerate(edges_a):
    candidates=np.flatnonzero(np.max(np.abs(bounds_b-bounds_a[k]),axis=1)<=slack)
    options.append([int(n) for n in candidates
                    if wires_equal(ex,edges_b[n])])
    if not options[-1]:return False
   if not perfect(options):return False
  return True
 except Exception:return False
