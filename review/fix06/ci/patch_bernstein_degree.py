from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/parametric_identity.py';s=p.read_text()
a=" if p.shape!=q.shape or w.shape!=v.shape:return float('inf')"
b=""" if p.shape!=q.shape or w.shape!=v.shape:
  from .bernstein_degree import compatible_nets
  try:(p,w),(q,v)=compatible_nets((p,w),(q,v))
  except (ValueError,TypeError,IndexError):return float('inf')"""
assert s.count(a)==1;s=s.replace(a,b);p.write_text(s)
print('BERNSTEIN_DEGREE_PATCH_PASS')
