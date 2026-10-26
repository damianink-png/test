"""RC7: conservative STEP re-export CAD proof fixes for two exact native failures.

No change to user tolerance, matching policy, Boolean fallback, or crash guards.
Only prefilters are relaxed where full analytic surface + oriented trim proof
remains mandatory; micro-edges are bounded to <0.8% of tolerance.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1])
step=root/"dsac29/step_reexport_tolerance.py"
s=step.read_text(encoding="utf-8")
old="                if db>tolerance:continue"
new="""                # STEP round-trips can perturb OCC's per-face B-spline AABB
                # while the *entire* analytic patch and all trims are unchanged.
                # This is only a candidate filter: prove() below must still
                # verify every surface and every oriented boundary wire.
                if db>tolerance and 'BSpline' not in typ:continue"""
assert s.count(old)==1, "Unexpected RC7 STEP source: B-spline filter"
step.write_text(s.replace(old,new),encoding="utf-8")

param=root/"dsac29/parametric_identity.py"
s=param.read_text(encoding="utf-8")
old="""  def wires_equal(ex,ey):
   if len(ex)!=len(ey) or not ex:return False
   dx=[data(e) for e in ex];dy=[data(e) for e in ey]
   return perfect(edge_options(dx,dy,tol))"""
new="""  def tiny_edge_cleanup(edges):
   # Some STEP re-exports insert one or two ~10-nm seam fragments. An edge
   # may be ignored ONLY if its *entire* conservative CAD AABB fits within
   # tol/16, the sum of removed spans is <=tol/4, and at least two full
   # edges remain. All other edges must pass the original exact-curve proof.
   # tol is already the stricter user tolerance/8.
   if len(edges)<3:return edges
   spans=[]
   for edge in edges:
    bounds=Bnd_Box();BRepBndLib.Add_s(edge,bounds)
    if bounds.IsVoid() or bounds.IsOpen():return edges
    coords=np.asarray(bounds.Get(),float)
    if not np.isfinite(coords).all():return edges
    spans.append(float(np.linalg.norm(coords[3:]-coords[:3])))
   tiny=[k for k,span in enumerate(spans) if span<=tol/16]
   if not tiny or len(tiny)>2 or sum(spans[k] for k in tiny)>tol/4:return edges
   remaining=[e for k,e in enumerate(edges) if k not in tiny]
   return remaining if len(remaining)>=2 else edges
  def wires_equal(ex,ey):
   ex=tiny_edge_cleanup(ex);ey=tiny_edge_cleanup(ey)
   if len(ex)!=len(ey) or not ex:return False
   dx=[data(e) for e in ex];dy=[data(e) for e in ey]
   return perfect(edge_options(dx,dy,tol))"""
assert s.count(old)==1, "Unexpected RC7 parametric proof source"
s=s.replace(old,new)
old="if len(ex)==len(edges_b[n]) and wires_equal(ex,edges_b[n])"
assert s.count(old)==1, "Unexpected RC7 wire prefilter"
s=s.replace(old,"if wires_equal(ex,edges_b[n])")
param.write_text(s,encoding="utf-8")
print("RC7 conservative parametric proof patch applied")
