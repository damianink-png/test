import itertools
import numpy as np
from dsac29.assignment import assign

def test_global_assignment_beats_nearest_first():
 edges={(0,0):.09,(0,1):.11,(1,0):.01,(1,1):.21}
 result=assign(edges)
 assert {(a,b) for a,b,_,_ in result}=={(0,1),(1,0)}
 assert all(not uncertain for _,_,uncertain,_ in result)

def test_equal_alternatives_are_uncertain():
 assert all(x[2] for x in assign({(i,j):.2 for i in range(3) for j in range(3)}))

def test_matches_exhaustive_optimum_and_gap():
 rng=np.random.default_rng(1947)
 for n in range(1,5):
  for _ in range(15):
   edges={(i,j):float(rng.random()) for i in range(n) for j in range(n) if rng.random()>.25}
   possibilities=[]
   for choice in itertools.product(range(-1,n),repeat=n):
    js=[j for j in choice if j>=0]
    if len(set(js))!=len(js) or any((i,j) not in edges for i,j in enumerate(choice) if j>=0):continue
    pairs={(i,j) for i,j in enumerate(choice) if j>=0}
    possibilities.append((len(pairs),sum(edges[p] for p in pairs),pairs))
   optimum=min(possibilities,key=lambda x:(-x[0],x[1]))
   actual=assign(edges)
   pairs={(i,j) for i,j,_,_ in actual}
   assert len(pairs)==optimum[0]
   assert abs(sum(edges[p] for p in pairs)-optimum[1])<1e-9
   for i,j,uncertain,gap in actual:
    alternatives=[x for x in possibilities if (i,j) not in x[2] and x[0]==optimum[0]]
    expected=min((x[1]-optimum[1] for x in alternatives),default=float('inf'))
    assert uncertain==(expected<=.025+1e-10)

def test_large_group_fallback_is_explicitly_uncertain():
 result=assign({(i,j):abs(i-j)/70 for i in range(65) for j in range(65)})
 assert len(result)==65 and all(x[2] and x[3] is None for x in result)

def test_input_order_does_not_change_assignment():
 edges={(0,0):.09,(0,1):.11,(1,0):.01,(1,1):.21}
 assert assign(edges)==assign(dict(reversed(list(edges.items()))))
