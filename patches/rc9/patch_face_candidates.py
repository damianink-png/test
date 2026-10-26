"""Improve face candidate lookup without changing the CAD proof tolerance.

A STEP round-trip can perturb an integrated face centroid while its exact
analytic AABB and oriented trims remain unchanged. A centroid is a hint,
never a necessary condition of face equality.
"""
from pathlib import Path
import ast
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding='utf-8')
start = s.index('    buckets=defaultdict(list)\n', s.index('def reexport_equivalent_world('))
end = s.index('    # Perfect face correspondence:', start)
old = s[start:end]
assert 'if dc>tolerance:continue' in old
assert 'options.append([j for score,j in sorted(available)])' in old
replacement = '''    buckets=defaultdict(list)
    box_buckets=defaultdict(list)
    for i,(typ,ori,area,c,box) in enumerate(fb):
        buckets[(typ,ori,*(floor(float(v)/cell) for v in c))].append(i)
        box_buckets[(typ,ori,*(floor(float(v)/cell) for v in box[:3]))].append(i)
    from itertools import product
    offsets=tuple(product((-1,0,1),repeat=3))
    options=[]
    for typ,ori,area,c,box in fa:
        index=tuple(floor(float(v)/cell) for v in c)
        box_index=tuple(floor(float(v)/cell) for v in box[:3])
        indices=set()
        for d in offsets:
            indices.update(buckets.get((typ,ori,*(index[k]+d[k] for k in range(3))),()))
            indices.update(box_buckets.get((typ,ori,*(box_index[k]+d[k] for k in range(3))),()))
        available=[]
        for j in sorted(indices):
            _,_,area_b,cb,bb=fb[j]
            dc=float(np.linalg.norm(c-cb))
            db=float(np.max(np.abs(box-bb)))
            # Both are lookup filters. The original strict face/wire proof
            # below remains mandatory and uses the original tolerance.
            if dc>tolerance and db>tolerance:continue
            da=abs(area-area_b)
            area_lim=max(.1,2*tolerance*sqrt(max(1.,area,area_b)))
            if da>area_lim:continue
            if db>tolerance and 'BSpline' not in typ:continue
            score=min(dc,db)/max(tolerance,1e-6)+da/area_lim
            available.append((score,j))
        if not available:return False
        options.append([j for score,j in sorted(available)])
'''
s=s[:start]+replacement+s[end:]
ast.parse(s)
p.write_text(s,encoding='utf-8')
print('Face candidate AABB+centroid lookup patched; B-Rep proof unchanged')
