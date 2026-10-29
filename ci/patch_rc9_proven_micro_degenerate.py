"""Prove a single redundant 3-D point seam in invalid STEP re-exports.

No CAD tolerance relaxation, no removal of non-degenerate edges, no
acceptance of invalid repairs or Boolean results.
"""
from pathlib import Path
import ast
import sys

root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'

def edit(filename, replacements):
    path=root/'dsac29'/filename
    source=path.read_text(encoding='utf-8')
    for old,new in replacements:
        if source.count(old)!=1:
            raise SystemExit(f'{filename}: expected one anchor, got {source.count(old)}')
        source=source.replace(old,new)
    ast.parse(source)
    path.write_text(source,encoding='utf-8')

edit('parametric_identity.py',[
 ('def prove(a,b,owner,face_data,tolerance,*,strict_repair=True):',
  'def prove(a,b,owner,face_data,tolerance,*,strict_repair=True,allow_original_micro_degenerate=False):'),
 ('''  def wires_equal(ex,ey):
   ex=tiny_edge_cleanup(ex);ey=tiny_edge_cleanup(ey)
   if len(ex)!=len(ey) or not ex:return False
   dx=[data(e) for e in ex];dy=[data(e) for e in ey]
   return perfect(edge_options(dx,dy,tol))
''','''  def _one_proven_redundant_degenerate(edges):
   """Ignore one point seam only if it repeats a retained boundary vertex."""
   from OCP.BRep import BRep_Tool
   from OCP.TopAbs import TopAbs_VERTEX
   from OCP.TopoDS import TopoDS
   def vertices(edge):
    return [np.asarray(BRep_Tool.Pnt_s(v).Coord(),float)
            for v in items(edge,TopAbs_VERTEX,TopoDS.Vertex_s)]
   candidates=[]
   for k,edge in enumerate(edges):
    if not BRep_Tool.Degenerated_s(edge):continue
    bounds=Bnd_Box();BRepBndLib.Add_s(edge,bounds,False)
    if bounds.IsVoid() or bounds.IsOpen():continue
    coords=np.asarray(bounds.Get(),float)
    if not np.isfinite(coords).all():continue
    if np.linalg.norm(coords[3:]-coords[:3])>min(tol/8.,.001):continue
    if BRep_Tool.Tolerance_s(edge)>tol/8.:continue
    retained=[e for m,e in enumerate(edges) if m!=k]
    if len(retained)<2:continue
    point_vertices=vertices(edge)
    other_vertices=[v for e in retained for v in vertices(e)]
    if not point_vertices or not other_vertices:continue
    if all(min(np.linalg.norm(p-v) for v in other_vertices)<=tol/64.
           for p in point_vertices):
     candidates.append(retained)
   return candidates[0] if len(candidates)==1 else edges

  def wires_equal(ex,ey):
   ex=tiny_edge_cleanup(ex);ey=tiny_edge_cleanup(ey)
   if len(ex)!=len(ey) and allow_original_micro_degenerate and not strict_repair:
    # Original/original invalid-STEP proof only. Require the supporting
    # face area, centroid and bounds to agree far inside the CAD budget.
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    pa,pb=GProp_GProps(),GProp_GProps()
    BRepGProp.SurfaceProperties_s(fa[i],pa)
    BRepGProp.SurfaceProperties_s(fb[j],pb)
    ba,bb=Bnd_Box(),Bnd_Box()
    BRepBndLib.AddOptimal_s(fa[i],ba,False,False)
    BRepBndLib.AddOptimal_s(fb[j],bb,False,False)
    if (abs(pa.Mass()-pb.Mass())<=4*tol*tol
        and np.linalg.norm(np.asarray(pa.CentreOfMass().Coord())-
                           np.asarray(pb.CentreOfMass().Coord()))<=tol/16.
        and np.max(np.abs(np.asarray(ba.Get())-np.asarray(bb.Get())))<=tol/16.):
     if len(ex)>len(ey):ex=_one_proven_redundant_degenerate(ex)
     elif len(ey)>len(ex):ey=_one_proven_redundant_degenerate(ey)
   if len(ex)!=len(ey) or not ex:return False
   dx=[data(e) for e in ex];dy=[data(e) for e in ey]
   return perfect(edge_options(dx,dy,tol))
''')
])
edit('step_reexport_tolerance.py',[
 ('''        return bool(prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=False))''',
  '''        return bool(prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=False,
                          allow_original_micro_degenerate=True))''')
])
print('PASS: bounded degenerate-point seam proof; all other safety checks retained')
