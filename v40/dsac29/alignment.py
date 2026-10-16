"""Optional rigid assembly registration using unique named, verified anchors."""
from collections import defaultdict
import numpy as np
from .geometry import equivalent_rigid, transform, describe


def align_assembly(a, b, tolerance=0.01, progress=None):
    names_a=defaultdict(list);names_b=defaultdict(list)
    for i,p in enumerate(a):names_a[p.name].append(i)
    for j,p in enumerate(b):names_b[p.name].append(j)
    pairs=[(v[0],names_b[k][0]) for k,v in names_a.items()
           if len(v)==1 and len(names_b.get(k,[]))==1]
    if not pairs:raise ValueError('Brak jednoznacznej wspólnej części do wyrównania. Wyłącz wyrównanie lub nadaj częściom unikalne nazwy.')
    pairs.sort(key=lambda ij:-a[ij[0]].volume)
    candidates=[]
    if len(pairs)>=3:
        pa=np.array([a[i].center for i,j in pairs]);pb=np.array([b[j].center for i,j in pairs])
        ca=pa.mean(axis=0);cb=pb.mean(axis=0)
        if np.linalg.matrix_rank(pb-cb,tol=tolerance)>=2:
            U,_,Vt=np.linalg.svd((pb-cb).T@(pa-ca))
            D=np.eye(3);D[-1,-1]=np.linalg.det(Vt.T@U.T)
            Q=Vt.T@D@U.T;u=ca-Q@cb
            from .geometry import equivalent_world
            votes=0
            for i,j in pairs:
                if np.linalg.norm(a[i].center-(Q@b[j].center+u))>tolerance:continue
                aligned=describe(transform(b[j].shape,Q,u),b[j].name,b[j].path)
                if equivalent_world(a[i],aligned,tolerance):votes+=1
            if votes:candidates.append((votes,Q,u,pairs[0][0],pairs[0][1]))
    for i,j in pairs[:12]:
        same,R,t=equivalent_rigid(a[i],b[j],tolerance)
        if not same:continue
        distances=[np.linalg.norm(a[x].center-(R@b[y].center+t)) for x,y in pairs]
        votes=sum(d<=max(tolerance,1e-4) for d in distances)
        candidates.append((votes,R,t,i,j))
    if not candidates:raise ValueError('Nie potwierdzono wspólnej geometrii do wyrównania.')
    candidates.sort(key=lambda x:-x[0]);votes,R,t,i,j=candidates[0]
    if votes/max(1,len(pairs))<0.6:
        raise ValueError('Brak zgodnej transformacji większości wspólnych części. Wyłącz wyrównanie i sprawdź położenia.')
    # Equal-scoring inconsistent transforms indicate symmetric-anchor ambiguity.
    for n,Q,u,_,_ in candidates[1:]:
        if n==votes and (not np.allclose(R,Q,atol=1e-7) or np.linalg.norm(t-u)>tolerance):
            raise ValueError('Wyrównanie niejednoznaczne (symetryczne części). Porównaj bez wyrównania.')
    aligned=[describe(transform(p.shape,R,t),p.name,p.path,p.source) for p in b]
    info={'enabled':True,'anchor':a[i].name,'votes':votes,'anchors':len(pairs),
          'rotation_B_to_A':R.tolist(),'translation_B_to_A_mm':t.tolist()}
    if progress:progress(f'Wyrównano B do A: {votes}/{len(pairs)} wspólnych środków; baza: {a[i].name}')
    return aligned,info
