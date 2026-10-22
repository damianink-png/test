"""Safe optimization for large assemblies' one-to-one assignment.

No geometry classification/STEP changes. The graph component traversal changes
from repeatedly scanning remaining vertices O(V²) to O(V+E), and degree-one
components are resolved directly because they are provably unique.
"""
import os
from pathlib import Path
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'dsac29/assignment.py'
s=p.read_text('utf8')
old="        todo=[min(remaining)];component=set()"
assert s.count(old)==1
s=s.replace(old,"        todo=[next(iter(remaining))];component=set()",1)
old="""        local={(i,j):c for i in aa for j in bb if (c:=edges.get((i,j))) is not None}
        audit=max(len(aa),len(bb))<=max_component"""
new="""        if len(aa)==len(bb)==1:
            # Only possible matching in this connected component. By the
            # minimum-cardinality-first objective it is compulsory and its
            # global uniqueness is exact, not a heuristic.
            answer.append((aa[0],bb[0],False,float('inf')))
            continue
        # Enumerate sparse adjacent edges instead of Cartesian aa × bb.
        available_b=set(bb)
        local={(i,j):edges[i,j] for i in aa
               for _,j in adjacent['a',i] if j in available_b}
        audit=max(len(aa),len(bb))<=max_component"""
assert s.count(old)==1
s=s.replace(old,new,1)
p.write_text(s,encoding='utf8')
print('assignment: direct singleton proofs and O(V+E) component traversal; Hungarian retained for competing pairs')
