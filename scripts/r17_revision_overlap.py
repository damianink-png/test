"""R17: name-independent world-space majority-overlap revision matching.

Run AFTER R16 geometry-identical classification and BEFORE material export.
No positive match without real OCC Boolean Common + validated Common/Cut
regions. Ambiguous one-to-many and repetitive parts are never guessed.
"""
from bisect import bisect_right
from collections import defaultdict
from math import sqrt
import numpy as np
from .compare import Record
from .names import canonical
from .geometry import _precise_world_bounds,_common_volume
from .material_deltas import calculate

SAME_NAME_MIN=0.68
OTHER_NAME_MIN=0.72
MIN_IOU=0.57
MIN_MARGIN=0.075
MAX_CHECKS=1400

def _name_eq(a,b):
    x,y=canonical(a.name),canonical(b.name)
    return bool(x and y and x==y)

def _name_changed(a,b):
    return (str(a.name).strip()!=str(b.name).strip() and
        getattr(a,'name_origin','explicit')=='explicit' and
        getattr(b,'name_origin','explicit')=='explicit')

def _bbox_intersect(a,b):
    return float(np.prod(np.maximum(0.,np.minimum(a[3:],b[3:])-np.maximum(a[:3],b[:3]))))

def _score(v,a,b,same):
    top=max(a.volume,b.volume)
    lo=min(a.volume,b.volume)
    union=a.volume+b.volume-v
    if top<=0 or lo<=0 or union<=0:return None
    frac=v/top
    iou=v/union
    if frac<(SAME_NAME_MIN if same else OTHER_NAME_MIN) or v/lo<0.80 or iou<MIN_IOU:
        return None
    return 0.65*iou+0.35*frac+(0.015 if same else 0.)

