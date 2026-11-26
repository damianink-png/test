from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/parametric_identity.py';s=p.read_text()
a='allow_parametric_orientation=False):'
assert s.count(a)==1;s=s.replace(a,'allow_parametric_orientation=False,surface_prover=None,edge_prover=None):')
s=s.replace('  if not allow_parametric_orientation and (strict_repair', '  if surface_prover is None and not allow_parametric_orientation and (strict_repair')
a='   if allow_parametric_orientation:'
assert s.count(a)==1;s=s.replace(a,'   if surface_prover is not None:\n    if not surface_prover(fa[i],fb[j],tol):return False\n   elif allow_parametric_orientation:')
s=s.replace('def edge_data(e):','def edge_data(e,force_spline=False):')
s=s.replace(" if 'Line' in kind:return"," if not force_spline and 'Line' in kind:return")
s=s.replace(" if 'Circle' in kind:"," if not force_spline and 'Circle' in kind:")
s=s.replace('d=edge_data(e);cache.setdefault', 'd=edge_data(e,force_spline=surface_prover is not None);cache.setdefault')
a='def edge_options(left,right,tol):'
assert s.count(a)==1;s=s.replace(a,'def edge_options(left,right,tol,additional_proof=None):')
a=' for d in left:\n  p=anchor(d)'
assert s.count(a)==1;s=s.replace(a,' for i,d in enumerate(left):\n  p=anchor(d)')
a='  options.append([j for j in sorted(candidates) if edge_equal(d,right[j],tol)])'
assert s.count(a)==1
s=s.replace(a,'''  options.append([j for j in sorted(candidates) if edge_equal(d,right[j],tol)
                  or (additional_proof is not None and additional_proof(i,j))])''')
a='  def wires_equal(ex,ey):'
assert s.count(a)==1
s=s.replace(a,'''  def oriented_edges_equal(left,right):
   extra=None if edge_prover is None else lambda i,j: edge_prover(left[i],right[j],tol)
   return perfect(edge_options([data(e) for e in left],[data(e) for e in right],tol,extra))

  def wires_equal(ex,ey):''')
a='perfect(edge_options([data(e) for e in x],[data(e) for e in y],tol))'
assert s.count(a)==1;s=s.replace(a,'oriented_edges_equal(x,y)')
p.write_text(s);print('ORIGINAL_BOUNDARY_PATCH_PASS')
