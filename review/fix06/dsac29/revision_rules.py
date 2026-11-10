"""Conservative revision classification with cached part populations.

A relocated occurrence is MOVED only when the geometrically identical named
part has the same number of occurrences in both revisions. Unknown/changed
correspondences become separate old and new occurrences.
"""
from collections import defaultdict
from time import perf_counter
import numpy as np
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

    def eligible(ref,p):
        # Numerical descriptors cannot veto a completed original-boundary proof.
        # Unknown pairs retain the strict candidate filter and native verification.
        return ((geometry_first and geometry_context.has_rigid_proof(ref,p,tolerance))
                or candidate(ref,p,tolerance))

    def proof(ref, p):
        if geometry_first and geometry_context.has_rigid_proof(ref,p,tolerance):return True
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
        if not geometry_first and (not name or name!=canonical(b_part.name)):return False
        if geometry_first:name=None  # STEP-generated labels are not part identity.
        key=(name,id(handles[id(a_part)]),id(handles[id(b_part)]))
        if key in populations:return populations[key]
        # Reject mismatched candidate counts *before* any expensive Booleans.
        # A candidate is only a cheap filter, never accepted as shape proof.
        ca=[p for p in (old if geometry_first else by_a[name]) if eligible(a_part,p)]
        cb=[p for p in (new if geometry_first else by_b[name]) if eligible(a_part,p)]
        if len(ca)!=len(cb) or not ca:
            populations[key]=False;return False
        # Native identical instances are common in assemblies. No extra B-Rep
        # testing is necessary for those; other definitions are verified once.
        total_a=sum(1 for p in ca if proof(a_part,p))
        total_b=sum(1 for p in cb if proof(a_part,p))
        result=total_a==total_b and total_a>0
        populations[key]=result
        return result

    # Only inconclusive heuristic pairings may be split by the repeated-part
    # policy. Native failures and independently proven placements stay visible.
    from .repeated_geometry import repeated_ids
    heuristic=any(r.a_index is not None and r.b_index is not None and
                  r.status in ('CHANGED','UNCERTAIN') and
                  r.confidence=='Heurystyka — sprawdź parę' for r in records)
    repeated_a=repeated_ids(old,tolerance,geometry_context) if heuristic else set()
    repeated_b=repeated_ids(new,tolerance,geometry_context) if heuristic else set()
    output=[]
    if progress:progress(f'Po B-Rep: ustalanie przesuniętych części i liczby wystąpień ({len(records)} pozycji)...')
    for n,r in enumerate(records):
        if progress and n and n%50==0:
            progress(f'Po B-Rep: sklasyfikowano {n}/{len(records)} pozycji; dodatkowe testy {comparisons[0]}; {perf_counter()-begin:.1f} s')
        i,j=r.a_index,r.b_index
        if (i is not None and j is not None and
            r.status in ('CHANGED','UNCERTAIN') and
            r.confidence=='Heurystyka — sprawdź parę' and
            (i in repeated_a or j in repeated_b)):
            note='Powtarzająca się geometria; wyłączono automatyczne parowanie materiału'
            output.extend((Record(i,None,'REMOVED',note,confidence='Rozdzielone rewizje'),
                           Record(None,j,'ADDED',note,confidence='Rozdzielone rewizje')))
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
            # A completed rigid B-Rep proof of THIS particular A/B occurrence
            # survives a change of quantities in the family. The old policy
            # discarded even independently verified MOVED pairs when one copy
            # was removed or added elsewhere in the assembly. Unknown/heuristic
            # correspondences do NOT receive this exception.
            independently_moved=(r.status=='MOVED' and proven)
            if population_ok or independently_moved:
                from .compare import _location_matrix
                left,right=old[i],new[j]
                # Compare actual world geometry envelopes FIRST. For baked
                # STEP coordinates, two different shapes can both have an
                # identity TopLoc, yet be hundreds of millimeters apart.
                from .geometry import _precise_world_bounds
                bounds_a=np.asarray(_precise_world_bounds(left.shape),dtype=float)
                bounds_b=np.asarray(_precise_world_bounds(right.shape),dtype=float)
                near_world=bool(np.all(np.isfinite(bounds_a)) and
                    np.all(np.isfinite(bounds_b)) and
                    # The approximate 4*tolerance envelope previously hid
                    # real 0.04 mm moves at tolerance=0.01 mm. Only an
                    # envelope within the actual CAD tolerance can be a
                    # possible stationary re-export: larger changes are
                    # genuine candidate movements after rigid native proof.
                    np.max(np.abs(bounds_a-bounds_b))<=max(1e-8,min(.01,float(tolerance))))
                same_placement=bool(near_world and np.allclose(
                    _location_matrix(left),_location_matrix(right),
                    rtol=0,atol=max(1e-8,min(float(tolerance),0.01)*.25)))
                if same_placement:
                    output.append(Record(i,j,'SAME',
                        'Tożsama geometria i położenie: skorygowano pozorny ruch',
                        confidence='B-Rep, to samo położenie i obwiednia'))
                    continue
                if near_world:
                    from .native_guard import guarded_registered_world,NativeGeometryFailure
                    try:
                        if guarded_registered_world(left,right,tolerance,
                                                    timeout_s=15,allow_boolean=False):
                            output.append(Record(i,j,'SAME',
                                'Zweryfikowano identyczny materiał w oryginalnej pozycji',
                                confidence='Pełny B-Rep w świecie'))
                            continue
                    except NativeGeometryFailure as exc:
                        output.append(Record(i,j,'UNCERTAIN',
                            'Nie ukończono weryfikacji pozornego ruchu B-Rep: '+str(exc),
                            confidence='Niepotwierdzona lokalizacja'))
                        continue
                    # An inconclusive fast world test is not positive proof
                    # of a move. It might be a different STEP face partition.
                    output.append(Record(i,j,'UNCERTAIN',
                        'Ta sama obwiednia w świecie, lecz różny zapis B-Rep; '
                        'nie potwierdzono rzeczywistego ruchu',
                        confidence='Wymaga niezależnego dowodu'))
                    continue
                note=('Pełny B-Rep; ruch po zmianie liczby wystąpień w rodzinie'
                      if independently_moved and not population_ok else
                      'Równa geometria i liczba wystąpień; inne położenie lub obrót')
                output.append(Record(i,j,'MOVED',note,
                    r.distance_mm,r.delta_x,r.delta_y,r.delta_z,0.0,r.rotation_deg,
                    ('B-Rep; tożsamość wystąpienia może być niejednoznaczna'
                     if independently_moved and not population_ok else
                     ('B-Rep; niejednoznaczna tożsamość wystąpienia — sprawdź parę'
                      if r.status=='UNCERTAIN' else 'B-Rep; tożsamość wystąpienia wg pozycji'))))
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
