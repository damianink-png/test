"""R17: name-independent world-space majority-overlap revision matching.

Run AFTER R16 geometry-identical classification and BEFORE material export.
No positive match without real OCC Boolean Common + validated Common/Cut
regions. Ambiguous one-to-many and repetitive parts are never guessed.
"""
from bisect import bisect_right
from time import perf_counter
from .native_guard import NativeGeometryFailure
from collections import defaultdict
from math import sqrt
import numpy as np
from .compare import Record
from .names import canonical
from .geometry import _precise_world_bounds
from .material_deltas import operate,volume,bind_common,bind_regions
from .material_guard import calculate_isolated as calculate
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from . import trace_r22 as trace

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

def _reuse_common_volume(a, b, saved_a, saved_b):
    """Exact native definition + same relative pose: valid translated proof."""
    sa, sb = a.shape, b.shape
    ca, cb = saved_a.shape, saved_b.shape
    if not sa.IsPartner(ca) or not sb.IsPartner(cb):
        return False
    if sa.Orientation() != ca.Orientation() or sb.Orientation() != cb.Orientation():
        return False
    # Do not collapse coincident/duplicate occurrences: every candidate in
    # a one-to-many ambiguity must remain independently observable.
    if np.max(np.abs(a.center-saved_a.center)) <= 1.e-9:
        return False
    for new, old in ((sa, ca), (sb, cb)):
        tn = new.Location().Transformation()
        to = old.Location().Transformation()
        for i in (1, 2, 3):
            for j in (1, 2, 3):
                if abs(tn.Value(i, j) - to.Value(i, j)) > 1.e-12:
                    return False
    return bool(np.max(np.abs((a.center-saved_a.center)-(b.center-saved_b.center))) < 1.e-9)


def _translated_regions(regions, offset):
    """Only rigidly relocate independently verified Common/Cut results."""
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.TopLoc import TopLoc_Location
    from .material_deltas import MaterialRegions
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(*map(float, offset)))
    loc = TopLoc_Location(tr)
    return MaterialRegions(regions.common.Moved(loc), regions.added.Moved(loc),
                           regions.removed.Moved(loc), regions.common_mm3,
                           regions.added_mm3, regions.removed_mm3)


def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None,review_approval=None,geometry_context=None):
    """Strict by default; an explicit review choice may preserve unknowns."""
    records=list(records)
    try:
        return _merge_material_revisions_strict(a,b,records,tolerance,progress,cancelled,geometry_context=geometry_context)
    except NativeGeometryFailure as exc:
        if review_approval is None:raise
        uncertain={'ADDED','REMOVED','CHANGED'}
        old_ids={r.a_index for r in records if r.status in uncertain and r.a_index is not None}
        new_ids={r.b_index for r in records if r.status in uncertain and r.b_index is not None}
        proposal={'status':'material_unverified','reason':str(exc),
                  'unverified_A':len(old_ids),'unverified_B':len(new_ids)}
        if review_approval(proposal)!='review':
            raise InterruptedError('Anulowano przygotowanie raportu częściowego.') from exc
        from dataclasses import replace
        reason='Niepotwierdzony wynik materiału w raporcie częściowym. Szczegóły: ANALIZA_NIEKOMPLETNA.txt.'
        result=[replace(r,status='UNCERTAIN',note=reason,confidence='Raport częściowy — wymaga sprawdzenia',
                        distance_mm=None,delta_x=None,delta_y=None,delta_z=None,
                        volume_delta_mm3=None,rotation_deg=None)
                if r.status in uncertain else r for r in records]
        stat={'accepted':0,'incomplete':True,'reason':str(exc),
              'unverified_A':len(old_ids),'unverified_B':len(new_ids)}
        trace.mark('revision_overlap_guard','PARTIAL_REVIEW',**stat)
        if progress:progress(f'Raport częściowy: do sprawdzenia {len(old_ids)} elementów A i {len(new_ids)} elementów B. Nie potwierdzono różnic materiału.')
        return result,{},stat


