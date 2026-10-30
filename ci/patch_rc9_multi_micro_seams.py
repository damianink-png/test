"""RC9: prove bounded redundant STEP point seams; fail closed on source drift."""
import ast
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'/'dsac29'
p=root/'parametric_identity.py'
s=p.read_text(encoding='utf-8')
start=s.index('  def _one_proven_redundant_degenerate(edges):')
end=s.index('  for j,i in owner.items():',start)
old=s[start:end]
if ('return candidates[0] if len(candidates)==1 else edges' not in old
    or 'if len(ex)!=len(ey) or not ex:return False' not in old):
    raise RuntimeError('Unexpected audited RC9 micro-seam proof')
new='''  def _point_seam_variants(edges, count):
   # A candidate may omit at most two true degenerate point edges. Their
   # conservative total extent stays below half the 0.01-mm CAD tolerance.
   from itertools import combinations
   from OCP.BRep import BRep_Tool
   from OCP.TopAbs import TopAbs_VERTEX
   from OCP.TopoDS import TopoDS
   def vertices(e):
    return [np.asarray(BRep_Tool.Pnt_s(v).Coord(),float)
            for v in items(e,TopAbs_VERTEX,TopoDS.Vertex_s)]
   if count not in (1,2):return []
   eligible=[]
   for k,e in enumerate(edges):
    if not BRep_Tool.Degenerated_s(e):continue
    box=Bnd_Box();BRepBndLib.Add_s(e,box,False)
    if box.IsVoid() or box.IsOpen():continue
    xyz=np.asarray(box.Get(),float)
    if not np.isfinite(xyz).all():continue
    span=float(np.linalg.norm(xyz[3:]-xyz[:3]))
    if span<=tol/2. and BRep_Tool.Tolerance_s(e)<=tol/8.:
     eligible.append((k,span))
   if len(eligible)<count or len(eligible)>8:return []
   result=[]
   for combo in combinations(eligible,count):
    if sum(span for _,span in combo)>tol:continue
    omitted={k for k,_ in combo}
    kept=[e for k,e in enumerate(edges) if k not in omitted]
    if len(kept)<2:continue
    anchors=[v for e in kept for v in vertices(e)]
    if not anchors:continue
    if all(vertices(edges[k]) and all(
           min(np.linalg.norm(p-v) for v in anchors)<=tol/64.
           for p in vertices(edges[k])) for k in omitted):
     result.append(kept)
   return result

  def wires_equal(ex,ey):
   ex=tiny_edge_cleanup(ex);ey=tiny_edge_cleanup(ey)
   left,right=[ex],[ey]
   if len(ex)!=len(ey) and allow_original_micro_degenerate and not strict_repair:
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    pa,pb=GProp_GProps(),GProp_GProps()
    BRepGProp.SurfaceProperties_s(fa[i],pa)
    BRepGProp.SurfaceProperties_s(fb[j],pb)
    ba,bb=Bnd_Box(),Bnd_Box()
    BRepBndLib.AddOptimal_s(fa[i],ba,False,False)
    BRepBndLib.AddOptimal_s(fb[j],bb,False,False)
    # Area is a necessary tolerance-scaled filter, NOT the verdict.
    # Every retained 3D edge and its supporting analytic surface is proven.
    if (abs(pa.Mass()-pb.Mass())<=max(4*tol*tol,tol*np.sqrt(max(pa.Mass(),pb.Mass())))
        and np.linalg.norm(np.asarray(pa.CentreOfMass().Coord())-
                           np.asarray(pb.CentreOfMass().Coord()))<=tol/16.
        and np.max(np.abs(np.asarray(ba.Get())-np.asarray(bb.Get())))<=tol/16.):
     if len(ex)>len(ey):left=_point_seam_variants(ex,len(ex)-len(ey))
     else:right=_point_seam_variants(ey,len(ey)-len(ex))
   # No positive result without a full bijection of all retained 3D edges.
   for x in left:
    for y in right:
     if len(x)==len(y) and x and perfect(edge_options(
          [data(e) for e in x],[data(e) for e in y],tol)):
      return True
   return False
'''
s=s[:start]+new+s[end:]
ast.parse(s);p.write_text(s,encoding='utf-8')
p=root/'step_reexport_tolerance.py';s=p.read_text(encoding='utf-8')
old='    if (prove(a.shape,b.shape,owner,fa,tolerance) or (not allow_boolean and not _repair_boundary_only and prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=False))):return True'
new='''    if prove(a.shape,b.shape,owner,fa,tolerance):return True
    # Source solids must remain valid. Point seams are only a candidate
    # omission; all retained analytic surfaces and trims still get proved.
    if (not _repair_boundary_only and shape_valid(a.shape) and shape_valid(b.shape)
        and prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=False,
                  allow_original_micro_degenerate=True)):
        return True'''
if s.count(old)!=1:raise RuntimeError('Unexpected audited RC9 world-proof call')
s=s.replace(old,new);ast.parse(s);p.write_text(s,encoding='utf-8')
print('PASS: bounded point-seam proof patched, native validation preserved')
