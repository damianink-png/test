"""Component-wise minimum-cost one-to-one assignment, with ambiguity audit.

Original implementation of the rectangular Hungarian algorithm. No SciPy
runtime dependency. Candidate generation and geometric evidence stay upstream.
"""
from collections import defaultdict
import numpy as np

def _hungarian(cost):
    n,m=cost.shape
    u=np.zeros(n+1);v=np.zeros(m+1);p=np.zeros(m+1,dtype=int);way=np.zeros(m+1,dtype=int)
    for i in range(1,n+1):
        p[0]=i;j0=0;minimum=np.full(m+1,np.inf);used=np.zeros(m+1,dtype=bool)
        while True:
            used[j0]=True;i0=p[j0];delta=np.inf;j1=0
            for j in range(1,m+1):
                if used[j]:continue
                current=cost[i0-1,j-1]-u[i0]-v[j]
                if current<minimum[j]:minimum[j]=current;way[j]=j0
                if minimum[j]<delta:delta=minimum[j];j1=j
            for j in range(m+1):
                if used[j]:u[p[j]]+=delta;v[j]-=delta
                else:minimum[j]-=delta
            j0=j1
            if p[j0]==0:break
        while True:
            j1=way[j0];p[j0]=p[j1];j0=j1
            if j0==0:break
    result=[(int(p[j])-1,j-1) for j in range(1,m+1) if p[j]]
    return result,sum(float(cost[i,j]) for i,j in result)

def assign(edges,margin=0.025,max_component=60):
    """edges[(A,B)] = cost in [0,1]. Return (A,B,ambiguous,gap).

    Maximize eligible pair count, then minimize total cost. Rejecting one chosen
    edge and solving again measures ambiguity of the WHOLE assignment. Large
    connected components use bounded greedy fallback, explicitly ambiguous.
    """
    adjacent=defaultdict(set)
    for i,j in edges:
        adjacent['a',i].add(('b',j));adjacent['b',j].add(('a',i))
    remaining=set(adjacent);answer=[]
    while remaining:
        todo=[min(remaining)];component=set()
        while todo:
            node=todo.pop()
            if node in component:continue
            component.add(node);todo.extend(adjacent[node]-component)
        remaining-=component
        aa=sorted(i for role,i in component if role=='a');bb=sorted(j for role,j in component if role=='b')
        local={(i,j):c for i in aa for j in bb if (c:=edges.get((i,j))) is not None}
        if max(len(aa),len(bb))>max_component:
            used_a=set();used_b=set()
            for (i,j),cost in sorted(local.items(),key=lambda x:(x[1],x[0])):
                if i not in used_a and j not in used_b:
                    answer.append((i,j,True,None));used_a.add(i);used_b.add(j)
            continue
        ix={a:i for i,a in enumerate(aa)};jx={b:j for j,b in enumerate(bb)}
        # Dummy penalty dominates the sum of all valid edge costs.
        penalty=len(aa)+len(bb)+1
        matrix=np.full((len(aa),len(bb)+len(aa)),float(penalty))
        matrix[:,:len(bb)]=penalty*100
        for (i,j),cost in local.items():matrix[ix[i],jx[j]]=cost
        chosen,best=_hungarian(matrix)
        for i,j in chosen:
            if j>=len(bb) or (aa[i],bb[j]) not in local:continue
            old=matrix[i,j];matrix[i,j]=penalty*100
            _,alternative=_hungarian(matrix);matrix[i,j]=old
            gap=max(0.,alternative-best)
            answer.append((aa[i],bb[j],gap<=margin,gap))
    return sorted(answer)