def _merge_material_revisions_strict(a,b,records,tolerance=0.01,progress=None,cancelled=None,geometry_context=None):
    old_ids={r.a_index for r in records if r.status=='REMOVED' and r.a_index is not None and r.b_index is None}
    new_ids={r.b_index for r in records if r.status=='ADDED' and r.b_index is not None and r.a_index is None}
    stat=dict(candidate_pairs=0,boolean_checks=0,accepted=0,ambiguous=0,invalid_boolean=0,
              budget_exceeded=False,rigid_pairs_excluded=0,min_common_larger_same_name=SAME_NAME_MIN,
              min_common_larger_different_name=OTHER_NAME_MIN,min_iou=MIN_IOU)
    if not old_ids or not new_ids:return list(records),{},stat
    if progress:progress(f'Zmiany materiału: {len(old_ids)} starych i {len(new_ids)} nowych elementów; sprawdzanie geometrii…')
    ba={i:np.asarray(_precise_world_bounds(a[i].shape),float) for i in old_ids}
    bb={j:np.asarray(_precise_world_bounds(b[j].shape),float) for j in new_ids}
    sorted_b=sorted((bb[j][0],j) for j in new_ids)
    xstarts=[x for x,j in sorted_b]
    edges={}
    best_common={}
    common_cache=[]
    stat['common_proof_reuse']=0
    guarded_large = True  # every unresolved Common is isolated, including small assemblies
    guarded_started=perf_counter()
    guarded_budget_s=240.0
    trace.mark('revision_overlap_guard','BEGIN',guarded=guarded_large,unresolved=len(old_ids)+len(new_ids))
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
        for _,j in candidates:
            # A verified rigidly congruent definition is not changed material.
            # If population changes kept these as separate ADDED/REMOVED
            # occurrences, retain that classification; never invent a pairing.
            if geometry_context is not None and geometry_context.has_rigid_proof(ref,b[j],tolerance):
                stat['rigid_pairs_excluded']+=1
                continue
            if stat['boolean_checks']>=MAX_CHECKS:
                stat['budget_exceeded']=True;break
            if perf_counter()-guarded_started>=guarded_budget_s:
                raise NativeGeometryFailure('Limit czasu bezpiecznej analizy wspólnego materiału — nieukończone porównanie')
            cached=next((entry for entry in common_cache
                         if _reuse_common_volume(ref,b[j],entry[0],entry[1])),None)
            shape=None
            evidence=None
            recovered_regions=None
            if cached is not None:
                common=cached[2]
                stat['common_proof_reuse']+=1
            else:
                stat['boolean_checks']+=1
                if progress:progress(f'Zmiany materiału: Common A[{i}] ↔ B[{j}], test {stat["boolean_checks"]}; limit 90 s')
            try:
                if cached is None and guarded_large:
                    from .native_guard import guarded_common
                    shape=trace.brep_call('revision_common_isolated',i,j,guarded_common,ref.shape,b[j].shape,tolerance)
                elif cached is None:
                    shape=trace.brep_call('revision_common',i,j,operate,BRepAlgoAPI_Common,ref.shape,b[j].shape,tolerance)
                if cached is None:
                    try:
                        evidence=bind_common(shape,ref.shape,b[j].shape,tolerance)
                    except (RuntimeError,ValueError) as exc:
                        # The optional Common cache is not a material verdict.
                        # Serialization may invalidate OCCT topology even when
                        # the child validated it. Recompute all three regions
                        # independently; never use the invalid shape or its volume.
                        stat['invalid_boolean']+=1
                        trace.mark('revision_common_cache','RECOMPUTE',a_index=i,b_index=j,error=str(exc))
                        if progress:progress(f'Zmiany materiału: ponowne obliczenie podziału A[{i}] ↔ B[{j}] po odrzuceniu pomocniczego Common')
                        recovered_regions=calculate(ref,b[j],tolerance)
                        bind_regions(recovered_regions,ref,b[j],tolerance)
                        shape=recovered_regions.common
                    common=volume(shape)
                    if len(common_cache)<128:
                        common_cache.append((ref,b[j],common))
            except NativeGeometryFailure as exc:
                raise NativeGeometryFailure(f'Para A[{i}] „{ref.name}” / B[{j}] „{b[j].name}”: '+str(exc)) from exc
            except Exception as exc:
                raise NativeGeometryFailure('Niekompletna analiza wspólnego materiału: '+str(exc)) from exc
            score=_score(common,ref,b[j],_name_eq(ref,b[j]))
            if score is not None:
                edges[i,j]=score
                if i not in best_common or score>best_common[i][0]:
                    if i not in best_common and len(best_common)>=64:
                        best_common.pop(next(iter(best_common)))
                    best_common[i]=(score,j,evidence,recovered_regions)
        if stat['budget_exceeded']:raise NativeGeometryFailure('Limit liczby testów materiału — analiza niekompletna')
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
    accepted={};regions={};region_cache=[]
    stat['region_proof_reuse']=0
    selected=set(chosen)
    best_common={i:value for i,value in best_common.items() if (i,value[1]) in selected}
    for i,j in chosen:
        if cancelled and cancelled():raise InterruptedError('Anulowano porównywanie rewizji')
        if progress:progress(f'Zmiany materiału: podział Common/Cut A[{i}] ↔ B[{j}]; limit 90 s')
        try:
            cached=best_common.pop(i,None)
            reuse=next((entry for entry in region_cache
                        if _reuse_common_volume(a[i],b[j],entry[0],entry[1])),None)
            if cached is not None and cached[1]==j and cached[3] is not None:
                reg=cached[3]
            elif reuse is not None:
                reg=_translated_regions(reuse[2],a[i].center-reuse[0].center)
                stat['region_proof_reuse']+=1
            else:
                reg=trace.brep_call('revision_material_regions',i,j,calculate,a[i],b[j],tolerance,common_shape=cached[2] if cached and cached[1]==j else None)
                if len(region_cache)<128:
                    region_cache.append((a[i],b[j],reg))
            if _score(reg.common_mm3,a[i],b[j],_name_eq(a[i],b[j])) is None:
                raise ValueError('Niewystarczający wspólny materiał')
            if reg.added_mm3+reg.removed_mm3<=max(1e-3,max(a[i].volume,b[j].volume)*1e-7):
                raise ValueError('Brak różnicy')
        except NativeGeometryFailure:
            raise
        except Exception as exc:
            raise NativeGeometryFailure('Niekompletna analiza różnic materiału: '+str(exc)) from exc
        rename=_name_changed(a[i],b[j])
        d=b[j].center-a[i].center
        record=Record(i,j,'CHANGED',
            f'Wspólna geometria {reg.common_mm3/max(a[i].volume,b[j].volume):.1%}; '+
            f'dodano {reg.added_mm3:.2f} mm³, usunięto {reg.removed_mm3:.2f} mm³'+
            (f'; zmiana nazwy {a[i].name} → {b[j].name}' if rename else ''),
            float(np.linalg.norm(d)),float(d[0]),float(d[1]),float(d[2]),
            float(b[j].volume-a[i].volume),None,'Zweryfikowano OCC Common i Cut',name_changed=rename)
        accepted[i]=(j,record);regions[i]=bind_regions(reg,a[i],b[j],tolerance)
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
    trace.mark('revision_overlap_guard','END',guarded=guarded_large,checks=stat['boolean_checks'],seconds=round(perf_counter()-guarded_started,2))
    if progress:progress(f'R17: zmienione rewizje {len(accepted)}; nierozstrzygnięte {stat["ambiguous"]}.')
    return out,precalc,stat
