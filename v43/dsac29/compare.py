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


class Cancelled(RuntimeError): pass


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


class _CenterAxisIndex:
    """Conservative spatial broadphase for nearby modified parts.

    Uses a binary search in each coordinate and scans the smallest resulting
    axis interval. Unlike a fixed-radius 3-D grid, this supports per-part
    radii without discarding candidate centers or allocating huge cell boxes.
    """
    def __init__(self, parts, indices):
        self.parts=parts
        self.axes=[]
        for axis in range(3):
            pairs=sorted((float(parts[j].center[axis]),j) for j in indices)
            self.axes.append(([x for x,_ in pairs],[j for _,j in pairs]))

    def query(self,part,radius):
        intervals=[]
        for axis,(values,ids) in enumerate(self.axes):
            mid=float(part.center[axis])
            # Tolerance margin avoids dropping a point just outside an axis
            # interval because of Open CASCADE/float coordinate rounding.
            slack=1e-9*max(1.,abs(mid),abs(radius))
            lo=bisect_left(values,mid-radius-slack)
            hi=bisect_right(values,mid+radius+slack)
            intervals.append((hi-lo,axis,lo,hi))
        _,axis,lo,hi=min(intervals)
        values,ids=self.axes[axis]
        return (j for j in ids[lo:hi] if dist(part,self.parts[j])<=radius)


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
            progress=None,cancelled=None,max_checks:int=15000) -> list[Record]:
    """Deterministic conservative matching. Cancels between expensive B-Rep ops."""
    if tolerance<=0 or tolerance>1: raise ValueError('Tolerancja B-Rep musi być w zakresie (0, 1] mm')
    free_a=set(range(len(a))); free_b=set(range(len(b)))
    out=[]; checks=0
    # Keep the Python TShape handles alive for the entire comparison. OCP's
    # wrappers are weakly cached; hashing a temporary TShape() on each pass
    # can give a DIFFERENT key despite IsPartner() being true.
    _handles_a=[s.shape.TShape() for s in a]
    _handles_b=[s.shape.TShape() for s in b]
    group_a=[id(t) for t in _handles_a]
    group_b=[id(t) for t in _handles_b]
    # Caches only PROVEN geometry equivalence for STEP instances sharing a
    # native TShape (the usual case for many repeated assembly components).
    world_anchors = {}
    congruent_groups = set()
    rigid_anchors = {}
    failed_a=set();failed_b=set()
    failed_groups = set()
    memo_hits = 0
    if progress:progress('Etap 1/3: sprawdzanie identycznych brył w tym samym miejscu')
    # Repeated occurrences matched 1:1, prioritizing the same name at same world position.
    started = perf_counter()
    cells = _spatial_index(b, free_b, tolerance)
    # Match exact names first GLOBALLY: repeated and overlapping occurrences
    # must not consume a counterpart that has an exact-name match elsewhere.
    for names_equal in (True, False):
        for i, s in enumerate(a):
            if i not in free_a: continue
            if cancelled and cancelled(): raise Cancelled('Przerwano analizę')
            js = [j for j in _nearby(cells, s, tolerance)
                  if j in free_b
                  and (_normalized_name(s.name) == _normalized_name(b[j].name)) == names_equal
                  and dist(s, b[j]) <= tolerance and candidate(s, b[j], tolerance)]
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
                else:
                    if checks >= max_checks: raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')
                    checks += 1
                    try: same = equivalent_world(s, b[j], tolerance)
                    except Exception as exc:
                        failed_a.add(i);failed_b.add(j)
                        if progress: progress(f'B-Rep test błędny {i}/{j}: {exc}')
                        continue
                if same:
                    world_anchors.setdefault((gs,gt),(i,j))
                    congruent_groups.add((gs,gt))
                    renamed = genuine_rename(s,b[j])
                    out.append(Record(i,j,'RENAMED' if renamed else 'SAME',
                        ('Nazwa: '+s.name+' → '+b[j].name) if renamed else ('B-Rep: zgodne w położeniu; nazwy eksportowe: '+s.name+' / '+b[j].name if s.name!=b[j].name else 'B-Rep: zgodne w położeniu')))
                    free_a.remove(i); free_b.remove(j)
                    break
                # No match; continue searching the next candidate.
            if progress and (i+1)%200 == 0:
                progress(f'Etap zgodności: {i+1}/{len(a)}; B-Rep: {checks}; pamięć: {memo_hits}; {perf_counter()-started:.1f}s')
    if progress:progress(f'B-Rep zgodne: {len(out)}; etap 2/3: przesunięte i obrócone')
    # Geometric equivalence under proper rotation + translation, independent of names.
    # Lazy candidate generation per unmatched A occurrence avoids O(N*M) memory.
    volume_index = _VolumeIndex(b, free_b)
    for names_equal in (True, False):
        for idx,i in enumerate(sorted(free_a)):
            if i not in free_a:continue
            if cancelled and cancelled(): raise Cancelled('Przerwano analizę')
            s = a[i]
            js = [j for j in volume_index.query(s.volume, tolerance)
                  if j in free_b
                  and (_normalized_name(s.name) == _normalized_name(b[j].name)) == names_equal
                  and candidate(s, b[j], tolerance)]
            js.sort(key=lambda j:(dist(s,b[j]),j))
            for j in js:
                ga,gb=group_a[i],group_b[j]
                pair=(ga,gb)
                if pair in congruent_groups or s.shape.IsPartner(b[j].shape):
                    match=True;memo_hits+=1
                    if pair in rigid_anchors:
                        ai,bj,rr=rigid_anchors[pair]
                        rotation=(_location_matrix(a[ai])[:,:3] @ _location_matrix(s)[:,:3].T).T @ rr @ (_location_matrix(b[bj])[:,:3] @ _location_matrix(b[j])[:,:3].T)
                    elif s.shape.IsPartner(b[j].shape):
                        rotation=_location_matrix(s)[:,:3] @ _location_matrix(b[j])[:,:3].T
                    elif pair in world_anchors:
                        ai,bj=world_anchors[pair]
                        rotation=_location_matrix(s)[:,:3] @ _location_matrix(a[ai])[:,:3].T @ _location_matrix(b[bj])[:,:3] @ _location_matrix(b[j])[:,:3].T
                    else:rotation=None
                elif pair in failed_groups:
                    match=False;memo_hits+=1
                else:
                    if checks>=max_checks:raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')
                    checks+=1
                    try: match,rotation,_=equivalent_rigid(s,b[j],tolerance)
                    except Exception as exc:
                        failed_a.add(i);failed_b.add(j)
                        if progress:progress(f'Test ustawienia {i}/{j}: {exc}')
                        continue
                    if match:
                        congruent_groups.add(pair);rigid_anchors[pair]=(i,j,rotation)
                    else:failed_groups.add(pair)
                if match:
                    d=b[j].center-s.center
                    renamed=genuine_rename(s,b[j])
                    remark='Ta sama bryła B-Rep, inne ustawienie/pozycja'
                    if renamed:remark+='; zmiana nazwy: '+s.name+' → '+b[j].name
                    angle=None if rotation is None else float(np.degrees(np.arccos(np.clip((np.trace(rotation)-1)/2,-1,1))))
                    if angle is not None:remark+=f'; obrót dopasowania: {angle:.3f}° (symetria może dać równoważne ustawienie)'
                    out.append(Record(i,j,'MOVED',remark,float(np.linalg.norm(d)),*map(float,d),0.0,angle))
                    free_a.remove(i);free_b.remove(j)
                    break
            if progress and (idx+1)%100 == 0:
                progress(f'Etap transformacji: {idx+1}/{len(a)}; B-Rep: {checks}; pamięć: {memo_hits}; {perf_counter()-started:.1f}s')
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
        by_name[_normalized_name(b[j].name)].append(j)
    # Only inspect all B occurrences sharing a name or within 2*tolerance
    # of the centroid. This preserves the original heuristics without O(A*B)
    # Python-level distance evaluations for dissimilar parts.
    uncertain_cell=max(2*tolerance,1.)
    uncertain_cells=_spatial_index(b,free_b,uncertain_cell)
    near_index=_CenterAxisIndex(b,free_b)
    for i in free_a:
        s=a[i]
        candidates=set(by_name.get(_normalized_name(s.name),()))
        candidates.update(_nearby(uncertain_cells,s,uncertain_cell))
        # Only nearby leftovers; never do a full Boolean cross-product.
        candidates.update(near_index.query(s,max(2.,max(s.bbox)*0.08)))
        for j in candidates:
            t=b[j]
            near=dist(s,t)
            vol_ratio=abs(s.volume-t.volume)/max(s.volume,t.volume)
            bbox_delta=np.linalg.norm(np.array(s.bbox)-np.array(t.bbox))
            same_name=bool(_normalized_name(s.name)) and _normalized_name(s.name)==_normalized_name(t.name)
            if not (vol_ratio<0.45 and bbox_delta<max(50.,sum(s.bbox)*0.25)):
                continue
            if same_name and near<max(250.,sum(s.bbox)*0.75):
                score=(0,near,vol_ratio,i,j);potential.append((score,i,j,'CHANGED'))
            elif (near<=max(2.,max(s.bbox)*0.08) and vol_ratio<0.25
                  and overlap_checks<40 and simple_a[i] and simple_b[j] and i not in failed_a and j not in failed_b):
                from .geometry import _common_volume
                overlap_checks+=1
                if progress:progress(f'Sprawdzanie wspólnej objętości prostych brył: {overlap_checks}/40')
                if cancelled and cancelled():raise Cancelled('Przerwano analizę')
                try:overlap=_common_volume(s.shape,t.shape,tolerance)/min(s.volume,t.volume)
                except Exception:
                    failed_a.add(i);failed_b.add(j);continue
                if overlap>=0.90:
                    potential.append(((1,near,vol_ratio,i,j),i,j,'CHANGED'))
                    overlap_pairs[i,j]=overlap
                elif near<=tolerance*2 and vol_ratio<0.15:
                    potential.append(((2,near,vol_ratio,i,j),i,j,'UNCERTAIN'))
            elif near<=tolerance*2 and vol_ratio<0.15 and bbox_delta<max(2.,sum(s.bbox)*0.04):
                score=(1,near,vol_ratio,i,j);potential.append((score,i,j,'UNCERTAIN'))
    potential.sort()
    degree_a=defaultdict(int);degree_b=defaultdict(int)
    for _,i,j,_ in potential:degree_a[i]+=1;degree_b[j]+=1
    for _,i,j,status in potential:
        if i not in free_a or j not in free_b:continue
        if degree_a[i]>1 or degree_b[j]>1 or i in failed_a or j in failed_b:status='UNCERTAIN'
        d=b[j].center-a[i].center
        reason=('Bryły nie są równe; dopasowanie na podstawie położenia i nazwy lub wspólnej objętości '
                '(szczegóły zmiany wymagają kontroli)') if status=='CHANGED' else (
                'Podobna pozycja i gabaryty, ale brak pewnego dopasowania B-Rep; wymagana kontrola')
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
