"""Conservative 1:1 matching with actual B-Rep Boolean tests.

Only B-Rep proven matches can be green. Failures/ambiguities are NOT reported
as matches. The tool compares STEP-exported solids, not editable ZW3D features.
"""
from dataclasses import dataclass
from typing import Optional
from bisect import bisect_left, bisect_right
from collections import defaultdict
from itertools import product
from math import floor
from time import perf_counter
import numpy as np
from .names import canonical,genuine_rename
from .geometry import SolidInfo, candidate, equivalent_world, equivalent_rigid, dist,close
from . import trace_r22 as trace
from .native_guard import NativeGeometryFailure,guarded_world_reexport


class Cancelled(RuntimeError): pass

class ShiftDetected(RuntimeError):
    """Early exit after world-match phase: skip expensive rigid pairing."""
    def __init__(self,proposal):
        super().__init__('Wstępna analiza wykryła przesunięcie całego złożenia')
        self.proposal=proposal



@dataclass
class Record:
    a_index: Optional[int]
    b_index: Optional[int]
    status: str
    note: str
    distance_mm: Optional[float] = None
    delta_x: Optional[float] = None
    delta_y: Optional[float] = None
    delta_z: Optional[float] = None
    volume_delta_mm3: Optional[float] = None
    rotation_deg: Optional[float] = None
    confidence: str = "B-Rep"
    # Name differences are orthogonal to verified B-Rep geometry.
    # Set on geometry-identical revision records to preserve supplier labels.
    name_changed: bool = False


def _normalized_name(s):
    return canonical(s)


class _VolumeIndex:
    """Range lookup, conservative wrt geometry.candidate(). Never skips possible matches."""
    def __init__(self, objects, ids):
        self.sorted = sorted((objects[j].volume, j) for j in ids)
        self.values = [v for v, _ in self.sorted]

    def query(self, volume, tolerance):
        # Same absolute/relative tolerance as close() in geometry.candidate.
        abs_tol = max(tolerance ** 3, 1e-5)
        rel = 1e-7
        margin = max(abs_tol, rel * max(volume, abs_tol) / (1.0 - rel)) * 1.001 + 1e-10
        left = bisect_left(self.values, volume - margin)
        right = bisect_right(self.values, volume + margin)
        return (self.sorted[k][1] for k in range(left, right))


def _cell(s, size):
    return tuple(floor(float(q) / size) for q in s.center)


def _spatial_index(objects, ids, size):
    cells = defaultdict(list)
    for j in ids:
        cells[_cell(objects[j], size)].append(j)
    return cells


def _nearby(cells, part, size):
    ix, iy, iz = _cell(part, size)
    for dx, dy, dz in product((-1, 0, 1), repeat=3):
        yield from cells.get((ix + dx, iy + dy, iz + dz), ())


def _topology_id(s: SolidInfo):
    """TShape identity ignores occurrence placement, but not geometry.

    It is only a memoization key. A positive cached B-Rep check must exist
    between two different TShape identities before recycling its result.
    """
    return hash(s.shape.TShape())


def _location_matrix(s: SolidInfo):
    t = s.shape.Location().Transformation()
    return np.array([[t.Value(i,j) for j in range(1,5)] for i in range(1,4)],dtype=float)


def _relative_location_is_same(s, ref_a, t, ref_b, tolerance):
    """After proven world equality of two anchors, prove equality of moved
    instances of their respective identical TopoDS TShapes via placement.
    """
    ma=_location_matrix(s); ar=_location_matrix(ref_a)
    mb=_location_matrix(t); br=_location_matrix(ref_b)
    # Relative affine rigid transforms in world coordinates.
    ra=ma[:,:3] @ ar[:,:3].T
    rb=mb[:,:3] @ br[:,:3].T
    ta=ma[:,3]-ra @ ar[:,3]
    tb=mb[:,3]-rb @ br[:,3]
    return bool(np.allclose(ra,rb,rtol=0,atol=1e-9) and
                np.linalg.norm(ta-tb)<=min(tolerance*0.1,1e-5))


