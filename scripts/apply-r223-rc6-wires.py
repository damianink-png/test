"""RC6: indexed CAD wire matching and bounded native world proof.
Numeric wire bounds are a necessary rejection filter, NEVER equality proof.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/'dsac29/parametric_identity.py'
s=p.read_text(encoding='utf-8')
old='''  def wires_equal(x,y):
   ex=items(x,TopAbs_EDGE,TopoDS.Edge_s);ey=items(y,TopAbs_EDGE,TopoDS.Edge_s)
   if len(ex)!=len(ey) or not ex:return False
   dx=[data(e) for e in ex];dy=[data(e) for e in ey]
   return perfect(edge_options(dx,dy,tol))
  for j,i in owner.items():
   if not surface_equal(fa[i],fb[j],face_data[i][4],tol):return False
   wa=items(fa[i],TopAbs_WIRE,TopoDS.Wire_s);wb=items(fb[j],TopAbs_WIRE,TopoDS.Wire_s)
   if len(wa)!=len(wb) or not wa:return False
   if not perfect([[k for k,y in enumerate(wb) if wires_equal(x,y)] for x in wa]):return False
'''
new='''  # Precompute each wire's native edges and exact-geometry bounds once.
  # Only a full edge-by-edge proof may yield True.
  from OCP.Bnd import Bnd_Box
  from OCP.BRepBndLib import BRepBndLib
  def wire_bounds(w):
   bb=Bnd_Box();BRepBndLib.AddOptimal_s(w,bb,False,False)
   return np.asarray(bb.Get(),dtype=float)
  def wires_equal(ex,ey):
   if len(ex)!=len(ey) or not ex:return False
   dx=[data(e) for e in ex];dy=[data(e) for e in ey]
   return perfect(edge_options(dx,dy,tol))
  for j,i in owner.items():
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
                    if len(ex)==len(edges_b[n]) and wires_equal(ex,edges_b[n])])
    if not options[-1]:return False
   if not perfect(options):return False
'''
assert s.count(old)==1,'Unexpected parametric_identity.prove layout'
p.write_text(s.replace(old,new),encoding='utf-8')
p=root/'dsac29/compare.py'
s=p.read_text(encoding='utf-8')
old='''                        if step_reexport_tolerance or not candidate(s,b[j],tolerance):
                            same=trace.brep_call('reexport_world',i,j,(guarded_world_reexport if len(a)>=600 and step_reexport_tolerance else reexport_equivalent_world),s,b[j],tolerance)
                        else:
                            same=trace.brep_call('equivalent_world',i,j,equivalent_world,s,b[j],tolerance)
                            if not same and coarse_candidate(s,b[j],tolerance):
                                same=trace.brep_call('reexport_world_fallback',i,j,(guarded_world_reexport if len(a)>=600 else reexport_equivalent_world),s,b[j],tolerance)
'''
new='''                        # A registered large STEP frame may contain faces
                        # where in-process OCC Common stalls >100s or crashes.
                        # Use a bounded child for the residual pairs. Timeout
                        # is an INCOMPLETE proof, never a positive equality.
                        large_registered = len(a)>=600 and bool(certified_pairs)
                        if large_registered:
                            same=trace.brep_call('registered_world_guarded',i,j,
                                guarded_world_reexport,s,b[j],tolerance)
                        elif step_reexport_tolerance or not candidate(s,b[j],tolerance):
                            same=trace.brep_call('reexport_world',i,j,(guarded_world_reexport if len(a)>=600 and step_reexport_tolerance else reexport_equivalent_world),s,b[j],tolerance)
                        else:
                            same=trace.brep_call('equivalent_world',i,j,equivalent_world,s,b[j],tolerance)
                            if not same and coarse_candidate(s,b[j],tolerance):
                                same=trace.brep_call('reexport_world_fallback',i,j,(guarded_world_reexport if len(a)>=600 else reexport_equivalent_world),s,b[j],tolerance)
'''
assert s.count(old)==1,'Unexpected compare.py world proof layout'
p.write_text(s.replace(old,new),encoding='utf-8')
print('Applied RC6 indexed CAD-wire matching and bounded registered world checks')
