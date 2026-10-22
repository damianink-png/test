"""R11.29 conservative majority alignment for repeated CAD parts."""
from pathlib import Path
import os
root=Path(os.environ["DS_COMPARE_SOURCE"])
p=root/"dsac29/alignment.py"
s=p.read_text("utf8")
old="""    if not pairs:
        raise AlignmentUnavailable('Nie znaleziono jednoznacznych wspólnych części.')
    if len(pairs)==1 and (len(a)!=1 or len(b)!=1):
        raise AlignmentUnavailable('Jedna baza nie wystarcza do wyrównania wieloczęściowego złożenia.')"""
new="""    if not pairs or (len(pairs)==1 and (len(a)!=1 or len(b)!=1)):
        # ZW3D can supply many identical, anonymously named occurrences.
        # Use majority registration, with physical B-Rep proof.
        return _align_repeated_translation(a,b,tolerance,progress)"""
if s.count(old)!=1:raise RuntimeError("R11.29 alignment anchor mismatch")
s=s.replace(old,new,1)
s+="""

def _align_repeated_translation(a,b,tolerance,progress=None):
    \"\"\"Conservative world-BRep translation consensus for repeated shapes.

    Hypotheses from descriptors/positions are only candidates; every accepted
    hypothesis must be backed by OCC B-Rep world equality after relocation.
    \"\"\"
    from collections import Counter,defaultdict
    from math import ceil
    from .geometry import candidate
    if min(len(a),len(b))<2:
        raise AlignmentUnavailable('Za mało niezależnych elementów.')
    sig_a=defaultdict(list);sig_b=defaultdict(list)
    for i,p in enumerate(a):sig_a[signature(p)].append(i)
    for j,p in enumerate(b):sig_b[signature(p)].append(j)
    common=set(sig_a).intersection(sig_b)
    if not common:
        raise AlignmentUnavailable('Brak wspólnych charakterystyk brył.')
    def sample(ids,max_count=7):
        if len(ids)<=max_count:return ids
        return [ids[round(k*(len(ids)-1)/(max_count-1))] for k in range(max_count)]
    proposals={}
    for key in common:
        for i in sample(sig_a[key]):
            for j in sample(sig_b[key]):
                if not candidate(a[i],b[j],tolerance):continue
                shift=np.asarray(a[i].center-b[j].center,dtype=float)
                proposals[tuple(np.round(shift,4))]=shift
                if len(proposals)>=900:break
            if len(proposals)>=900:break
        if len(proposals)>=900:break
    if not proposals:
        raise AlignmentUnavailable('Nie uzyskano hipotez przemieszczenia.')
    step=max(tolerance/8.0,0.00001)
    def token(info,center):
        return (signature(info),)+tuple(np.round(np.asarray(center)/step).astype(int))
    reference=Counter(token(p,p.center) for p in a)
    ranked=[]
    for translation in proposals.values():
        shifted=Counter(token(part,part.center+translation) for part in b)
        votes=sum(min(q,shifted.get(key,0)) for key,q in reference.items())
        ranked.append((votes,tuple(float(x) for x in translation)))
    ranked.sort(key=lambda x:(-x[0],x[1]))
    candidates=[]
    for rawvotes,offset in ranked:
        if len(candidates)>=5:break
        if rawvotes<max(2,ceil(.6*min(len(a),len(b)))):break
        if any(np.linalg.norm(np.asarray(offset)-np.asarray(old[1]))<=tolerance/10 for old in candidates):continue
        candidates.append((rawvotes,offset))
    if not candidates:
        raise AlignmentUnavailable('Powtarzalne części nie tworzą większości zgodnej z jednym przesunięciem.')
    winners=[]
    for votes,offset in candidates:
        t=np.asarray(offset,dtype=float)
        aligned=[]
        for p in b:
            new=describe(transform(p.shape,np.eye(3),t),p.name,p.path,p.source)
            new.name_origin=p.name_origin
            aligned.append(new)
        by_sig=defaultdict(list)
        for i,part in enumerate(a):by_sig[signature(part)].append(i)
        accepted=0;seen=set()
        for j,new in enumerate(aligned):
            indices=by_sig.get(signature(new),[])
            for i in indices:
                if i in seen:continue
                if np.linalg.norm(a[i].center-new.center)>tolerance:continue
                if not candidate(a[i],new,tolerance):continue
                if equivalent_world(a[i],new,tolerance):
                    accepted+=1;seen.add(i);break
            if accepted>=20:break
        required=min(20,max(2,ceil(.60*min(len(a),len(b)))))
        if accepted>=required:winners.append((accepted,tuple(offset),aligned))
    if not winners:
        raise AlignmentUnavailable('Hipotezy przesunięcia nie przeszły potwierdzenia B-Rep.')
    if len(a)==len(b):
        centroid_shift=(np.mean([p.center for p in a],axis=0)
                        -np.mean([p.center for p in b],axis=0))
        winners.sort(key=lambda x:(-x[0],np.linalg.norm(np.asarray(x[1])-centroid_shift)))
    else:
        centroid_shift=None
        winners.sort(key=lambda x:-x[0])
    best_score,offset,aligned=winners[0]
    for score,other,_ in winners[1:]:
        if score!=best_score:break
        if np.linalg.norm(np.asarray(offset)-np.asarray(other))>tolerance:
            best_delta=(np.linalg.norm(np.asarray(offset)-centroid_shift)
                        if centroid_shift is not None else float('inf'))
            other_delta=(np.linalg.norm(np.asarray(other)-centroid_shift)
                         if centroid_shift is not None else float('inf'))
            if best_delta>other_delta*.5 or other_delta-best_delta<max(10*tolerance,0.5):
                raise AlignmentUnavailable('Wiele równorzędnych przesunięć; nie można bezpiecznie wybrać jednego.')
    if progress:
        progress(f'Wyrównanie powtarzalnych brył: {best_score} potwierdzonych dopasowań, przesunięcie {list(np.round(offset,3))} mm')
    return aligned,{'requested':True,'enabled':True,'status':'registered',
                    'method':'repeated_translation_consensus','votes':best_score,
                    'rotation_B_to_A':np.eye(3).tolist(),
                    'translation_B_to_A_mm':list(offset),
                    'coordinate_system':'B transformed into A before geometry matching and STEP export'}
"""
p.write_text(s,encoding="utf8")
print("R11.29 alignment: verified majority translation for assemblies with repeated CAD parts")