def compare(a: list[SolidInfo], b: list[SolidInfo], tolerance:float=0.01,
            progress=None,cancelled=None,max_checks:int=15000,revision_only:bool=False,
            exact_serialization:bool=False,geometry_context=None,stage1_check=None,step_reexport_tolerance:bool=False,certified_pairs=()) -> list[Record]:
    """Deterministic conservative matching. Cancels between expensive B-Rep ops."""
    if tolerance<=0 or tolerance>1: raise ValueError('Tolerancja B-Rep musi być w zakresie (0, 1] mm')
    if a is b:
        # The same imported object array, reused ONLY after a full input file
        # SHA-256 comparison, needs no geometric comparison at all. This is an
        # exact proof, not a probabilistic fingerprint of a CAD shape.
        if progress:progress(f'R11: {len(a)} identycznych wystąpień; bez testów B-Rep.')
        return [Record(i,i,'SAME','Ten sam źródłowy STEP (SHA-256); niezmieniona geometria, nazwy i położenia',confidence='Identyczna zawartość STEP') for i in range(len(a))]
    from .step_reexport_tolerance import coarse_candidate,reexport_equivalent_world,search_radius,world_candidate
    free_a=set(range(len(a))); free_b=set(range(len(b)))
    norm_a=[_normalized_name(p.name) for p in a]
    norm_b=[_normalized_name(p.name) for p in b]
    out=[]; checks=0
    for i,j in certified_pairs:
        if i not in free_a or j not in free_b:raise ValueError('Nieprawidłowa mapa potwierdzonych par')
        if dist(a[i],b[j])>search_radius(tolerance):raise ValueError('Potwierdzone pary nie pasują do zastosowanego układu')
        out.append(Record(i,j,'SAME','Zapisany dowód B-Rep po wyrównaniu',name_changed=genuine_rename(a[i],b[j])))
        free_a.remove(i);free_b.remove(j)
    # Native IsPartner() identity, shared by matching and exact BOM.
    from .geometry_registry import GeometryRegistry
    geometry_context = geometry_context if geometry_context is not None else GeometryRegistry()
    trace.mark('signature_cache','BEGIN',solids_a=len(a),solids_b=len(b))
    group_a=[geometry_context.definition(s) for s in a]
    group_b=[geometry_context.definition(s) for s in b]
    trace.mark('signature_cache','END',definitions_a=len(set(group_a)),definitions_b=len(set(group_b)))
    # Caches only PROVEN geometry equivalence for STEP instances sharing a
    # native TShape (the usual case for many repeated assembly components).
    world_anchors = {}
    congruent_groups = set()
    # Seed both placement-aware and rigid definition caches, not only records.
    # A later occurrence may use a proven definition in another placement.
    for i,j in certified_pairs:
        pair=(group_a[i],group_b[j])
        world_anchors.setdefault(pair,(i,j))
        congruent_groups.add(pair)
        geometry_context.remember_equivalence(a[i],b[j],tolerance)
    # A byte-for-byte identical neutral-location B-Rep serialization proves
    # equivalence of a native definition. Hashes are evaluated lazily ONCE per
    # TShape group, never once per occurrence. Inconclusive hashes still use
    # the original Boolean verification; a numerical signature is never proof.
    def exact_same_definition(s,t,ga,gb):
        return ga == gb or geometry_context.same_definition(s,t)
    rigid_anchors = {}
    failed_a=set();failed_b=set()
    failed_groups = set()
    memo_hits = 0
    trace.mark('world_matching','BEGIN',certified=len(certified_pairs))
    if progress:progress('Etap 1/3: sprawdzanie identycznych brył w tym samym miejscu')
    # Repeated occurrences matched 1:1, prioritizing the same name at same world position.
    started = perf_counter()
    broad_world_lookup=len(a)>=600
    lookup_radius=search_radius(tolerance) if broad_world_lookup else tolerance
    cells = _spatial_index(b, free_b, lookup_radius)
    # Match exact names first GLOBALLY: repeated and overlapping occurrences
    # must not consume a counterpart that has an exact-name match elsewhere.
    for names_equal in (True, False):
        for i, s in enumerate(a):
            if i not in free_a: continue
            if cancelled and cancelled(): raise Cancelled('Przerwano analizę')
            js = [j for j in _nearby(cells, s, lookup_radius)
                  if j in free_b
                  and (norm_a[i] == norm_b[j]) == names_equal
                  and dist(s, b[j]) <= lookup_radius and
                  (candidate(s,b[j],tolerance) or
                   coarse_candidate(s,b[j],tolerance) or
                   (broad_world_lookup and world_candidate(s,b[j],tolerance)))]
            js.sort(key=lambda j:(dist(s,b[j]),abs(s.volume-b[j].volume),j))
            for j in js:
                gs, gt = group_a[i], group_b[j]
                anchor = world_anchors.get((gs,gt))
                if anchor and _relative_location_is_same(s,a[anchor[0]],b[j],b[anchor[1]],tolerance):
                    same = True
                    memo_hits += 1
                elif s.shape.IsSame(b[j].shape):
                    same = True
                    memo_hits += 1
                elif exact_serialization and not step_reexport_tolerance and exact_same_definition(s,b[j],gs,gt) and np.allclose(
                        _location_matrix(s),_location_matrix(b[j]),rtol=0,atol=1e-9):
                    # Same exact local B-Rep and identical assembly placement.
                    same = True
                    memo_hits += 1
                else:
                    if checks >= max_checks: raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')
                    checks += 1
                    try:
                        # In the verified STEP re-export registration branch,
                        # check the CAD-face tolerance before OCC Common: two
                        # coincident, separately serialized curved faces can
                        # make OCC Common hang or falsely return zero volume.
                        # A registered large STEP frame may contain faces
                        # where in-process OCC Common stalls >100s or crashes.
                        # Use a bounded child for the residual pairs. Timeout
                        # is an INCOMPLETE proof, never a positive equality.
                        large_registered = len(a)>=600 and bool(certified_pairs)
                        if large_registered:
                            same=trace.brep_call('registered_world_guarded',i,j,
                                guarded_world_reexport,s,b[j],tolerance)
                        elif step_reexport_tolerance or not candidate(s,b[j],tolerance):
                            same=trace.brep_call('reexport_world',i,j,(guarded_world_reexport if len(a)>=600 else reexport_equivalent_world),s,b[j],tolerance)
                        else:
                            same=trace.brep_call('equivalent_world',i,j,equivalent_world,s,b[j],tolerance)
                            if not same and coarse_candidate(s,b[j],tolerance):
                                same=trace.brep_call('reexport_world_fallback',i,j,(guarded_world_reexport if len(a)>=600 else reexport_equivalent_world),s,b[j],tolerance)
                    except NativeGeometryFailure:
                        raise
                    except Exception as exc:
                        failed_a.add(i);failed_b.add(j)
                        if progress: progress(f'B-Rep test błędny {i}/{j}: {exc}')
                        continue
                if same:
                    geometry_context.remember_equivalence(s,b[j],tolerance)
                    world_anchors.setdefault((gs,gt),(i,j))
                    congruent_groups.add((gs,gt))
                    renamed = genuine_rename(s,b[j])
                    out.append(Record(i,j,'RENAMED' if renamed else 'SAME',
                        ('Nazwa: '+s.name+' → '+b[j].name) if renamed else ('B-Rep: zgodne w położeniu; nazwy eksportowe: '+s.name+' / '+b[j].name if s.name!=b[j].name else 'B-Rep: zgodne w położeniu')))
                    free_a.remove(i); free_b.remove(j)
                    break
                # No match; continue searching the next candidate.
            if progress and (i+1)%25 == 0:
                progress(f'Etap zgodności: {i+1}/{len(a)}; B-Rep: {checks}; pamięć: {memo_hits}; {perf_counter()-started:.1f}s')
    trace.mark('world_matching','END',matches=len(out),remaining_a=len(free_a),remaining_b=len(free_b),native_checks=checks)
    if stage1_check is not None:
        if cancelled and cancelled():raise Cancelled('Przerwano analizę')
        proposal=stage1_check(out,frozenset(free_a),frozenset(free_b))
        if proposal is not None:
            raise ShiftDetected(proposal)
    trace.mark('rigid_candidates','BEGIN',remaining_a=len(free_a),remaining_b=len(free_b))
    if progress:progress(f'B-Rep zgodne: {len(out)}; etap 2/3: przesunięte i obrócone')
    # Geometric equivalence under proper rotation + translation, independent of names.
    # Lazy candidate generation per unmatched A occurrence avoids O(N*M) memory.
    volume_index = _VolumeIndex(b, free_b)
    rigid_edges={}
    placements={}
    def placement(part):
        key=id(part)
        if key not in placements:placements[key]=_location_matrix(part)
        return placements[key]
    def matched_rotation(i,j):
        s,t=a[i],b[j];pair=(group_a[i],group_b[j])
        if pair in rigid_anchors:
            ai,bj,rr=rigid_anchors[pair]
            if (i,j)==(ai,bj):return rr
            return (placement(a[ai])[:,:3] @ placement(s)[:,:3].T).T @ rr @ (placement(b[bj])[:,:3] @ placement(t)[:,:3].T)
        if s.shape.IsPartner(t.shape) or (exact_serialization and exact_same_definition(s,t,*pair)):
            return placement(s)[:,:3] @ placement(t)[:,:3].T
        if pair in world_anchors:
            ai,bj=world_anchors[pair]
            return placement(s)[:,:3] @ placement(a[ai])[:,:3].T @ placement(b[bj])[:,:3] @ placement(t)[:,:3].T
        return None
    centers_b=np.asarray([p.center for p in b])
    candidate_cache={}
    def rigid_candidate(i,j):
        key=(group_a[i],group_b[j])
        if key not in candidate_cache:candidate_cache[key]=candidate(a[i],b[j],tolerance)
        return candidate_cache[key]
    # Large registered frames may leave complex re-exported CAD solids that
    # crash inside native rigid Boolean operations. Isolate ONLY this risky
    # stage; a crash must fail the entire job, never become a green match.
    use_native_guard = bool(len(a)>=600 and len(certified_pairs)>=max(100,int(len(a)*.40)))
    native_guard_started = perf_counter()
    native_guard_budget_s = 240.0
    for names_equal in (True, False):
        for idx,i in enumerate(sorted(free_a)):
            if i not in free_a:continue
            if cancelled and cancelled(): raise Cancelled('Przerwano analizę')
            s = a[i]
            # In a verified STEP frame, volume/area are search filters only.
            # A native CAD pose plus a complete original-boundary proof may
            # confirm moved re-exports rejected by strict integrated moments.
            lookup=(sorted(free_b) if use_native_guard else volume_index.query(s.volume,tolerance))
            js = [j for j in lookup
                  if j in free_b
                  and (norm_a[i] == norm_b[j]) == names_equal
                  and (rigid_candidate(i,j) or (use_native_guard and world_candidate(s,b[j],tolerance)))]
            distances=dict(zip(js,np.linalg.norm(centers_b[js]-s.center,axis=1))) if js else {}
            js.sort(key=lambda j:(distances[j],j))
            for j in js:
                ga,gb=group_a[i],group_b[j]
                pair=(ga,gb)
                if pair in congruent_groups or s.shape.IsPartner(b[j].shape) or (exact_serialization and exact_same_definition(s,b[j],ga,gb)):
                    match=True;memo_hits+=1
                elif pair in failed_groups:
                    match=False;memo_hits+=1
                else:
                    if checks>=max_checks:raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')
                    checks+=1
                    try:
                        if use_native_guard:
                            if perf_counter()-native_guard_started>native_guard_budget_s:
                                raise NativeGeometryFailure('Budżet izolowanych porównań B-Rep wyczerpany; analiza niekompletna')
                            from .native_guard import guarded_rigid
                            match,rotation,_=trace.brep_call('equivalent_rigid_guarded',i,j,guarded_rigid,s,b[j],tolerance,registered_reexport=True)
                        else:
                            match,rotation,_=trace.brep_call('equivalent_rigid',i,j,equivalent_rigid,s,b[j],tolerance)
                    except NativeGeometryFailure:
                        raise
                    except Exception as exc:
                        failed_a.add(i);failed_b.add(j)
                        if progress:progress(f'Test ustawienia {i}/{j}: {exc}')
                        continue
                    geometry_context.remember_equivalence(s,b[j],tolerance,match)
                    if match:
                        congruent_groups.add(pair);rigid_anchors[pair]=(i,j,rotation)
                    else:failed_groups.add(pair)
                if match:
                    # Geometry proof was already shared on the first check.
                    if pair not in congruent_groups:
                        geometry_context.remember_equivalence(s,b[j],tolerance)
                        congruent_groups.add(pair)
                    rigid_edges[i,j]=(float(distances[j]),not names_equal)
            if progress and (idx+1)%100 == 0:
                progress(f'Etap transformacji: {idx+1}/{len(a)}; B-Rep: {checks}; pamięć: {memo_hits}; {perf_counter()-started:.1f}s')
    trace.mark('rigid_candidates','END',candidate_edges=len(rigid_edges),native_checks=checks,memo_hits=memo_hits)
    from .assignment import assign
    scale=max((d for d,n in rigid_edges.values()),default=1.) or 1.
    costs={pair:0.85*d/scale+0.15*renamed for pair,(d,renamed) in rigid_edges.items()}
    # Free the redundant edge values before allocating the assignment matrix.
    del rigid_edges
    for i,j,ambiguous,gap in assign(costs):
        s,t=a[i],b[j];d=t.center-s.center
        rotation=matched_rotation(i,j)
        remark='Ta sama bryła B-Rep, inne ustawienie/pozycja'
        if genuine_rename(s,t):remark+='; zmiana nazwy: '+s.name+' → '+t.name
        angle=None if rotation is None else float(np.degrees(np.arccos(np.clip((np.trace(rotation)-1)/2,-1,1))))
        if angle is not None:remark+=f'; obrót dopasowania: {angle:.3f}° (symetria może dać równoważne ustawienie)'
        record=Record(i,j,'MOVED',remark,float(np.linalg.norm(d)),*map(float,d),0.0,angle)
        if ambiguous:
            record.status='UNCERTAIN'
            record.confidence='Geometria B-Rep zgodna; tożsamość wystąpienia niepewna'
            record.note+='; równoważne lub niezweryfikowane globalnie przypisanie wystąpień'
        else:
            record.note+='; globalny dobór par według położenia i nazwy'
            record.confidence='B-Rep; przypisanie wystąpienia heurystyczne'
        out.append(record);free_a.remove(i);free_b.remove(j)
    if revision_only:
        trace.mark('revision_only_classification','BEGIN',remaining_a=len(free_a),remaining_b=len(free_b))
        for i in sorted(free_a):
            out.append(Record(i,None,'UNCERTAIN' if i in failed_a else 'REMOVED',
                'Błąd testu B-Rep — nie rozstrzygnięto' if i in failed_a else 'Brak zgodnego odpowiednika w B'))
        for j in sorted(free_b):
            out.append(Record(None,j,'UNCERTAIN' if j in failed_b else 'ADDED',
                'Błąd testu B-Rep — nie rozstrzygnięto' if j in failed_b else 'Brak zgodnego odpowiednika w A'))
        out.sort(key=lambda r:(r.b_index is None,r.b_index if r.b_index is not None else r.a_index))
        trace.mark('revision_only_classification','END',records=len(out),checks=checks,memo_hits=memo_hits)
        if progress:progress(f'Porównanie rewizji: {checks} testów B-Rep; trafień pamięci {memo_hits}; pominięto zbędne parowanie zmienionej geometrii.')
        return out
    if progress:progress(f'Dopasowano {len(out)}; etap 3/3: zmienione / dodane / usunięte')
    # Conservative pairing for DIFFERENT geometry. Require close position and a strong
    # semantic signal (same name) or very close center / similar bounding envelope.
    potential=[];overlap_pairs={};overlap_checks=0
    # Automatic overlap is restricted to simple solids. Complex imported parts
    # retain conservative classification; detailed cuts remain user-triggered.
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    def simple_shape(shape):
        ex=TopExp_Explorer(shape,TopAbs_FACE);n=0
        while ex.More():
            n+=1
            if n>24:return False
            ex.Next()
        return True
    simple_a={i:simple_shape(a[i].shape) for i in free_a}
    simple_b={j:simple_shape(b[j].shape) for j in free_b}
    by_name=defaultdict(list)
    for j in free_b:
        by_name[norm_b[j]].append(j)
    # Only inspect all B occurrences sharing a name or within 2*tolerance
    # of the centroid. This preserves the original heuristics without O(A*B)
    # Python-level distance evaluations for dissimilar parts.
    uncertain_cell=max(2*tolerance,1.)
    uncertain_cells=_spatial_index(b,free_b,uncertain_cell)
    x_index=sorted((float(b[j].center[0]),j) for j in free_b)
    x_values=[x for x,j in x_index]
    for i in free_a:
        s=a[i]
        candidates=set(by_name.get(norm_a[i],()))
        candidates.update(_nearby(uncertain_cells,s,uncertain_cell))
        # Only nearby leftovers; never do a full Boolean cross-product.
        radius=max(2.,max(s.bbox)*0.08)
        lo=bisect_left(x_values,s.center[0]-radius);hi=bisect_right(x_values,s.center[0]+radius)
        candidates.update(j for _,j in x_index[lo:hi] if dist(s,b[j])<=radius)
        for j in candidates:
            t=b[j]
            near=dist(s,t)
            vol_ratio=abs(s.volume-t.volume)/max(s.volume,t.volume)
            bbox_delta=np.linalg.norm(np.array(s.bbox)-np.array(t.bbox))
            same_name=bool(norm_a[i]) and norm_a[i]==norm_b[j]
            if not (vol_ratio<0.45 and bbox_delta<max(50.,sum(s.bbox)*0.25)):
                continue
            if same_name and near<max(250.,sum(s.bbox)*0.75):
                score=(0,near,vol_ratio,i,j);potential.append((score,i,j,'CHANGED'))
            elif (near<=max(2.,max(s.bbox)*0.08) and vol_ratio<0.25
                  and overlap_checks<40 and simple_a[i] and simple_b[j] and i not in failed_a and j not in failed_b):
                from .native_guard import guarded_common
                from .material_deltas import volume
                overlap_checks+=1
                if progress:progress(f'Sprawdzanie wspólnej objętości prostych brył: {overlap_checks}/40')
                if cancelled and cancelled():raise Cancelled('Przerwano analizę')
                try:overlap=volume(trace.brep_call('common_volume_isolated',i,j,guarded_common,s.shape,t.shape,tolerance))/min(s.volume,t.volume)
                except Exception:
                    failed_a.add(i);failed_b.add(j);continue
                if overlap>=0.90:
                    potential.append(((1,near,vol_ratio,i,j),i,j,'CHANGED'))
                    overlap_pairs[i,j]=overlap
                elif near<=tolerance*2 and vol_ratio<0.15:
                    potential.append(((2,near,vol_ratio,i,j),i,j,'UNCERTAIN'))
            elif near<=tolerance*2 and vol_ratio<0.15 and bbox_delta<max(2.,sum(s.bbox)*0.04):
                score=(1,near,vol_ratio,i,j);potential.append((score,i,j,'UNCERTAIN'))
    # Optimize all eligible changed pairs together, rather than consuming
    # nearest candidates greedily. Do not treat every multi-edge group as a tie.
    costs={};statuses={}
    for _,i,j,status in potential:
        size=max(10.,max(a[i].bbox),max(b[j].bbox))
        near=min(1.,dist(a[i],b[j])/size)
        volume=abs(a[i].volume-b[j].volume)/max(a[i].volume,b[j].volume)
        envelope=min(1.,float(np.linalg.norm(np.array(a[i].bbox)-b[j].bbox))/size)
        renamed=norm_a[i]!=norm_b[j]
        costs[i,j]=0.60*near+0.20*volume+0.10*envelope+0.10*renamed
        statuses[i,j]=status
    for i,j,ambiguous,gap in assign(costs):
        status=statuses[i,j]
        if ambiguous or i in failed_a or j in failed_b:status='UNCERTAIN'
        d=b[j].center-a[i].center
        reason=('Bryły nie są równe; dopasowanie na podstawie położenia i nazwy lub wspólnej objętości '
                '(szczegóły zmiany wymagają kontroli)') if status=='CHANGED' else (
                'Podobna pozycja i gabaryty, ale brak pewnego dopasowania B-Rep; wymagana kontrola')
        reason+='; globalny dobór par'
        if ambiguous:reason+='; alternatywne przypisanie podobnie prawdopodobne lub limit rozmiaru grupy'
        if (i,j) in overlap_pairs:reason+=f'; wspólna objętość: {overlap_pairs[i,j]*100:.1f}% mniejszej bryły; tożsamość pary wymaga kontroli'
        out.append(Record(i,j,status,reason,float(np.linalg.norm(d)),
                          *map(float,d),float(b[j].volume-a[i].volume),None,"Heurystyka — sprawdź parę"))
        free_a.remove(i);free_b.remove(j)
    for i in sorted(free_a):out.append(Record(i,None,'UNCERTAIN' if i in failed_a else 'REMOVED','Błąd testu B-Rep — nie rozstrzygnięto' if i in failed_a else 'Brak odpowiednika w B'))
    for j in sorted(free_b):out.append(Record(None,j,'UNCERTAIN' if j in failed_b else 'ADDED','Błąd testu B-Rep — nie rozstrzygnięto' if j in failed_b else 'Brak odpowiednika w A'))
    out.sort(key=lambda v:(v.b_index is None, v.b_index if v.b_index is not None else v.a_index))
    assert len({r.a_index for r in out if r.a_index is not None})==len(a)
    assert len({r.b_index for r in out if r.b_index is not None})==len(b)
    if progress:progress(f'Gotowe. Testów B-Rep: {checks}; testów nakładania: {overlap_checks}; trafień pamięci: {memo_hits}; A:{len(a)}, B:{len(b)}')
    return out
