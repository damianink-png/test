"""Conservative revision classification with cached part populations.

A relocated occurrence is MOVED only when the geometrically identical named
part has the same number of occurrences in both revisions. Unknown/changed
correspondences become separate old and new occurrences.
"""
from collections import defaultdict
from time import perf_counter
from .compare import Record
from .names import canonical, genuine_rename
from .geometry import candidate, equivalent_rigid


def classify_revisions(old, new, records, tolerance=0.01, progress=None, geometry_context=None, geometry_first=False):
    from .geometry_registry import GeometryRegistry
    geometry_context=geometry_context if geometry_context is not None else GeometryRegistry()
    by_a=defaultdict(list)
    by_b=defaultdict(list)
    for p in old:by_a[canonical(p.name)].append(p)
    for p in new:by_b[canonical(p.name)].append(p)

    # Hold OCP TShape handles alive: temporary wrappers can otherwise reuse ids.
    handles={id(p):p.shape.TShape() for p in old+new}
    verified={}; populations={}; comparisons=[0]; begin=perf_counter()
    # Reuse B-Rep proofs already obtained in the main matcher. Never repeat an
    # expensive rigid transform for exactly the same native shape definitions.
    for r in records:
        if (r.a_index is not None and r.b_index is not None and
            (r.status=='MOVED' or (r.status=='UNCERTAIN' and 'B-Rep zgodna' in r.confidence))):
            ha=id(handles[id(old[r.a_index])]);hb=id(handles[id(new[r.b_index])])
            verified[ha,hb]=True
            geometry_context.remember_equivalence(old[r.a_index],new[r.b_index],tolerance)

    def proof(ref, p):
        if not candidate(ref,p,tolerance):return False
        if ref.shape.IsPartner(p.shape):return True
        # Cache by shared native definition, NOT by occurrence: repeated STEP
        # instances must not trigger hundreds of equivalent_rigid Booleans.
        key=(id(handles[id(ref)]),id(handles[id(p)]))
        if key not in verified:
            comparisons[0]+=1
            if progress and comparisons[0]%8==0:
                progress(f'Weryfikacja liczby wystąpień: {comparisons[0]} różnych definicji B-Rep; {perf_counter()-begin:.1f} s')
            verified[key]=geometry_context.rigid_equivalent(ref,p,tolerance)
        return verified[key]

    def same_population(a_part,b_part):
        name=canonical(a_part.name)
        if not name or name!=canonical(b_part.name):return False
        key=(name,id(handles[id(a_part)]),id(handles[id(b_part)]))
        if key in populations:return populations[key]
        # Reject mismatched candidate counts *before* any expensive Booleans.
        # A candidate is only a cheap filter, never accepted as shape proof.
        ca=[p for p in by_a[name] if candidate(a_part,p,tolerance)]
        cb=[p for p in by_b[name] if candidate(a_part,p,tolerance)]
        if len(ca)!=len(cb) or not ca:
            populations[key]=False;return False
        # Native identical instances are common in assemblies. No extra B-Rep
        # testing is necessary for those; other definitions are verified once.
        total_a=sum(1 for p in ca if proof(a_part,p))
        total_b=sum(1 for p in cb if proof(a_part,p))
        result=total_a==total_b and total_a>0
        populations[key]=result
        return result

    from .repetition import repeated_ids
    repeated_a=repeated_ids(old,tolerance,geometry_context)
    repeated_b=repeated_ids(new,tolerance,geometry_context)
    output=[]
    if progress:progress(f'Po B-Rep: ustalanie przesuniętych części i liczby wystąpień ({len(records)} pozycji)...')
    for n,r in enumerate(records):
        if progress and n and n%50==0:
            progress(f'Po B-Rep: sklasyfikowano {n}/{len(records)} pozycji; dodatkowe testy {comparisons[0]}; {perf_counter()-begin:.1f} s')
        i,j=r.a_index,r.b_index
        # A heuristic pair of repeated components has no occurrence identity.
        # Keep real geometry failures visible; only split successful, inconclusive
        # heuristic pairings. Proven equal geometry still follows MOVED rules.
        if (i is not None and j is not None and
            (i in repeated_a or j in repeated_b) and
            (r.status=='CHANGED' or
             (r.status=='UNCERTAIN' and r.confidence=='Heurystyka — sprawdź parę' and
              'Błąd' not in r.note))):
            note='Powtarzająca się geometria; pominięto heurystyczne parowanie i Common'
            output.append(Record(i,None,'REMOVED',note,confidence='Rozdzielone rewizje'))
            output.append(Record(None,j,'ADDED',note,confidence='Rozdzielone rewizje'))
            continue
        if r.status=='UNCERTAIN' and 'B-Rep zgodna' not in r.confidence:

            output.append(r);continue
        if i is None:
            output.append(Record(None,j,'ADDED',r.note,confidence=r.confidence));continue
        if j is None:
            output.append(Record(i,None,'REMOVED',r.note,confidence=r.confidence));continue
        if r.status in ('SAME','RENAMED'):
            # Native B-Rep has already PROVEN geometry and world-space identity.
            # Supplier names are separate metadata and must never remove a
            # green geometry match from the unchanged count.
            renamed=genuine_rename(old[i],new[j])
            status='SAME' if geometry_first else ('RENAMED' if renamed else 'SAME')
            note=(('Różny zapis nazwy A→B: '+str(old[i].name)+' → '+str(new[j].name)+'; ') if renamed else '')+r.note
            output.append(Record(i,j,status,note,confidence=r.confidence,name_changed=renamed))
            continue
        if r.status=='CHANGED' and canonical(old[i].name) and canonical(old[i].name)==canonical(new[j].name):
            # Keep a uniquely assigned same-name revision pair. Detailed
            # geometry changes will be proven by native Boolean before export.
            output.append(Record(i,j,'CHANGED',r.note,r.distance_mm,
                                 r.delta_x,r.delta_y,r.delta_z,
                                 r.volume_delta_mm3,r.rotation_deg,r.confidence))
            continue
        if r.status in ('MOVED','UNCERTAIN'):
            proven=r.status=='MOVED' or 'B-Rep zgodna' in r.confidence
            try:population_ok=proven and same_population(old[i],new[j])
            except Exception as exc:
                output.append(Record(i,j,'UNCERTAIN','Błąd weryfikacji liczby wystąpień: '+str(exc),confidence='Wymaga sprawdzenia'));continue
            if population_ok:
                output.append(Record(i,j,'MOVED',
                    'Równa geometria i liczba wystąpień; inne położenie lub obrót',
                    r.distance_mm,r.delta_x,r.delta_y,r.delta_z,0.0,r.rotation_deg,
                    ('B-Rep; niejednoznaczna tożsamość wystąpienia — sprawdź parę' if r.status=='UNCERTAIN' else 'B-Rep; tożsamość wystąpienia wg pozycji')))
                continue
        # Geometric modifications or ambiguous matches are NOT MOVED.
        # They are represented as removed old + added new, not fake pairs.
        note='Zmiana geometrii, liczby wystąpień lub brak jednoznacznego odpowiednika'
        output.append(Record(i,None,'REMOVED',note,confidence='Rozdzielone rewizje'))
        output.append(Record(None,j,'ADDED',note,confidence='Rozdzielone rewizje'))
    output.sort(key=lambda r:(r.b_index is None,r.b_index if r.b_index is not None else r.a_index))
    assert all(r.status in ('SAME','RENAMED','CHANGED','MOVED','ADDED','REMOVED','UNCERTAIN') for r in output)
    assert len({r.a_index for r in output if r.a_index is not None})==len(old)
    assert len({r.b_index for r in output if r.b_index is not None})==len(new)
    if progress:progress(f'Po B-Rep: klasyfikacja ukończona w {perf_counter()-begin:.1f} s; dodatkowe testy: {comparisons[0]}.')
    return output
