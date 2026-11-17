from pathlib import Path
import sys
p=Path(sys.argv[1])/'dsac29/parametric_identity.py';s=p.read_text()
a=" return ('bezier',out)"
b=""" from OCP.TColStd import TColStd_Array1OfReal
 knots=TColStd_Array1OfReal(1,split.NbArcs()+1);split.Knots(knots)
 values=list(knots)
 span=values[-1]-values[0]
 return ('bezier',out,[(v-values[0])/span for v in values])"""
assert s.count(a)==1;s=s.replace(a,b)
a=" return len(a[1])==len(b[1]) and all(pole_bound(x,y)<=tol for x,y in zip(a[1],b[1]))"
b=""" if len(a[1])==len(b[1]) and all(pole_bound(x,y)<=tol for x,y in zip(a[1],b[1])):return True
 if len(a)>2 and len(b)>2:
  from .bernstein_partition import curves_equal
  return curves_equal(a,b,tol)
 return False"""
assert s.count(a)==1;s=s.replace(a,b);p.write_text(s)
