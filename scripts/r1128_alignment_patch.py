"""R11.28: consensus-verified registration, pure translation for one- or
two-anchor models, and fail-closed export if requested alignment is ambiguous.
"""
import os
from pathlib import Path
root=Path(os.environ['DS_COMPARE_SOURCE'])
p=root/'dsac29/alignment.py'
code='''"""Conservative, validated rigid whole-assembly registration.

Only an explicitly requested alignment transforms B into A coordinates.
Pure translations can be established from two anchors or from a single
unique solid in a single-solid assembly; ambiguous multi-part transformations
raise AlignmentUnavailable. All hypotheses require B-Rep world verification.
"""
from collections import defaultdict
import numpy as np
from .geometry import equivalent_rigid,equivalent_world,transform,describe,signature

class AlignmentUnavailable(ValueError):
    """Not enough consistent, geometrically verified assembly anchors."""

def align_assembly(a,b,tolerance=0.01,progress=None):
    names_a=defaultdict(list);names_b=defaultdict(list)
    for i,part in enumerate(a):names_a[part.name].append(i)
    for j,part in enumerate(b):names_b[part.name].append(j)
    pairs=[(items[0],names_b[name][0]) for name,items in names_a.items()
           if len(items)==1 and len(names_b.get(name,()))==1]
    signatures_a=defaultdict(list);signatures_b=defaultdict(list)
    for i,p in enumerate(a):signatures_a[signature(p)].append(i)
    for j,p in enumerate(b):signatures_b[signature(p)].append(j)
    for key,ids in signatures_a.items():
        if len(ids)!=1 or len(signatures_b.get(key,()))!=1:continue
        pair=(ids[0],signatures_b[key][0])
        if pair not in pairs and not any(i==pair[0] or j==pair[1] for i,j in pairs):
            pairs.append(pair)
    verified=[]
    for i,j in pairs:
        if progress:progress(f'Wyrównanie: weryfikacja wspólnych baz {len(verified)+1}/{len(pairs)}')
        if equivalent_rigid(a[i],b[j],tolerance)[0]:
            verified.append((i,j))
    pairs=sorted(verified,key=lambda ij:-a[ij[0]].volume)
    if not pairs:
        raise AlignmentUnavailable('Nie znaleziono jednoznacznych wspólnych części.')
    if len(pairs)==1 and (len(a)!=1 or len(b)!=1):
        raise AlignmentUnavailable('Jedna baza nie wystarcza do wyrównania wieloczęściowego złożenia.')
    def score(R,t):
        supporting=[]
        for i,j in pairs:
            if np.linalg.norm(a[i].center-(R@b[j].center+t))>max(0.0001,tolerance):
                continue
            aligned=describe(transform(b[j].shape,R,t),b[j].name,b[j].path,b[j].source)
            if equivalent_world(a[i],aligned,tolerance):
                supporting.append((i,j))
        return supporting

    identity=np.eye(3)
    identity_votes=sum(equivalent_world(a[i],b[j],tolerance) for i,j in pairs)
    min_votes=1 if len(a)==len(b)==len(pairs)==1 else 2
    if identity_votes>=min_votes and identity_votes/len(pairs)>=0.6:
        if progress:progress('Wyrównanie: bazowy układ współrzędnych jest już zgodny.')
        return b,{'requested':True,'enabled':True,'status':'already_aligned',
                  'anchors':len(pairs),'votes':identity_votes,
                  'rotation_B_to_A':identity.tolist(),'translation_B_to_A_mm':[0.0,0.0,0.0]}

    candidates=[]
    # Pure translation needs neither three anchors nor non-collinear centroids.
    # A single anchor is accepted ONLY when each input contains one solid.
    for i,j in pairs[:16]:
        offset=np.asarray(a[i].center-b[j].center,dtype=float)
        candidates.append(('translation',identity,offset,i,j))
    if len(pairs)>=3:
        pa=np.array([a[i].center for i,j in pairs],dtype=float)
        pb=np.array([b[j].center for i,j in pairs],dtype=float)
        ca=pa.mean(axis=0);cb=pb.mean(axis=0)
        if np.linalg.matrix_rank(pb-cb,tol=max(tolerance,1.e-6))>=2:
            U,_,Vt=np.linalg.svd((pb-cb).T@(pa-ca))
            D=np.eye(3);D[-1,-1]=np.linalg.det(Vt.T@U.T)
            rotation=Vt.T@D@U.T;offset=ca-rotation@cb
            candidates.append(('rigid_kabsch',rotation,offset,pairs[0][0],pairs[0][1]))
        for i,j in pairs[:12]:
            same,rotation,offset=equivalent_rigid(a[i],b[j],tolerance)
            if same:candidates.append(('rigid_anchor',rotation,offset,i,j))
    if not candidates:
        raise AlignmentUnavailable('Nie uzyskano zgodnej transformacji B do A.')

    ranked=[]
    for method,R,t,i,j in candidates:
        supported=score(R,t)
        if len(supported)>=min_votes and len(supported)/len(pairs)>=0.6:
            ranked.append((len(supported),method,R,t,i,j))
    if not ranked:
        raise AlignmentUnavailable('Brak transformacji potwierdzonej przez większość wspólnych części.')
    ranked.sort(key=lambda value:(-value[0],0 if value[1]=='translation' else 1))
    votes,method,R,t,i,j=ranked[0]
    # Equal-score transforms affecting entire assembly differently are
    # dangerous. Do not quietly pick an arbitrary symmetric registration.
    for other_votes,_,Q,u,_,_ in ranked[1:]:
        if other_votes!=votes:break
        if not np.allclose(R,Q,atol=1e-6) or np.linalg.norm(t-u)>max(tolerance,1e-4):
            raise AlignmentUnavailable('Równorzędne sprzeczne transformacje; wyrównanie jest niejednoznaczne.')
    aligned=[]
    for original in b:
        p=describe(transform(original.shape,R,t),original.name,original.path,original.source)
        p.name_origin=original.name_origin
        aligned.append(p)
    # Verify original parts did not lose shape/count after applying transform.
    if len(aligned)!=len(b):
        raise RuntimeError('Niespójna liczba części po wyrównaniu.')
    info={'requested':True,'enabled':True,'status':'registered',
          'method':method,'votes':votes,'anchors':len(pairs),
          'rotation_B_to_A':R.tolist(),'translation_B_to_A_mm':t.tolist(),
          'coordinate_system':'B transformed into A coordinates before comparison and STEP export'}
    if progress:progress(f'Wyrównano B do A: {votes}/{len(pairs)} sprawdzonych baz; translacja [mm]: {np.round(t,3).tolist()}')
    return aligned,info
'''
p.write_text(code,encoding='utf8')
p=root/'dsac29/cli.py'
s=p.read_text('utf8')
old='''        except AlignmentUnavailable as exc:
            warning='Nie zastosowano wyrównania: '+str(exc)+' Porównano oryginalne położenia modeli.'
            alignment={'requested':True,'enabled':False,'warning':warning}
            if progress:progress('UWAGA: '+warning)'''
new='''        except AlignmentUnavailable as exc:
            # Never quietly compare in raw coordinates when the user requested
            # registration: this would produce a misleading color STEP.
            raise RuntimeError('Wyrównanie całego złożenia nie jest wiarygodne: '+str(exc)+
                ' Anulowano analizę bez eksportu błędnie zestawionego STEP. '
                'Wyłącz wyrównanie, jeśli chcesz celowo porównać oryginalne pozycje.') from exc'''
assert s.count(old)==1,('cli alignment anchor',s.count(old))
p.write_text(s.replace(old,new,1),encoding='utf8')
print('R11.28 alignment: verified translation from 1/2 anchors + geometry-backed consensus; no silent raw-coordinate fallback')
