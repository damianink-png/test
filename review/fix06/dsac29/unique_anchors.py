"""Largest bilateral singleton descriptors -> original native translation proof.

Central principal inertia moments are translation/rotation invariant. They
admit candidates only; neither descriptors nor names certify any geometry.
Ambiguous descriptor cohorts are deliberately left to the general search.
"""
from bisect import bisect_left,bisect_right
from time import monotonic
import numpy as np
from . import cad_pose_search as search


def descriptor_match(a,b):
    av=np.asarray([a.volume,a.area,*a.eigenvalues],dtype=float)
    bv=np.asarray([b.volume,b.area,*b.eigenvalues],dtype=float)
    if av.shape!=(5,) or bv.shape!=(5,) or not np.isfinite(av).all() or not np.isfinite(bv).all():return False
    if np.any(av<=0) or np.any(bv<=0):return False
    # Permissive numerical lookup, never a tolerance for geometry proof.
    return bool(np.all(np.abs(av-bv)<=np.maximum([.01,.01,.001,.001,.001],
                       np.maximum(av,bv)*[.01,.01,.025,.025,.025])))


def unique_pairs(a,b,cancelled=None,*,deadline=None,clock=monotonic):
    def index(parts):
        ids=sorted(range(len(parts)),key=lambda i:parts[i].volume)
        return ids,[float(parts[i].volume) for i in ids]
    ia,va=index(a);ib,vb=index(b)
    def cohort(p,parts,ids,values):
        width=max(.011,abs(p.volume)*.0102);out=[]
        lo=bisect_left(values,p.volume-width);hi=bisect_right(values,p.volume+width)
        for k in range(lo,hi):
            if k%128==0:
                search.check_cancel(cancelled)
                if deadline is not None and clock()>=deadline:return []
            i=ids[k]
            if descriptor_match(p,parts[i]):
                out.append(i)
                if len(out)>1:break
        return out
    for i in sorted(range(len(a)),key=lambda i:(-a[i].volume,i)):
        search.check_cancel(cancelled)
        if deadline is not None and clock()>=deadline:return
        js=cohort(a[i],b,ib,vb)
        if len(js)!=1:continue
        j=js[0]
        if cohort(b[j],a,ia,va)==[i]:yield i,j


def proven_translations(a,b,tolerance,state,deadline,*,extended=False,progress=None,cancelled=None,clock=monotonic):
    """Return only seed translations proven on original WHOLE anchor solids.

    A seed is not a frame decision. The coordinator independently checks the
    remaining assembly. Completed native negatives persist across Search;
    timeouts remain unknown and may be retried with the extended budget.
    """
    from .native_guard import guarded_registered_world,NativeGeometryFailure
    from .cad_registration import place_for_proof
    from . import trace_r22 as trace
    if not hasattr(state,'unique_anchor_cache'):state.unique_anchor_cache={}
    diagnostics={'candidates':0,'native_checks':0,'proven':0,'unknown':0,'anchors':[]}
    state.unique_anchor_diagnostics=diagnostics
    end=min(deadline,clock()+(24 if extended else 12));out=[]
    if progress:progress('Wyrównanie: szukam największych unikatowych detali według objętości i centralnych momentów bezwładności…')
    for i,j in unique_pairs(a,b,cancelled,deadline=end,clock=clock):
        if clock()>=end or diagnostics['candidates']>=(16 if extended else 8):break
        diagnostics['candidates']+=1
        if progress:progress(f'Unikatowy detal: A[{i}] ↔ B[{j}], objętość {a[i].volume:.6g} mm³; zgodne objętość, pole i główne momenty. Sprawdzam geometrię B-Rep (od największego).')
        offsets=[np.asarray(a[i].center)-np.asarray(b[j].center)]
        for attempt in range(2):
            if attempt:
                if clock()>=end:break
                points=search.landmarks([a[i],b[j]],cancelled)
                offsets.append(points[0]-points[1])
                if np.linalg.norm(offsets[-1]-offsets[0])<=tolerance*.1:break
            shift=offsets[-1]
            if not np.isfinite(shift).all() or np.linalg.norm(shift)<=tolerance:continue
            if any(np.linalg.norm(shift-old[0])<=tolerance*.1 for old in out):break
            key=(i,j,tuple(float(v) for v in shift))
            same=state.unique_anchor_cache.get(key)
            if same is None:
                search.check_cancel(cancelled)
                placed=place_for_proof(b[j],np.eye(3),shift)
                remaining=end-clock()
                if remaining<=0:break
                diagnostics['native_checks']+=1
                try:
                    same=bool(guarded_registered_world(a[i],placed,tolerance,allow_boolean=False,
                              timeout_s=min(16. if extended else 8.,remaining)))
                    state.unique_anchor_cache[key]=same
                except NativeGeometryFailure as exc:
                    diagnostics['unknown']+=1
                    trace.mark('unique_anchor','UNVERIFIED',a_id=i,b_id=j,error=str(exc))
                    if progress:progress(f'Unikatowy detal A[{i}]/B[{j}]: nieukończony dowód geometrii; sprawdzam kolejny detal.')
                    continue
            trace.mark('unique_anchor','PROOF',a_id=i,b_id=j,match=bool(same),translation=shift.tolist())
            if same:
                out.append((shift,(i,j)));diagnostics['proven']+=1
                diagnostics['anchors'].append(dict(a=i,b=j,volume=float(a[i].volume),translation=shift.tolist()))
                if progress:progress(f'Unikatowy detal A[{i}]/B[{j}]: geometria potwierdzona; wektor B → A {shift.tolist()} mm. Sprawdzam wspólne przesunięcie pozostałych detali.')
                break
        if len(out)>=3:break
    if progress and not out:progress(f'Unikatowe detale: {diagnostics["candidates"]} kandydatów, {diagnostics["native_checks"]} testów geometrii, {diagnostics["unknown"]} nieukończonych; brak potwierdzonego wektora z unikatowego detalu. Kontynuuję ogólne wyszukiwanie.')
    return out
