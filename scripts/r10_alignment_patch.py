from pathlib import Path
p=Path(__file__).resolve().parents[1]/'source'/'dsac29'/'alignment.py'
s=p.read_text(encoding='utf-8')
def rep(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:90])
 s=s.replace(a,b,1)

rep("""    except AlignmentUnavailable:
        return _align_repeated_translation(a,b,tolerance,progress)""",
"""    except AlignmentUnavailable:
        try:
            return _align_repeated_translation(a,b,tolerance,progress)
        except AlignmentUnavailable as exc:
            return _align_sparse_translation(a,b,tolerance,progress,previous=exc)""")
rep("""    return _align_repeated_translation(a,b,tolerance,progress)

def _align_anchors""",
"""    try:
        return _align_repeated_translation(a,b,tolerance,progress)
    except AlignmentUnavailable as exc:
        return _align_sparse_translation(a,b,tolerance,progress,previous=exc)

def _align_anchors""")
rep("""    try:
        aligned,info=_align_anchors(a,b,tolerance,progress)""",
"""    # Large revised assemblies may have few unchanged parts. Check a
    # conservative partial world B-Rep consensus before expensive rigid
    # anchor trials. No transform is accepted on descriptors alone.
    if initial['ratio']<.60 and min(len(a),len(b))>=40:
        try:
            return _align_sparse_translation(a,b,tolerance,progress)
        except AlignmentUnavailable:
            pass
    try:
        aligned,info=_align_anchors(a,b,tolerance,progress)""")
s+=r'''

def _align_sparse_translation(a,b,tolerance,progress=None,previous=None):
    """Whole-frame translation from a PARTIAL, native-B-Rep-verified overlap.

    Never accept a candidate from names, mass or centers alone. Require
    many actual world-space OCC B-Rep equalities, improvement over CAD
    coordinates, and no similarly supported competing translation.
    """
    from collections import defaultdict
    from math import ceil
    from .geometry import candidate
    from .compare import _spatial_index,_nearby
    from .registration_gate import frame_support
    from types import SimpleNamespace
    pop=min(len(a),len(b))
    required=max(8,ceil(.15*pop))
    if pop<40:
        raise AlignmentUnavailable(str(previous or 'Za mało brył do częściowego wyrównania.'))
    sa=defaultdict(list);sb=defaultdict(list)
    for i,p in enumerate(a):sa[signature(p)].append(i)
    for j,p in enumerate(b):sb[signature(p)].append(j)
    common=sa.keys() & sb.keys()
    if not common:
        raise AlignmentUnavailable(str(previous or 'Brak wspólnych brył.'))
    hist=defaultdict(lambda:[0,None])
    def sample(ids,limit=13):
        if len(ids)<=limit:return ids
        return list(dict.fromkeys(ids[round(k*(len(ids)-1)/(limit-1))]
                                  for k in range(limit)))
    for key in sorted(common,key=lambda k:(len(sa[k])*len(sb[k]),str(k))):
        for i in sample(sa[key]):
            for j in sample(sb[key]):
                if not candidate(a[i],b[j],tolerance):continue
                shift=np.asarray(a[i].center-b[j].center,dtype=float)
                cell=tuple(int(round(float(v)/max(tolerance*.1,1.e-4))) for v in shift)
                entry=hist[cell];entry[0]+=1
                if entry[1] is None:entry[1]=shift
    if not hist:
        raise AlignmentUnavailable(str(previous or 'Brak hipotez przesunięcia.'))
    proposals=sorted(hist.values(),key=lambda val:-val[0])[:48]
    original=frame_support(a,b,tolerance,proofs=12)
    cell_size=max(tolerance,1.e-6)
    cells=_spatial_index(a,range(len(a)),cell_size)
    ranked=[]
    for _,translation in proposals:
        visited=set();pairs=[]
        for j,part in enumerate(b):
            center=part.center+translation
            for i in _nearby(cells,SimpleNamespace(center=center),cell_size):
                if i in visited or np.linalg.norm(a[i].center-center)>tolerance:continue
                if not candidate(a[i],part,tolerance):continue
                visited.add(i);pairs.append((i,j));break
        if len(pairs)>=required:ranked.append((len(pairs),translation,pairs))
    if not ranked:
        raise AlignmentUnavailable(str(previous or 'Za mało wspólnych detali do wyrównania.'))
    ranked.sort(key=lambda item:-item[0])
    if progress:
        progress(f'Wyrównanie częściowych rewizji: najlepsza hipoteza '
                 f'{ranked[0][0]}/{pop} brył, wymagane {required}.')
    winners=[]
    for coarse,offset,pairs in ranked[:12]:
        if len(winners)>=3 and coarse<winners[0][0]*.75:break
        verified=0
        for i,j in pairs:
            shifted=_relocate(b[j],np.eye(3),offset)
            if equivalent_world(a[i],shifted,tolerance):verified+=1
        if verified>=required:winners.append((verified,offset))
    if not winners:
        raise AlignmentUnavailable('Kandydaty przesunięcia nie przeszły kontroli B-Rep.')
    winners.sort(key=lambda item:-item[0])
    best,offset=winners[0]
    for other_score,other_offset in winners[1:]:
        if np.linalg.norm(offset-other_offset)<=tolerance:continue
        if other_score>=best-max(4,ceil(.08*best)):
            raise AlignmentUnavailable('Dwa przesunięcia mają podobne poparcie B-Rep.')
    aligned=[_relocate(p,np.eye(3),offset) for p in b]
    final=frame_support(a,aligned,tolerance,proofs=12)
    gain=max(3,ceil(.04*pop))
    if (final['count']<required or final['count']<original['count']+gain
            or final['checked']<2 or final['proofs']!=final['checked']):
        raise AlignmentUnavailable('Nie potwierdzono poprawy wyrównania całego złożenia.')
    info={'requested':True,'enabled':True,'status':'registered',
          'method':'partial_world_brep_consensus','votes':best,
          'verified_world_matches':final['count'],
          'previous_world_matches':original['count'],
          'rotation_B_to_A':np.eye(3).tolist(),
          'translation_B_to_A_mm':[float(v) for v in offset],
          'coordinate_system':'B transformed into A before matching and STEP export'}
    if progress:
        progress(f'Wyrównano częściowe rewizje: {best} potwierdzeń B-Rep, '
                 f'{original["count"]} → {final["count"]}, przesunięcie '
                 f'{np.round(offset,3).tolist()} mm.')
    return aligned,info
'''
p.write_text(s,encoding='utf-8')

p=Path(__file__).resolve().parents[1]/'source'/'dsac29'/'cli.py'
s=p.read_text(encoding='utf-8')
a="""                if (after['ratio']<.60 or after['count']<=initial['count'] or
                    after['proofs']!=after['checked']):"""
b="""                from math import ceil
                # Sparse consensus must prove improvement by native B-Rep,
                # and is never used if a similarly supported pose exists.
                sparse=proposal.get('method')=='partial_world_brep_consensus'
                minimum=max(8,ceil(.15*population)) if sparse else ceil(.60*population)
                gain=max(3,ceil(.04*population)) if sparse else 1
                if (after['count']<minimum or after['count']<initial['count']+gain or
                    after['checked']<2 or after['proofs']!=after['checked']):"""
assert s.count(a)==1
p.write_text(s.replace(a,b),encoding='utf-8')
print('R10 partial CAD frame patch PASS')
