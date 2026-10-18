"""Conservative 1:1 matching with actual B-Rep Boolean tests.

Only B-Rep proven matches can be green. Failures/ambiguities are NOT reported
as matches. The tool compares STEP-exported solids, not editable ZW3D features.
"""
from dataclasses import dataclass
from typing import Optional
import numpy as np
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


def _normalized_name(s):
    return ''.join(c.lower() for c in s if c.isalnum())


def compare(a: list[SolidInfo], b: list[SolidInfo], tolerance:float=0.01,
            progress=None,cancelled=None,max_checks:int=15000) -> list[Record]:
    """Deterministic conservative matching. Cancels between expensive B-Rep ops."""
    if tolerance<=0 or tolerance>1: raise ValueError('Tolerancja B-Rep musi być w zakresie (0, 1] mm')
    free_a=set(range(len(a))); free_b=set(range(len(b)))
    out=[]; checks=0
    if progress:progress('Etap 1/3: sprawdzanie identycznych brył w tym samym miejscu')
    # Repeated occurrences matched 1:1, prioritizing the same name at same world position.
    candidates=[]
    for i,s in enumerate(a):
        for j,t in enumerate(b):
            if dist(s,t)>tolerance:continue
            if not candidate(s,t,tolerance):continue
            score=(0 if _normalized_name(s.name)==_normalized_name(t.name) else 1,
                   dist(s,t),abs(s.volume-t.volume),i,j)
            candidates.append((score,i,j))
    candidates.sort()
    for _,i,j in candidates:
        if i not in free_a or j not in free_b:continue
        if cancelled and cancelled():raise Cancelled('Przerwano analizę')
        if checks>=max_checks: raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')
        checks+=1
        try: same=equivalent_world(a[i],b[j],tolerance)
        except Exception as exc:
            if progress:progress(f'B-Rep test błędny {i}/{j}: {exc}')
            continue
        if same:
            renamed=_normalized_name(a[i].name)!=_normalized_name(b[j].name)
            out.append(Record(i,j,'RENAMED' if renamed else 'SAME',
                             ('Nazwa: '+a[i].name+' → '+b[j].name) if renamed else 'B-Rep: zgodne w położeniu'))
            free_a.remove(i);free_b.remove(j)
    if progress:progress(f'B-Rep zgodne: {len(out)}; etap 2/3: przesunięte i obrócone')
    # Geometric equivalence under proper rotation + translation, independent of names.
    candidates=[]
    for i in free_a:
        for j in free_b:
            if not candidate(a[i],b[j],tolerance):continue
            candidates.append(((0 if _normalized_name(a[i].name)==_normalized_name(b[j].name) else 1,
                                dist(a[i],b[j]),i,j),i,j))
    candidates.sort()
    for _,i,j in candidates:
        if i not in free_a or j not in free_b:continue
        if cancelled and cancelled():raise Cancelled('Przerwano analizę')
        if checks>=max_checks:raise RuntimeError(f'Limit testów B-Rep ({max_checks}) — analiza niekompletna')
        checks+=1
        try: match,rotation,offset=equivalent_rigid(a[i],b[j],tolerance)
        except Exception as exc:
            if progress:progress(f'Test ustawienia {i}/{j}: {exc}')
            continue
        if match:
            d=b[j].center-a[i].center
            renamed=_normalized_name(a[i].name)!=_normalized_name(b[j].name)
            remark='Ta sama bryła B-Rep, inne ustawienie/pozycja'
            if renamed:remark+='; zmiana nazwy: '+a[i].name+' → '+b[j].name
            out.append(Record(i,j,'MOVED',remark,float(np.linalg.norm(d)),*map(float,d),0.0))
            free_a.remove(i);free_b.remove(j)
    if progress:progress(f'Dopasowano {len(out)}; etap 3/3: zmienione / dodane / usunięte')
    # Conservative pairing for DIFFERENT geometry. Require close position and a strong
    # semantic signal (same name) or very close center / similar bounding envelope.
    potential=[]
    for i in free_a:
        for j in free_b:
            s,t=a[i],b[j]
            near=dist(s,t)
            vol_ratio=abs(s.volume-t.volume)/max(s.volume,t.volume)
            bbox_delta=np.linalg.norm(np.array(s.bbox)-np.array(t.bbox))
            same_name=_normalized_name(s.name)==_normalized_name(t.name)
            if not (vol_ratio<0.45 and bbox_delta<max(50.,sum(s.bbox)*0.25)):
                continue
            if same_name and near<max(250.,sum(s.bbox)*0.75):
                score=(0,near,vol_ratio,i,j); potential.append((score,i,j,'CHANGED'))
            elif near<=tolerance*2 and vol_ratio<0.15 and bbox_delta<max(2.,sum(s.bbox)*0.04):
                score=(1,near,vol_ratio,i,j); potential.append((score,i,j,'UNCERTAIN'))
    potential.sort()
    for _,i,j,status in potential:
        if i not in free_a or j not in free_b:continue
        d=b[j].center-a[i].center
        reason=('Bryły nie są równe; dopasowanie na podstawie nazwy i położenia '
                '(szczegóły zmiany wymagają kontroli)') if status=='CHANGED' else (
                'Podobna pozycja i gabaryty, ale brak pewnego dopasowania B-Rep; wymagana kontrola')
        out.append(Record(i,j,status,reason,float(np.linalg.norm(d)),
                          *map(float,d),float(b[j].volume-a[i].volume)))
        free_a.remove(i);free_b.remove(j)
    for i in sorted(free_a):out.append(Record(i,None,'REMOVED','Brak odpowiednika w B'))
    for j in sorted(free_b):out.append(Record(None,j,'ADDED','Brak odpowiednika w A'))
    out.sort(key=lambda v:(v.b_index is None, v.b_index if v.b_index is not None else v.a_index))
    assert len({r.a_index for r in out if r.a_index is not None})==len(a)
    assert len({r.b_index for r in out if r.b_index is not None})==len(b)
    if progress:progress(f'Gotowe. Sprawdzono {checks} par B-Rep; wszystkich wystąpień A:{len(a)}, B:{len(b)}')
    return out
