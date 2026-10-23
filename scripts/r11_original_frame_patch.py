"""R11: normal CAD world frame FIRST; expensive registration only on failed preflight.
Apply after R8+R9+R10 patches. Fails on missing anchors.
"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'source'
p=root/'dsac29'/'registration_gate.py'
s=p.read_text(encoding='utf8')
assert 'def original_frame_fastpath(' not in s
s += '''

def original_frame_fastpath(a,b,tolerance,initial=None,progress=None):
    """Return True only if proven original CAD-frame matches justify skipping registration.

    A B-Rep-verified subset is sufficient when there is no alternative
    whole-assembly translation supported by the existing CAD descriptors.
    Descriptor votes are a negative filter ONLY; any transform still needs
    native world-space B-Rep proof and explicit user approval.
    """
    from collections import defaultdict,Counter
    from math import ceil
    from .compare import _spatial_index,_nearby
    from types import SimpleNamespace
    if initial is None:initial=frame_support(a,b,tolerance,proofs=8)
    population=min(len(a),len(b))
    if population==0:return False,'Brak brył'
    required=min(population,max(2,ceil(.35*population)))
    if (initial['count']<required or initial['checked']<min(2,population)
            or initial['proofs']!=initial['checked']):
        return False,f'Potwierdzono tylko {initial["count"]}/{population} pozycji'

    # A periodic assembly shifted by one pitch may overlap n-1 of n solids.
    # Estimate candidate shifts from centroids of equal-cardinality shape
    # cohorts (not the global centroid distorted by changed definitions).
    sig_a=defaultdict(list);sig_b=defaultdict(list)
    for i,part in enumerate(a):sig_a[signature(part)].append(i)
    for i,part in enumerate(b):sig_b[signature(part)].append(i)
    possible=Counter();representatives={}
    threshold=max(.01,tolerance)
    for key in sig_a.keys() & sig_b.keys():
        ia,ib=sig_a[key],sig_b[key]
        if len(ia)!=len(ib):continue
        offset=(np.mean([a[i].center for i in ia],axis=0)
                -np.mean([b[i].center for i in ib],axis=0))
        if np.linalg.norm(offset)<=tolerance:continue
        k=tuple(int(round(float(c)/threshold)) for c in offset)
        possible[k]+=len(ia)
        representatives[k]=offset
    if possible:
        cell_size=max(tolerance,1.e-6)
        idx=_spatial_index(a,range(len(a)),cell_size)
        for key,weight in possible.most_common(8):
            if weight<max(2,int(.04*population)):continue
            offset=representatives[key]
            used=set();votes=0
            for part in b:
                c=part.center+offset
                for i in _nearby(idx,SimpleNamespace(center=c),cell_size):
                    if i in used or np.linalg.norm(a[i].center-c)>tolerance:
                        continue
                    if signature(a[i])!=signature(part):continue
                    if not candidate(a[i],part,tolerance):continue
                    used.add(i);votes+=1;break
            if votes>initial['count']:
                if progress:progress(
                    f'Wstępna analiza: możliwe lepsze przesunięcie '
                    f'({votes} zamiast {initial["count"]} brył); weryfikacja B-Rep.')
                return False,'Podejrzenie globalnego przesunięcia'
    if progress:progress(
        f'Wstępna analiza: potwierdzono {initial["count"]}/{population} brył '
        'w obecnym układzie CAD; pomijam szukanie przesunięcia.')
    return True,'Potwierdzony oryginalny układ CAD, brak lepszej transformacji'
'''
p.write_text(s,encoding='utf8')

p=root/'dsac29'/'cli.py'
s=p.read_text(encoding='utf8')
def replace_once(old,new):
 global s
 n=s.count(old)
 if n!=1:raise RuntimeError(f'R11 anchor found {n} times: {old[:100]!r}')
 s=s.replace(old,new,1)
replace_once(
"""    alignment={'requested':bool(align or auto_align),'enabled':False}
    (Path(output)/'OSTRZEZENIA.txt').unlink(missing_ok=True)""",
"""    alignment={'requested':bool(align or auto_align),'enabled':False}
    alignment_started=perf_counter()
    (Path(output)/'OSTRZEZENIA.txt').unlink(missing_ok=True)""")
replace_once(
"""        from .registration_gate import frame_support
        initial=frame_support(a,b,tolerance)
        # Partial overlap can be a whole periodic assembly shifted by one pitch.
        # Only full overlap can skip searching for a better global frame.
        if (initial['ratio']>=1.0 and initial['proofs']==initial['checked']
            and initial['checked']>=min(2,min(len(a),len(b)))):
            alignment.update(enabled=False,status='already_aligned',
                             reason='Potwierdzono część wspólnych brył w oryginalnym układzie A/B.')
            if progress:progress('Wykrywanie położenia: modele mają wspólny układ odniesienia; bez przesuwania.')""",
"""        from .registration_gate import frame_support,original_frame_fastpath
        if progress:progress('Wstępne porównanie w oryginalnym układzie CAD (bez wyrównania)…')
        initial=frame_support(a,b,tolerance,proofs=8)
        world_ok,world_reason=original_frame_fastpath(a,b,tolerance,initial,progress)
        if world_ok:
            alignment.update(enabled=False,status='already_aligned',
                             method='original_cad_frame_preflight',
                             verified_world_parts=initial['count'],
                             checked_brep=initial['checked'],
                             reason=world_reason)""")
replace_once(
"""    # One shared, strictly in-memory geometry registry for matching and BOM.
    from .geometry_registry import GeometryRegistry""",
"""    alignment_s=perf_counter()-alignment_started
    # One shared, strictly in-memory geometry registry for matching and BOM.
    from .geometry_registry import GeometryRegistry""")
replace_once(
"""'parallel_worker_import_s':import_parallel_worker_s,'matching_and_classification_s':matching_s,""",
"""'parallel_worker_import_s':import_parallel_worker_s,'alignment_preflight_and_optional_registration_s':alignment_s,'alignment_status':alignment.get('status','not_requested'),'matching_and_classification_s':matching_s,""")
p.write_text(s,encoding='utf8')
(root/'R11_ZMIANY.txt').write_text(
    'DS Compare 1.0 R11\n'
    '- Po imporcie sprawdza B-Rep w obecnym położeniu (bez wyrównywania).\n'
    '- Pomija kosztowne wyrównanie, jeśli obecny układ CAD jest wiarygodny.\n'
    '- Powtarzalny układ przesunięty o rozstaw nadal uruchamia wyrównanie.\n'
    '- Wyrównanie wykrytego przesunięcia nadal wymaga potwierdzenia.\n'
    '- Dodano czas tego etapu do CZASY_ANALIZY.json.\n',
    encoding='utf8')
print('R11 fast-original-frame patch PASS')
