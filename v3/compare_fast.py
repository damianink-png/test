"""DS Compare V3.1 FAST: indexed conservative 1:1 B-Rep matching."""
from dataclasses import dataclass
from typing import Optional
from bisect import bisect_left, bisect_right
from collections import defaultdict
from itertools import product
from math import floor
from time import perf_counter
import numpy as np
from .geometry import SolidInfo, candidate, equivalent_world, equivalent_rigid, dist

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

def _normalized_name(s):
    return ''.join(c.lower() for c in s if c.isalnum())

class _VolumeIndex:
    def __init__(self, objects, ids):
        self.sorted = sorted((objects[j].volume, j) for j in ids)
        self.values = [v for v, _ in self.sorted]
    def query(self, volume, tolerance):
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

def compare(a: list[SolidInfo], b: list[SolidInfo], tolerance:float=0.01,
            progress=None,cancelled=None,max_checks:int=15000) -> list[Record]:
    if tolerance<=0 or tolerance>1:
        raise ValueError('Tolerancja B-Rep musi być w zakresie (0, 1] mm')
    free_a=set(range(len(a))); free_b=set(range(len(b)))
    out=[]; checks=0; started=perf_counter()
    if progress:progress('Etap 1/3: identyczne bryły w tym samym miejscu')
    cells=_spatial_index(b,free_b,tolerance)
    # Exact-name matches first globally: important with overlapping duplicates.
    for names_equal in (True,False):
        for i,s in enumerate(a):
            if i not in free_a:continue
            if cancelled and cancelled():raise Cancelled('Przerwano analizę')
            js=[j for j in _nearby(cells,s,tolerance)
                if j in free_b
                and (_normalized_name(s.name)==_normalized_name(b[j].name))==names_equal
                and dist(s,b[j])<=tolerance and candidate(s,b[j],tolerance)]
            js.sort(key=lambda j:(dist(s,b[j]),abs(s.volume-b[j].volume),j))
            for j in js:
                if checks>=max_checks:raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')
                checks+=1
                try:same=equivalent_world(s,b[j],tolerance)
                except Exception as exc:
                    if progress:progress(f'B-Rep test błędny {i}/{j}: {exc}')
                    continue
                if same:
                    out.append(Record(i,j,'SAME' if names_equal else 'RENAMED',
                        'B-Rep: zgodne w położeniu' if names_equal else 'Nazwa: '+s.name+' → '+b[j].name))
                    free_a.remove(i);free_b.remove(j);break
            if progress and (i+1)%200==0:
                progress(f'Etap zgodności: {i+1}/{len(a)}; B-Rep: {checks}; {perf_counter()-started:.1f}s')
    if progress:progress(f'B-Rep zgodne: {len(out)}; etap 2/3: przesunięte i obrócone')
    # Sort only the currently relevant candidate row; no quadratic candidate list.
    volumes=_VolumeIndex(b,free_b)
    for names_equal in (True,False):
        for idx,i in enumerate(sorted(free_a)):
            if cancelled and cancelled():raise Cancelled('Przerwano analizę')
            s=a[i]
            js=[j for j in volumes.query(s.volume,tolerance)
                if j in free_b
                and (_normalized_name(s.name)==_normalized_name(b[j].name))==names_equal
                and candidate(s,b[j],tolerance)]
            js.sort(key=lambda j:(dist(s,b[j]),j))
            for j in js:
                if checks>=max_checks:raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')
                checks+=1
                try:match,rotation,offset=equivalent_rigid(s,b[j],tolerance)
                except Exception as exc:
                    if progress:progress(f'Test ustawienia {i}/{j}: {exc}')
                    continue
                if match:
                    d=b[j].center-s.center
                    remark='Ta sama bryła B-Rep, inne ustawienie/pozycja'
                    if not names_equal:remark+='; zmiana nazwy: '+s.name+' → '+b[j].name
                    out.append(Record(i,j,'MOVED',remark,float(np.linalg.norm(d)),*map(float,d),0.0))
                    free_a.remove(i);free_b.remove(j);break
            if progress and (idx+1)%100==0:
                progress(f'Etap transformacji: {idx+1}/{len(a)}; B-Rep: {checks}; {perf_counter()-started:.1f}s')
    if progress:progress(f'Dopasowano {len(out)}; etap 3/3: zmienione / dodane / usunięte')
    potential=[]
    for i in free_a:
        for j in free_b:
            s,t=a[i],b[j]
            near=dist(s,t)
            vol_ratio=abs(s.volume-t.volume)/max(s.volume,t.volume)
            bbox_delta=np.linalg.norm(np.array(s.bbox)-np.array(t.bbox))
            same_name=_normalized_name(s.name)==_normalized_name(t.name)
            if not (vol_ratio<0.45 and bbox_delta<max(50.,sum(s.bbox)*0.25)):continue
            if same_name and near<max(250.,sum(s.bbox)*0.75):
                potential.append(((0,near,vol_ratio,i,j),i,j,'CHANGED'))
            elif near<=tolerance*2 and vol_ratio<0.15 and bbox_delta<max(2.,sum(s.bbox)*0.04):
                potential.append(((1,near,vol_ratio,i,j),i,j,'UNCERTAIN'))
    potential.sort()
    for _,i,j,status in potential:
        if i not in free_a or j not in free_b:continue
        d=b[j].center-a[i].center
        reason=('Bryły nie są równe; dopasowanie na podstawie nazwy i położenia (szczegóły zmiany wymagają kontroli)'
                if status=='CHANGED' else
                'Podobna pozycja i gabaryty, ale brak pewnego dopasowania B-Rep; wymagana kontrola')
        out.append(Record(i,j,status,reason,float(np.linalg.norm(d)),*map(float,d),
                          float(b[j].volume-a[i].volume)))
        free_a.remove(i);free_b.remove(j)
    for i in sorted(free_a):out.append(Record(i,None,'REMOVED','Brak odpowiednika w B'))
    for j in sorted(free_b):out.append(Record(None,j,'ADDED','Brak odpowiednika w A'))
    out.sort(key=lambda v:(v.b_index is None, v.b_index if v.b_index is not None else v.a_index))
    assert len({r.a_index for r in out if r.a_index is not None})==len(a)
    assert len({r.b_index for r in out if r.b_index is not None})==len(b)
    if progress:progress(f'Gotowe. Sprawdzono {checks} par B-Rep; A:{len(a)}, B:{len(b)}; {perf_counter()-started:.1f}s')
    return out
