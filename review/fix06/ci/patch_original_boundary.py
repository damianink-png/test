from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/parametric_identity.py';s=p.read_text()
a='allow_parametric_orientation=False):'
assert s.count(a)==1;s=s.replace(a,'allow_parametric_orientation=False,surface_prover=None):')
s=s.replace('  if not allow_parametric_orientation and (strict_repair', '  if surface_prover is None and not allow_parametric_orientation and (strict_repair')
a='   if allow_parametric_orientation:'
assert s.count(a)==1;s=s.replace(a,'   if surface_prover is not None:\n    if not surface_prover(fa[i],fb[j],tol):return False\n   elif allow_parametric_orientation:')
s=s.replace('def edge_data(e):','def edge_data(e,force_spline=False):')
s=s.replace(" if 'Line' in kind:return"," if not force_spline and 'Line' in kind:return")
s=s.replace(" if 'Circle' in kind:"," if not force_spline and 'Circle' in kind:")
s=s.replace('d=edge_data(e);cache.setdefault', 'd=edge_data(e,force_spline=surface_prover is not None);cache.setdefault')
p.write_text(s);print('ORIGINAL_BOUNDARY_PATCH_PASS')