def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None):
    old_ids={r.a_index for r in records if r.status=='REMOVED' and r.a_index is not None and r.b_index is None}
    new_ids={r.b_index for r in records if r.status=='ADDED' and r.b_index is not None and r.a_index is None}
    stat=dict(candidate_pairs=0,boolean_checks=0,accepted=0,ambiguous=0,invalid_boolean=0,
              budget_exceeded=False,min_common_larger_same_name=SAME_NAME_MIN,
              min_common_larger_different_name=OTHER_NAME_MIN,min_iou=MIN_IOU)
    if not old_ids or not new_ids:return list(records),{},stat
    ba={i:np.asarray(_precise_world_bounds(a[i].shape),float) for i in old_ids}
    bb={j:np.asarray(_precise_world_bounds(b[j].shape),float) for j in new_ids}
    sorted_b=sorted((bb[j][0],j) for j in new_ids)
    xstarts=[x for x,j in sorted_b]
    edges={}
    for idx,i in enumerate(sorted(old_ids)):
        if cancelled and cancelled():raise InterruptedError('Anulowano porównywanie rewizji')
        ref=a[i];bounds=ba[i]
        candidates=[]
        for _,j in sorted_b[:bisect_right(xstarts,bounds[3]+tolerance)]:
            other=b[j]
            if bb[j][3]+tolerance<bounds[0]:continue
            common_limit=SAME_NAME_MIN if _name_eq(ref,other) else OTHER_NAME_MIN
            if min(ref.volume,other.volume)/max(ref.volume,other.volume)<common_limit:continue
            boxvol=_bbox_intersect(bounds,bb[j])
            if boxvol+max(1e-3,tolerance**3)<common_limit*max(ref.volume,other.volume):continue
            bbox_larger=max(float(np.prod(np.maximum(bounds[3:]-bounds[:3],0))),
                            float(np.prod(np.maximum(bb[j][3:]-bb[j][:3],0))),1e-6)
            distance=np.linalg.norm(ref.center-other.center)/max(1.,sqrt(sum(d*d for d in ref.bbox)))
            priority=boxvol/bbox_larger+0.035*int(_name_eq(ref,other))-0.08*distance
            candidates.append((-priority,j))
        candidates.sort()
        stat['candidate_pairs']+=len(candidates)
        for _,j in candidates[:6]:
            if stat['boolean_checks']>=MAX_CHECKS:
                stat['budget_exceeded']=True;break
            stat['boolean_checks']+=1
            try:common=_common_volume(ref.shape,b[j].shape,tolerance)
            except Exception:
                stat['invalid_boolean']+=1;continue
            score=_score(common,ref,b[j],_name_eq(ref,b[j]))
            if score is not None:edges[i,j]=score
        if stat['budget_exceeded']:break
        if progress and idx and idx%50==0:
            progress(f'R17: geometria rewizji {idx}/{len(old_ids)}; B-Rep {stat["boolean_checks"]}')
    by_a=defaultdict(list);by_b=defaultdict(list)
    for (i,j),score in edges.items():
        by_a[i].append((score,j));by_b[j].append((score,i))
    for options in list(by_a.values())+list(by_b.values()):options.sort(reverse=True)
    chosen=[]
    for (i,j),score in sorted(edges.items(),key=lambda kv:-kv[1]):
        old_edges,new_edges=by_a[i],by_b[j]
        if old_edges[0][1]!=j or new_edges[0][1]!=i:continue
        if ((len(old_edges)>1 and score-old_edges[1][0]<MIN_MARGIN) or
            (len(new_edges)>1 and score-new_edges[1][0]<MIN_MARGIN)):
            stat['ambiguous']+=1;continue
        chosen.append((i,j))
    accepted={};regions={}
    for i,j in chosen:
        if cancelled and cancelled():raise InterruptedError('Anulowano porównywanie rewizji')
        try:
            reg=calculate(a[i],b[j],tolerance)
            if _score(reg.common_mm3,a[i],b[j],_name_eq(a[i],b[j])) is None:
                raise ValueError('Niewystarczający wspólny materiał')
            if reg.added_mm3+reg.removed_mm3<=max(1e-3,max(a[i].volume,b[j].volume)*1e-7):
                raise ValueError('Brak różnicy')
        except Exception:
            stat['invalid_boolean']+=1;continue
        rename=_name_changed(a[i],b[j])
        d=b[j].center-a[i].center
        record=Record(i,j,'CHANGED',
            f'Wspólna geometria {reg.common_mm3/max(a[i].volume,b[j].volume):.1%}; '+
            f'dodano {reg.added_mm3:.2f} mm³, usunięto {reg.removed_mm3:.2f} mm³'+
            (f'; zmiana nazwy {a[i].name} → {b[j].name}' if rename else ''),
            float(np.linalg.norm(d)),float(d[0]),float(d[1]),float(d[2]),
            float(b[j].volume-a[i].volume),None,'Zweryfikowano OCC Common i Cut',name_changed=rename)
        accepted[i]=(j,record);regions[i]=reg
    used_a=set(accepted);used_b={v[0] for v in accepted.values()}
    out=[r for r in records if not (
      (r.status=='REMOVED' and r.b_index is None and r.a_index in used_a) or
      (r.status=='ADDED' and r.a_index is None and r.b_index in used_b))]
    out.extend(record for j,record in accepted.values())
    out.sort(key=lambda r:(r.b_index is None,r.b_index if r.b_index is not None else r.a_index))
    precalc={idx:regions[r.a_index] for idx,r in enumerate(out)
             if r.status=='CHANGED' and r.a_index in regions and r.b_index==accepted[r.a_index][0]}
    assert len({r.a_index for r in out if r.a_index is not None})==len(a)
    assert len({r.b_index for r in out if r.b_index is not None})==len(b)
    stat['accepted']=len(accepted)
    if progress:progress(f'R17: zmienione rewizje {len(accepted)}; nierozstrzygnięte {stat["ambiguous"]}.')
    return out,precalc,stat
