"""R17: name-independent world-space majority-overlap revision matching.

Run AFTER R16 geometry-identical classification and BEFORE material export.
No positive match without real OCC Boolean Common + validated Common/Cut
regions. Ambiguous one-to-many and repetitive parts are never guessed.
"""
from bisect import bisect_right
from time import perf_counter
from .native_guard import NativeGeometryFailure
from .overlap_evidence import classify_overlap
from .candidate_policy import decide_pair
from collections import defaultdict
from math import sqrt, isfinite
import numpy as np
from .compare import Record
from .names import canonical
from .geometry import _precise_world_bounds,signature
from .material_deltas import operate,volume,bind_common,bind_regions
from .material_guard import calculate_isolated as calculate
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from . import trace_r22 as trace

SAME_NAME_MIN=0.68
OTHER_NAME_MIN=0.72
MIN_IOU=0.57
MIN_MARGIN=0.075
MAX_CHECKS=10000

class _XIntervalIndex:
    """Exact, conservative broad-phase for world-space X intervals.

    Uses a segment tree of the maximum X endpoint; queries skip whole
    subtrees that cannot overlap. Y/Z, volume and actual B-Rep proofs remain
    unchanged. Unlike a quantized voxel grid, no valid candidate is lost.
    """
    def __init__(self, bounds):
        self.rows=sorted((float(v[0]),float(v[3]),int(j)) for j,v in bounds.items())
        self.starts=[row[0] for row in self.rows]
        self.size=1 << (max(1,len(self.rows))-1).bit_length()
        self.max_ends=[float('-inf')]*(self.size*2)
        for k,(_,right,_) in enumerate(self.rows):
            self.max_ends[self.size+k]=right
        for k in range(self.size-1,0,-1):
            self.max_ends[k]=max(self.max_ends[k*2],self.max_ends[k*2+1])

    def candidates(self, bounds, tolerance):
        """Yield every B with X overlap (including tolerance), in X order."""
        right=float(bounds[3])+float(tolerance)
        left=float(bounds[0])-float(tolerance)
        stop=bisect_right(self.starts,right)
        if not stop:
            return
        stack=[(1,0,self.size)]
        while stack:
            node,begin,end=stack.pop()
            if begin>=stop or self.max_ends[node]<left:
                continue
            if end-begin==1:
                if begin<len(self.rows):
                    yield self.rows[begin][2]
                continue
            middle=(begin+end)//2
            stack.append((node*2+1,middle,end))
            stack.append((node*2,begin,middle))

def _name_eq(a,b):
    x,y=canonical(a.name),canonical(b.name)
    if x and y and x==y:return True
    from .material_names import material_name_key
    left,right=material_name_key(a.name),material_name_key(b.name)
    return bool(left and left==right)

def _name_changed(a,b):
    return (str(a.name).strip()!=str(b.name).strip() and
        getattr(a,'name_origin','explicit')=='explicit' and
        getattr(b,'name_origin','explicit')=='explicit')

def _bbox_intersect(a,b):
    return float(np.prod(np.maximum(0.,np.minimum(a[3:],b[3:])-np.maximum(a[:3],b[:3]))))

def _score(v,a,b,same):
    # Reject invalid Common before ranking, without changing overlap thresholds.
    if not all(isfinite(float(x)) for x in (v,a.volume,b.volume)) or v<0:
        return None
    top=max(a.volume,b.volume)
    lo=min(a.volume,b.volume)
    if top<=0 or lo<=0:return None
    # Common cannot contain more material than either source solid. Ignore
    # only rounding-level OCCT noise and never reward impossible volumes.
    if v>lo+1e-6*top:return None
    common=min(v,lo)
    union=a.volume+b.volume-common
    if union<=0:return None
    frac=common/top
    iou=common/union
    if frac<(SAME_NAME_MIN if same else OTHER_NAME_MIN) or v/lo<0.80 or iou<MIN_IOU:
        return None
    return 0.65*iou+0.35*frac+(0.015 if same else 0.)

def _reuse_common_volume(a, b, saved_a, saved_b, registry=None):
    """Reuse a positive proof for identical LOCAL B-Reps at same relative pose.

    Separately exported STEP instances can have distinct TopoDS TShapes.
    Exact serialized local B-Rep identity, NEVER numeric similarity, can
    independently prove that two occurrences share the same definition.
    """
    sa, sb = a.shape, b.shape
    ca, cb = saved_a.shape, saved_b.shape
    if not sa.IsPartner(ca) or not sb.IsPartner(cb):
        if registry is None or signature(a)!=signature(saved_a) or signature(b)!=signature(saved_b):
            return False
        if not registry.same_definition(a,saved_a) or not registry.same_definition(b,saved_b):
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


class _TranslatedProofIndex:
    """Index only previously verified native proofs; local hashes are hints.

    Each cache hit still requires _reuse_common_volume to check partner
    identity, orientation, rotation and relative translation. No failed
    Boolean result can become a positive proof.
    """
    def __init__(self, limit=128):
        from .geometry_registry import GeometryRegistry
        self.groups=defaultdict(list)
        # Numeric signatures are only bucket hints; hits need full B-Rep
        # identity and matching relative OCCT locations before proof reuse.
        self.signature_groups=defaultdict(list)
        self.registry=GeometryRegistry()
        self.limit=limit
        self.saved=0
        self.candidates_checked=0

    @staticmethod
    def _key(a,b):
        from OCP.TopLoc import TopLoc_Location
        sa=a.shape.Located(TopLoc_Location())
        sb=b.shape.Located(TopLoc_Location())
        return (hash(sa),int(sa.Orientation()),hash(sb),int(sb.Orientation()))

    def find(self,a,b):
        seen=set()
        for entries in (self.groups.get(self._key(a,b),()),
                        self.signature_groups.get((signature(a),signature(b)),())):
            for old_a,old_b,proof in entries:
                key=(id(old_a),id(old_b))
                if key in seen:continue
                seen.add(key)
                self.candidates_checked+=1
                if _reuse_common_volume(a,b,old_a,old_b,self.registry):
                    return (old_a,old_b,proof)
        return None

    def save(self,a,b,proof):
        if self.saved>=self.limit:return
        self.groups[self._key(a,b)].append((a,b,proof))
        self.signature_groups[(signature(a),signature(b))].append((a,b,proof))
        self.saved+=1


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



def _recenter_origin(a,b,tolerance):
    """Numerical stabilizer for whole-assembly bent/thin Boolean geometry.

    Bounding boxes are location hints only; they NEVER prove a material
    intersection. Both source solids are translated by the SAME rigid offset.
    Native Common/Cut and source-bound conservation still have to pass.
    """
    bounds_a=np.asarray(_precise_world_bounds(a.shape),dtype=float)
    bounds_b=np.asarray(_precise_world_bounds(b.shape),dtype=float)
    if (bounds_a.shape!=(6,) or bounds_b.shape!=(6,) or
            not np.isfinite(bounds_a).all() or not np.isfinite(bounds_b).all()):
        return None
    origin=.5*(np.minimum(bounds_a[:3],bounds_b[:3])+
               np.maximum(bounds_a[3:],bounds_b[3:]))
    # Do not introduce another native computation near the origin. This
    # intervention is for geometry numerically displaced in an assembly.
    if not np.isfinite(origin).all() or np.linalg.norm(origin)<=max(100.,1000.*tolerance):
        return None
    return origin


def _topology_recenter_candidate(message):
    reason=str(message)
    return ('Original STEP stored tolerance exceeds CAD budget' not in reason and
            any(marker in reason for marker in (
                'OCCT Boolean returned invalid or null topology',
                'MATERIAL_BOOLEAN_UNVERIFIED:',
                'Invalid Boolean topology')))


def _recentered_regions(a,b,tolerance):
    """Try the existing isolated Common/Cut near local origin and rebind.

    All three resulting B-Reps are moved BACK to their original world
    coordinates and validated against unmodified original A/B sources.
    This is never a heuristic CHANGED proof or a change in tolerance.
    """
    from types import SimpleNamespace
    from OCP.gp import gp_Trsf,gp_Vec
    from OCP.TopLoc import TopLoc_Location
    origin=_recenter_origin(a,b,tolerance)
    if origin is None:
        raise ValueError('Brak odsunietego ukladu CAD do ponowienia')
    transform=gp_Trsf()
    transform.SetTranslation(gp_Vec(*map(float,-origin)))
    location=TopLoc_Location(transform)
    left=SimpleNamespace(shape=a.shape.Moved(location),
                         volume=a.volume,name=a.name)
    right=SimpleNamespace(shape=b.shape.Moved(location),
                          volume=b.volume,name=b.name)
    centered=calculate(left,right,tolerance)
    restored=_translated_regions(centered,origin)
    # Exact bound/conservation of the CURRENT source geometry remains
    # mandatory; a successful subprocess alone cannot certify a revision.
    bind_regions(restored,a,b,tolerance)
    return restored


def merge_material_revisions(a,b,records,tolerance=0.01,progress=None,cancelled=None,review_approval=None,geometry_context=None):
    """Strict by default; an explicit review choice may preserve unknowns."""
    records=list(records)
    # In the interactive workflow isolate failed B-Rep pairs, preserving all
    # independent verified results. Strict non-interactive callers stay fail-closed.
    result,regions,stat=_merge_material_revisions_strict(
        a,b,records,tolerance,progress,cancelled,geometry_context=geometry_context,
        recover_failures=review_approval is not None)
    if not stat.get('incomplete'):
        return result,regions,stat
    proposal={'status':'material_unverified','reason':stat['reason'],
              'unverified_A':stat['unverified_A'],
              'unverified_B':stat['unverified_B'],
              'failed_pair':stat.get('failed_pair')}
    if review_approval(proposal)!='review':
        raise InterruptedError('Anulowano przygotowanie raportu częściowego.')
    trace.mark('revision_overlap_guard','PARTIAL_REVIEW',**stat)
    if progress:progress(
        f"Raport częściowy: do sprawdzenia {stat['unverified_A']} elementów A "
        f"i {stat['unverified_B']} elementów B; potwierdzono "
        f"{stat['accepted']} zmian geometrii mimo błędów innych par.")
    return result,regions,stat


def _merge_material_revisions_strict(a,b,records,tolerance=0.01,progress=None,cancelled=None,geometry_context=None,recover_failures=False):
    old_ids={r.a_index for r in records if r.status=='REMOVED' and r.a_index is not None and r.b_index is None}
    new_ids={r.b_index for r in records if r.status=='ADDED' and r.b_index is not None and r.a_index is None}
    original_old_ids=set(old_ids)
    original_new_ids=set(new_ids)
    stat=dict(candidate_pairs=0,boolean_checks=0,accepted=0,ambiguous=0,invalid_boolean=0,
              budget_exceeded=False,rigid_pairs_excluded=0,low_overlap_rejected_pairs=0,
              intermediate_overlap_reviewed_pairs=0,mutual_overlap_candidate_pairs=0,
              invalid_overlap_evidence=0,retry_budget_attempted=0,retry_budget_recovered=0,
              min_common_larger_same_name=SAME_NAME_MIN,
              min_common_larger_different_name=OTHER_NAME_MIN,min_iou=MIN_IOU,
               brep_calls_total=0,brep_calls_by_phase={},
               brep_failures_by_phase={},brep_seconds_by_phase={})
    def measured_brep(phase,i,j,fn,*args,**kwargs):
        """Record every native attempt, even errors and timeouts."""
        started=perf_counter()
        stat['brep_calls_total']+=1
        calls=stat['brep_calls_by_phase']
        calls[phase]=calls.get(phase,0)+1
        try:
            return trace.brep_call(phase,i,j,fn,*args,**kwargs)
        except BaseException:
            failures=stat['brep_failures_by_phase']
            failures[phase]=failures.get(phase,0)+1
            raise
        finally:
            elapsed=stat['brep_seconds_by_phase']
            elapsed[phase]=round(elapsed.get(phase,0.)+perf_counter()-started,4)
    if not old_ids or not new_ids:return list(records),{},stat
    if progress:progress(f'Zmiany materiału: przygotowanie Common — {len(old_ids)} starych i {len(new_ids)} nowych pozycji; sprawdzam wystąpienia w całych rewizjach.')
    # A removed occurrence of a repeated, still-present definition is not
    # automatically a material revision. Only exclude it when the existing
    # assembly match independently proves the SAME rigid geometry and name.
    # A genuinely revised definition with no surviving identical match remains
    # eligible for the normal Common/Cut revision search.
    # Do not treat occurrence deltas of an already proven surviving STEP
    # definition as changes in material. Historically only equal part NAMES
    # were searched; renamed STEP occurrences then entered Common/Cut and
    # could become UNCERTAIN after an unrelated Boolean failure.
    #
    # Names and numeric signatures only choose candidates. Exclusion still
    # requires two positive geometry proofs, one to each side of the
    # surviving SAME/RENAMED/MOVED match. Never infer from a shared name,
    # volume, bounding box, signature, or count alone.
    preparation_started=perf_counter()
    excluded_occurrences=set()
    excluded_added=set()
    stat['repeated_signature_fallback_checks']=0
    stat['repeated_signature_fallback_proofs']=0
    if geometry_context is not None:
        same_definition=getattr(geometry_context,'same_definition',None)
        def known_same_definition(left,right):
            return (geometry_context.has_rigid_proof(left,right,tolerance) or
                    (same_definition is not None and same_definition(left,right)))

        survivor_pairs=[r for r in records
                        if r.a_index is not None and r.b_index is not None
                        and r.status in ('SAME','RENAMED','UNCHANGED','MOVED')]

        def exclude_occurrences(indices,own,opposite,own_field,other_field):
            # Try name-indexed matches first (cheap common case). Only
            # unresolved names trigger a lazily built signature hint index.
            by_name=defaultdict(list)
            for record in survivor_pairs:
                p=own[getattr(record,own_field)]
                by_name[canonical(p.name)].append(record)
            signature_index=None
            excluded=set()
            for ordinal,i in enumerate(sorted(indices)):
                if cancelled and cancelled():raise InterruptedError('Anulowano porównywanie rewizji')
                if progress and ordinal and ordinal%50==0:progress(f'Zmiany materiału: kontrola istniejących odpowiedników {ordinal}/{len(indices)}.')
                part=own[i]
                tested=set()
                def prove_matching(records_to_check,fallback=False):
                    for record in records_to_check:
                        record_id=getattr(record,own_field)
                        if record_id in tested:continue
                        tested.add(record_id)
                        if fallback:stat['repeated_signature_fallback_checks']+=1
                        source=own[record_id]
                        # The existing SAME/RENAMED/MOVED record is an
                        # independently confirmed A↔B geometry proof. A
                        # repeat needs exact identity only to that survivor
                        # ON ITS OWN revision side. Requiring byte-identical
                        # B-Rep across two separately exported STEP revisions
                        # wrongly rejects genuine occurrences.
                        if known_same_definition(part,source):
                            if fallback:stat['repeated_signature_fallback_proofs']+=1
                            return True
                    return False
                if prove_matching(by_name.get(canonical(part.name),())):
                    excluded.add(i)
                    continue
                if signature_index is None:
                    signature_index=defaultdict(list)
                    for record in survivor_pairs:
                        signature_index[signature(own[getattr(record,own_field)])].append(record)
                if prove_matching(signature_index.get(signature(part),()),fallback=True):
                    excluded.add(i)
            return excluded

        excluded_occurrences=exclude_occurrences(old_ids,a,b,'a_index','b_index')
        excluded_added=exclude_occurrences(new_ids,b,a,'b_index','a_index')
        old_ids-=excluded_occurrences
        new_ids-=excluded_added
    # Repeated details may enter Common ONLY with equal full-model counts
    # and the same engineering name after a separated revision suffix.
    from .repeated_geometry import RepeatedMaterialPolicy
    repeat_policy=RepeatedMaterialPolicy(a,b,tolerance,geometry_context,cancelled,
        old_ids=original_old_ids,new_ids=original_new_ids,progress=progress)
    stat['population_scope_old']=len(original_old_ids)
    stat['population_scope_new']=len(original_new_ids)
    stat['population_statistics_scope']='families_touching_common_operands'
    stat['preparation_seconds']=round(perf_counter()-preparation_started,6)
    stat['repeated_old_population']=len(repeat_policy.repeated_a)
    stat['repeated_new_population']=len(repeat_policy.repeated_b)
    # A renamed survivor must not defeat the user's equal-population/name
    # exception. Restore ONLY unmatched repeated operands that meet it; never
    # consume an existing SAME/MOVED record or override a native failure.
    admitted_old,admitted_new=repeat_policy.eligible(original_old_ids,original_new_ids)
    old_ids.update(admitted_old & repeat_policy.repeated_a)
    new_ids.update(admitted_new & repeat_policy.repeated_b)
    eligible_old,eligible_new=repeat_policy.eligible(old_ids,new_ids)
    excluded_occurrences.update(old_ids-eligible_old)
    excluded_added.update(new_ids-eligible_new)
    excluded_occurrences-=eligible_old
    excluded_added-=eligible_new
    old_ids,new_ids=eligible_old,eligible_new
    stat['repeated_old_admitted']=len(old_ids & repeat_policy.repeated_a)
    stat['repeated_new_admitted']=len(new_ids & repeat_policy.repeated_b)
    stat['repeated_candidate_pairs_skipped']=0
    stat['removed_repeated_occurrences_excluded']=len(excluded_occurrences)
    stat['added_repeated_occurrences_excluded']=len(excluded_added)
    if not old_ids or not new_ids:return list(records),{},stat
    if progress:progress(f'Zmiany materiału: {len(old_ids)} starych i {len(new_ids)} nowych elementów; sprawdzanie geometrii…')
    ba={i:np.asarray(_precise_world_bounds(a[i].shape),float) for i in old_ids}
    bb={j:np.asarray(_precise_world_bounds(b[j].shape),float) for j in new_ids}
    # Spatial broad phase: avoid repeatedly slicing every earlier B interval
    # for each A. The interval tree is conservative and never proves geometry.
    index_started=perf_counter()
    x_index=_XIntervalIndex(bb)
    stat['spatial_index_build_seconds']=round(perf_counter()-index_started,5)
    stat['spatial_candidates_scanned']=0
    # Fingerprint is only a candidate-order accelerator, never a veto.
    # It computes no geometry: volume/area/central inertia are already loaded.
    from .fingerprint_priority import FingerprintPriority
    fingerprint_rank=FingerprintPriority()
    stat['fingerprint_tie_groups']=0
    stat['fingerprint_descriptors_calculated']=0
    edges={}
    best_common={}
    # Store verified reusable Common proofs for large assemblies, not only the first 128.
    common_cache=_TranslatedProofIndex(limit=min(4096,max(128,len(old_ids)+len(new_ids))))
    failed_old=set();failed_new=set();failures=[]
    def mark_failure(i,j,error,code='BOOLEAN_FAILED'):
        failed_old.add(i);failed_new.add(j)
        message=str(error)
        # A fatal input-tolerance mismatch is an input invariant, not a
        # transient numerical operation. Two native timeouts on the same
        # unchanged operands likewise cannot be repaired by repeating the
        # same Common + Cut deadlines. Keep both explicitly unverified.
        if 'Original STEP stored tolerance exceeds CAD budget' in message:
            code='INVALID_INPUT_TOLERANCE'
        elif ('Timeout odizolowanej operacji Common' in message and
              'Obliczenie Common/Cut nieukończone' in message):
            code='REPEATED_NATIVE_TIMEOUT'
        entry={'a_index':i,'b_index':j,'error':message,'code':code}
        failures.append(entry)
        trace.mark('revision_material_pair','UNVERIFIED',**entry)
        if progress:progress(f'Niepotwierdzona para A[{i}] / B[{j}]: {error}; kontynuuję inne pary.')
    stat['common_proof_reuse']=0
    stat['alternative_region_recovery']=0
    stat['alternative_region_failures']=0
    stat['recentered_material_attempted']=0
    stat['recentered_material_recovered']=0
    stat['recentered_material_failed']=0
    stat['excluded_after_common_failure']=0
    stat['exclusion_witnesses']=[]
    guarded_large = True  # every unresolved Common is isolated, including small assemblies
    guarded_started=perf_counter()
    # Native calls have independent per-pair deadlines. An assembly-wide
    # wall-clock cutoff discards valid later candidates on large CAD models.
    # Keep the separate native-call count cap as a safety fallback.
    guarded_budget_s=None
    stat['guarded_budget_seconds']=None
    stat['guarded_budget_mode']='per_pair'
    trace.mark('revision_overlap_guard','BEGIN',guarded=guarded_large,unresolved=len(old_ids)+len(new_ids),budget_seconds=guarded_budget_s)
    for idx,i in enumerate(sorted(old_ids)):
        if cancelled and cancelled():raise InterruptedError('Anulowano porównywanie rewizji')
        ref=a[i];bounds=ba[i]
        candidates=[]
        for j in x_index.candidates(bounds,tolerance):
            stat['spatial_candidates_scanned']+=1
            if not repeat_policy.allows(i,j):
                stat['repeated_candidate_pairs_skipped']+=1
                continue
            # Cheap conservative Y/Z gate before volume and distance. This
            # cannot reject touching / tolerance-adjacent valid pairs.
            target=bb[j]
            if (target[4]+tolerance<bounds[1] or bounds[4]+tolerance<target[1] or
                target[5]+tolerance<bounds[2] or bounds[5]+tolerance<target[2]):
                continue
            other=b[j]
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
        # Priority-only: all eligible pairs still get the same strict native
        # Common/Cut and global one-to-one assignment. On near-overlap ties
        # try the most CAD-similar definition first to reduce wasted work
        # before an existing operation budget/recovery path.
        if len(candidates)>1:
            candidates=fingerprint_rank.common_ties(ref,candidates,b)
            stat['fingerprint_tie_groups']=fingerprint_rank.tie_groups
            stat['fingerprint_descriptors_calculated']=fingerprint_rank.descriptors_computed
        stat['candidate_pairs']+=len(candidates)
        for _,j in candidates:
            if cancelled and cancelled():raise InterruptedError('Anulowano porównywanie rewizji')
            # A verified rigidly congruent definition is not changed material.
            # If population changes kept these as separate ADDED/REMOVED
            # occurrences, retain that classification; never invent a pairing.
            if geometry_context is not None and geometry_context.has_rigid_proof(ref,b[j],tolerance):
                stat['rigid_pairs_excluded']+=1
                continue
            # A cached, independently verified geometric proof does not run
            # another native operation, even if the scan reached MAX_CHECKS.
            cached=common_cache.find(ref,b[j])
            if cached is None and stat['boolean_checks']>=MAX_CHECKS:
                stat['budget_exceeded']=True
                if not recover_failures:
                    raise NativeGeometryFailure('Limit liczby testów materiału — analiza niekompletna')
                mark_failure(i,j,'Nie wykonano testu: przekroczony limit liczby operacji',code='BUDGET_EXCEEDED')
                continue
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
                    shape=measured_brep('revision_common_isolated',i,j,guarded_common,ref.shape,b[j].shape,tolerance)
                elif cached is None:
                    shape=measured_brep('revision_common',i,j,operate,BRepAlgoAPI_Common,ref.shape,b[j].shape,tolerance)
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
                        recovered_regions=measured_brep('revision_invalid_common_fresh_regions',i,j,
                                                        calculate,ref,b[j],tolerance)
                        bind_regions(recovered_regions,ref,b[j],tolerance)
                        shape=recovered_regions.common
                    common=volume(shape)
                    common_cache.save(ref,b[j],common)
            except NativeGeometryFailure as exc:
                failure=NativeGeometryFailure(f'Para A[{i}] „{ref.name}” / B[{j}] „{b[j].name}”: '+str(exc))
                failure.failed_pair={'a_index':i,'b_index':j}
                # An independently isolated shared-filler Common+Cuts method
                # can recover a malformed Common. Never accept it unless all
                # source-bound material regions pass strict conservation.
                if shape is None and cached is None:
                    try:
                        # Re-exported bent parts far from the world origin
                        # can produce unstable Boolean topology even if the
                        # individually exported detail (near 0,0,0) works.
                        # Replace the usual alternative with ONE equivalent
                        # local-coordinate attempt, keeping original operands
                        # and exact conservation checks.
                        use_local=(_topology_recenter_candidate(exc) and
                                   _recenter_origin(ref,b[j],tolerance) is not None)
                        if use_local:
                            stat['recentered_material_attempted']+=1
                            try:
                                recovered_regions=measured_brep(
                                    'revision_common_recentered_regions',i,j,
                                    _recentered_regions,ref,b[j],tolerance)
                            except Exception:
                                stat['recentered_material_failed']+=1
                                raise
                            stat['recentered_material_recovered']+=1
                        else:
                            recovered_regions=measured_brep('revision_common_alternative_regions',i,j,calculate,ref,b[j],tolerance)
                        bind_regions(recovered_regions,ref,b[j],tolerance)
                        common=volume(recovered_regions.common)
                        stat['alternative_region_recovery']+=1
                        trace.mark('revision_common_alternative_regions','RECOVERED',a_index=i,b_index=j,
                                   common_mm3=common,reason=str(exc))
                        if progress:progress(f'Alternatywna operacja Common/Cut poprawnie potwierdziła parę A[{i}] / B[{j}]')
                    except (NativeGeometryFailure,ValueError,RuntimeError,OSError) as alternative_exc:
                        stat['alternative_region_failures']+=1
                        failure=NativeGeometryFailure(str(failure)+'; alternatywna operacja także nie potwierdziła materiału: '+str(alternative_exc))
                        failure.failed_pair={'a_index':i,'b_index':j}
                        # When TWO independent native algorithms report the
                        # SAME deterministic invalid topology, a third heavy
                        # Boolean/exclusion retry cannot establish a positive
                        # material verdict. Likewise two consecutive timeouts
                        # must not launch another 45-90 s process. Fail closed:
                        # retain this pair as UNCERTAIN and continue the rest.
                        primary_msg=str(exc)
                        alternative_msg=str(alternative_exc)
                        topology='OCCT Boolean returned invalid or null topology'
                        double_topology=(topology in primary_msg and
                                         (topology in alternative_msg or
                                          'MATERIAL_BOOLEAN_UNVERIFIED:' in alternative_msg))
                        double_timeout=('Timeout odizolowanej operacji Common' in primary_msg and
                                        ('timed out' in alternative_msg or
                                         'limit 120 s' in alternative_msg))
                        if double_topology or double_timeout:
                            code=('REPEATED_NATIVE_TIMEOUT' if double_timeout
                                  else 'DETERMINISTIC_NATIVE_FAILURE')
                            stat['exclusion_skipped_terminal_failures']=stat.get(
                                'exclusion_skipped_terminal_failures',0)+1
                            trace.mark('revision_common_exclusion','SKIP_TERMINAL_NATIVE_FAILURE',
                                       a_index=i,b_index=j,reason=code)
                            if not recover_failures:raise failure from exc
                            mark_failure(i,j,failure,code=code)
                            continue
                        # Two independently checked translated partitions may
                        # EXCLUDE a changed-revision candidate. Their displaced
                        # geometry is never accepted as a positive comparison.
                        try:
                            from .common_exclusion import guarded_exclusion
                            threshold=(SAME_NAME_MIN if _name_eq(ref,b[j]) else OTHER_NAME_MIN)*max(ref.volume,b[j].volume)
                            proof=measured_brep('revision_common_exclusion',i,j,guarded_exclusion,
                                                  ref.shape,b[j].shape,tolerance,threshold)
                            if proof['excluded']:
                                stat['excluded_after_common_failure']+=1
                                if len(stat['exclusion_witnesses'])<30:
                                    stat['exclusion_witnesses'].append({'a_index':i,'b_index':j,'proof':proof})
                                trace.mark('revision_common_exclusion','EXCLUDED',a_index=i,b_index=j,threshold_mm3=threshold)
                                if progress:progress(f'Wykluczono niezgodną rewizję A[{i}]/B[{j}] na podstawie niezależnych granic wspólnej objętości.')
                                continue
                        except (NativeGeometryFailure,ValueError,RuntimeError,OSError,KeyError) as rejected:
                            trace.mark('revision_common_exclusion','UNRESOLVED',a_index=i,b_index=j,error=str(rejected))
                        if not recover_failures:raise failure from exc
                        mark_failure(i,j,failure)
                        continue
                else:
                    if not recover_failures:raise failure from exc
                    mark_failure(i,j,failure)
                    continue
            except Exception as exc:
                failure=NativeGeometryFailure('Niekompletna analiza wspólnego materiału: '+str(exc))
                if not recover_failures:raise failure from exc
                mark_failure(i,j,failure)
                continue
            # Size/position alone never establishes a revision. The candidate
            # policy only filters independently validated low-overlap pairs;
            # the strict shape/IoU score and Common/Cut proof remain mandatory.
            candidate_decision=decide_pair(
                volume_a=ref.volume,volume_b=b[j].volume,common_volume=common,
                valid_boolean=True,name_matches=_name_eq(ref,b[j]))
            if candidate_decision.action=='SEARCH_ALTERNATIVES':
                stat['low_overlap_rejected_pairs']+=1
                continue
            if candidate_decision.action=='RETRY_ISOLATED':
                stat['invalid_overlap_evidence']+=1
                if not recover_failures:
                    raise NativeGeometryFailure('Niespójny dowód wspólnej objętości')
                mark_failure(i,j,'Niespójny dowód wspólnej objętości')
                continue
            if candidate_decision.overlap_class=='REVIEW_CANDIDATE':
                stat['intermediate_overlap_reviewed_pairs']+=1
            elif candidate_decision.overlap_class=='POSSIBLE_REVISION':
                stat['mutual_overlap_candidate_pairs']+=1
            score=_score(common,ref,b[j],_name_eq(ref,b[j]))
            if score is not None:
                edges[i,j]=score
                if i not in best_common or score>best_common[i][0]:
                    if i not in best_common and len(best_common)>=64:
                        best_common.pop(next(iter(best_common)))
                    best_common[i]=(score,j,evidence,recovered_regions)
        if stat['budget_exceeded'] and not recover_failures:
            raise NativeGeometryFailure('Limit liczby testów materiału — analiza niekompletna')
        if progress and idx and idx%50==0:
            progress(f'R17: geometria rewizji {idx}/{len(old_ids)}; B-Rep {stat["boolean_checks"]}')
    # Recover earlier speculative Common failures using a LATER positive
    # witness for exact local old/new B-Reps and the same relative CAD pose.
    # Matching names, signatures, bounding boxes or similar volumes are
    # NEVER sufficient. Invalid original B-Reps still fail final bind_regions.
    stat['earlier_failures_recovered_by_exact_repeat']=0
    if recover_failures and failures and common_cache.saved:
        unresolved=[]
        for failure in failures:
            i,j=failure['a_index'],failure['b_index']
            evidence=common_cache.find(a[i],b[j])
            if evidence is None:
                unresolved.append(failure)
                continue
            score=_score(evidence[2],a[i],b[j],_name_eq(a[i],b[j]))
            if score is None:
                unresolved.append(failure)
                continue
            edges[i,j]=score
            if i not in best_common or score>best_common[i][0]:
                best_common[i]=(score,j,None,None)
            stat['earlier_failures_recovered_by_exact_repeat']+=1
            trace.mark('revision_repeat_positive_proof','RECOVERED_EARLIER_PAIR',
                       a_index=i,b_index=j,proof='exact_local_brep_relative_location')
        failures=unresolved
        failed_old={f['a_index'] for f in failures}
        failed_new={f['b_index'] for f in failures}
    # Post-pass: retry independently after the large-assembly candidate scan.
    # A pair that fails in a large assembly may pass as an isolated STEP pair.
    # Every retry runs a NEW guarded Common subprocess; no previous invalid
    # result, failed shape, or negative cache entry is reused.
    # A successful Common can EXCLUDE an unrelated pair; a positive CHANGED
    # still requires an independently validated Common/Cut partition.
    if recover_failures and failures and MAX_CHECKS>0:
        retry_started=perf_counter()
        # Do not repeat known deterministic failures; preserve all as
        # UNCERTAIN unless an independently proven alternative dominates.
        unproductive={'INVALID_INPUT_TOLERANCE','REPEATED_NATIVE_TIMEOUT',
                      'DETERMINISTIC_NATIVE_FAILURE'}
        stat['retry_skipped_unproductive']=sum(
            f['code'] in unproductive for f in failures)
        for failure in failures:
            if failure['code'] in unproductive:
                trace.mark('revision_postpass_retry','SKIP_UNPRODUCTIVE',
                           a_index=failure['a_index'],
                           b_index=failure['b_index'],reason=failure['code'])
        budget_pending=[f for f in failures if f['code']=='BUDGET_EXCEEDED']
        geometry_pending=[f for f in failures
                          if f['code'] not in unproductive
                          and f['code']!='BUDGET_EXCEEDED']
        # Retry all failed candidate pairs fairly: isolated comparisons can pass
        # even when the assembly-wide scan exhausted its shared budget.
        # Interleave geometry errors and budget omissions so neither starves.
        pending=[]
        for k in range(max(len(budget_pending),len(geometry_pending))):
            if k<len(geometry_pending):pending.append(geometry_pending[k])
            if k<len(budget_pending):pending.append(budget_pending[k])
        seen=set()
        # Each unique unresolved pair gets one retry, bounded by the native
        # worker's per-pair timeout. Earlier slow pairs cannot exhaust a
        # shared recovery deadline and starve later independent parts.
        stat['retry_budget_seconds']=None
        stat['retry_budget_mode']='per_pair'
        stat['retry_skipped_due_to_time']=0
        stat['retry_failure_attempted']=0
        stat['retry_failure_recovered']=0
        stat['retry_failure_excluded']=0
        stat['retry_failure_failed']=0
        for failure in pending:
            if cancelled and cancelled():raise InterruptedError('Anulowano porównywanie rewizji')
            i,j=failure['a_index'],failure['b_index']
            if (i,j) in seen:continue
            seen.add((i,j))
            is_budget=failure['code']=='BUDGET_EXCEEDED'
            if progress:progress(f'Ponowienie B-Rep A[{i}] / B[{j}]: {len(seen)}/{len(pending)}; przyczyna: {"TIME_BUDGET" if is_budget else "GEOMETRY_FAILURE"}')
            stat['retry_budget_attempted' if is_budget else 'retry_failure_attempted']+=1
            try:
                if is_budget:
                    reg=measured_brep('revision_budget_retry_regions',i,j,calculate,a[i],b[j],tolerance)
                    bind_regions(reg,a[i],b[j],tolerance)
                    common=reg.common_mm3
                else:
                    from .native_guard import guarded_common
                    try:
                        shape=measured_brep('revision_failed_pair_fresh_common',i,j,guarded_common,
                                              a[i].shape,b[j].shape,tolerance)
                        bind_common(shape,a[i].shape,b[j].shape,tolerance)
                        common=volume(shape)
                        reg=None
                    except (NativeGeometryFailure,ValueError,RuntimeError,OSError) as common_exc:
                        # A failing Common alone does not invalidate a pair:
                        # retry a fresh, independently bound Common + Cut partition.
                        trace.mark('revision_failed_pair_fresh_common','FALLBACK_REGIONS',
                                   a_index=i,b_index=j,error=str(common_exc))
                        reg=measured_brep('revision_failed_pair_fresh_regions_fallback',i,j,
                                            calculate,a[i],b[j],tolerance)
                        bind_regions(reg,a[i],b[j],tolerance)
                        common=reg.common_mm3
                proof=classify_overlap(a[i].volume,b[j].volume,common,valid_boolean=True)
                if proof.decision=='UNKNOWN':
                    raise ValueError('Niepotwierdzona wspólna objętość po ponowieniu')
                if proof.decision=='REJECT_CANDIDATE':
                    stat['low_overlap_rejected_pairs']+=1
                    if not is_budget:stat['retry_failure_excluded']+=1
                else:
                    score=_score(common,a[i],b[j],_name_eq(a[i],b[j]))
                    if score is not None:
                        if reg is None:
                            reg=measured_brep('revision_failed_pair_fresh_regions',i,j,
                                                calculate,a[i],b[j],tolerance)
                            bind_regions(reg,a[i],b[j],tolerance)
                        # Preliminary Common filters candidates; final ranking
                        # must use the verified Common/Cut partition.
                        verified_score=_score(reg.common_mm3,a[i],b[j],_name_eq(a[i],b[j]))
                        if verified_score is None:
                            raise ValueError('Zweryfikowany podział Common/Cut nie potwierdził rewizji')
                        score=verified_score
                        edges[i,j]=score
                        if i not in best_common or score>best_common[i][0]:
                            best_common[i]=(score,j,None,reg)
                failures.remove(failure)
                stat['retry_budget_recovered' if is_budget else 'retry_failure_recovered']+=1
                trace.mark('revision_postpass_retry','VERIFIED',a_index=i,b_index=j,
                           common_mm3=common,decision=proof.decision)
            except (NativeGeometryFailure,ValueError,RuntimeError,OSError) as exc:
                if not is_budget:stat['retry_failure_failed']+=1
                trace.mark('revision_postpass_retry','UNRESOLVED',a_index=i,b_index=j,error=str(exc))
        stat['retry_elapsed_s']=round(perf_counter()-retry_started,3)
        failed_old={f['a_index'] for f in failures}
        failed_new={f['b_index'] for f in failures}
    # A speculative Common failure must not erase a decisively stronger
    # independently verified alternative. Even an IDEAL (upper-bound)
    # intersection for the failed pair must score below the verified edge
    # by MIN_MARGIN. A candidate with unresolved competing claims remains
    # uncertain: exceptions are NEVER converted to geometric evidence.
    stat['dominated_failed_candidates']=0
    if recover_failures and failures:
        def upper_score(i,j):
            optimistic=min(max(0.,float(a[i].volume)),
                           max(0.,float(b[j].volume)),
                           _bbox_intersect(ba[i],bb[j]))
            return _score(optimistic,a[i],b[j],_name_eq(a[i],b[j]))
        verified_by_old=defaultdict(list)
        verified_by_new=defaultdict(list)
        failures_by_new=defaultdict(list)
        for (old_index,new_index),score in edges.items():
            verified_by_old[old_index].append((score,new_index))
            verified_by_new[new_index].append((score,old_index))
        for failure in failures:
            failures_by_new[failure['b_index']].append(failure['a_index'])
        for group in verified_by_old.values():
            group.sort(reverse=True)

        def decisive_alternative(i,j):
            limit=upper_score(i,j)
            for score,k in verified_by_old.get(i,()):
                if k==j:continue
                if limit is not None and score-limit<=MIN_MARGIN:continue
                if any(ee!=i and ss>=score-MIN_MARGIN
                       for ss,ee in verified_by_new[k]):
                    continue
                if any(other_j!=k and ss>=score-MIN_MARGIN
                       for ss,other_j in verified_by_old[i]):
                    continue
                rival_unknown=False
                for ee in failures_by_new[k]:
                    if ee==i:continue
                    bound=upper_score(ee,k)
                    if bound is None or bound>=score-MIN_MARGIN:
                        rival_unknown=True
                        break
                if rival_unknown:continue
                return True
            return False
        retained=[]
        for failure in failures:
            if decisive_alternative(failure['a_index'],failure['b_index']):
                stat['dominated_failed_candidates']+=1
                trace.mark('revision_failed_candidate','DOMINATED_BY_VERIFIED',
                           a_index=failure['a_index'],b_index=failure['b_index'])
            else:
                retained.append(failure)
        failures=retained
        failed_old={f['a_index'] for f in failures}
        failed_new={f['b_index'] for f in failures}
    # A genuinely unresolved candidate could still be the better match;
    # its operands stay UNCERTAIN instead of accepting a guessed edge.
    if recover_failures:
        edges={key:score for key,score in edges.items()
               if key[0] not in failed_old and key[1] not in failed_new}
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
    accepted={};regions={};region_cache=_TranslatedProofIndex()
    stat['region_proof_reuse']=0
    selected=set(chosen)
    best_common={i:value for i,value in best_common.items() if (i,value[1]) in selected}
    stat['region_retry_attempted']=0
    stat['region_retry_recovered']=0
    stat['region_retry_failed']=0
    def verify_regions(reg,i,j):
        # Even translated/cached regions must be bound to the CURRENT operands.
        if _score(reg.common_mm3,a[i],b[j],_name_eq(a[i],b[j])) is None:
            raise ValueError('Niewystarczający wspólny materiał')
        if reg.added_mm3+reg.removed_mm3<=max(1e-3,max(a[i].volume,b[j].volume)*1e-7):
            raise ValueError('Brak różnicy')
        return bind_regions(reg,a[i],b[j],tolerance)
    for i,j in chosen:
        if cancelled and cancelled():raise InterruptedError('Anulowano porównywanie rewizji')
        if progress:progress(f'Zmiany materiału: podział Common/Cut A[{i}] ↔ B[{j}]; limit 90 s')
        cached=best_common.pop(i,None)
        reuse=region_cache.find(a[i],b[j])
        try:
            if cached is not None and cached[1]==j and cached[3] is not None:
                reg=cached[3]
            elif reuse is not None:
                reg=_translated_regions(reuse[2],a[i].center-reuse[0].center)
                stat['region_proof_reuse']+=1
            else:
                reg=measured_brep('revision_material_regions',i,j,calculate,a[i],b[j],tolerance,common_shape=cached[2] if cached and cached[1]==j else None)
            bound=verify_regions(reg,i,j)
        except Exception as exc:
            # Same bent detail may pass in isolation but fail in a large
            # world-coordinate assembly. Before categorizing it UNCERTAIN,
            # try exactly one translated, source-verified local frame.
            rescued=False
            if (_topology_recenter_candidate(exc) and
                    _recenter_origin(a[i],b[j],tolerance) is not None):
                stat['recentered_material_attempted']+=1
                try:
                    reg=measured_brep('revision_material_regions_recentered',i,j,
                                      _recentered_regions,a[i],b[j],tolerance)
                    bound=verify_regions(reg,i,j)
                    rescued=True
                    stat['recentered_material_recovered']+=1
                    if progress:
                        progress(f'Zmiany materiału: odzyskano Common/Cut '
                                 f'dla A[{i}] / B[{j}] w lokalnym układzie CAD.')
                except Exception as local_exc:
                    stat['recentered_material_failed']+=1
                    trace.mark('revision_material_regions_recentered','UNVERIFIED',
                               a_index=i,b_index=j,error=str(local_exc))
            if not rescued:
                if not recover_failures:
                    if isinstance(exc,NativeGeometryFailure):raise
                    raise NativeGeometryFailure('Niekompletna analiza różnic materiału: '+str(exc)) from exc
                # Running an identical isolated material operation immediately
                # after its subprocess timeout repeats the same 120–240s deadline
                # without new evidence. Keep the part explicitly UNCERTAIN.
                import subprocess
                cause=exc
                timed_out=False
                while cause is not None:
                    if isinstance(cause,subprocess.TimeoutExpired):
                        timed_out=True
                        break
                    cause=cause.__cause__
                if timed_out:
                    stat['region_retry_skipped_timeout']=stat.get('region_retry_skipped_timeout',0)+1
                    trace.mark('revision_material_regions_retry','SKIP_IDENTICAL_TIMEOUT',a_index=i,b_index=j)
                    mark_failure(i,j,f'Podział materiału przekroczył limit czasu: {exc}. '
                                   'Nie powtórzono identycznej kosztownej operacji.')
                    continue
                # A native worker that returned a *verified failure code* for a
                # deterministic Boolean/topology defect will run the exact same
                # operands again in the fresh retry. OpenArm 2026-11-04: 13/13
                # such retries failed, wasting ~110 seconds. Fail closed instead:
                # leave the pair for explicit review, never classify it as SAME.
                # Do not skip unknown exceptions: those can be transient.
                reason_text=str(exc)
                if any(code in reason_text for code in (
                        'MATERIAL_BOOLEAN_UNVERIFIED:',
                        'INVALID_BREP_AFTER_REPAIR:',
                        'Original STEP stored tolerance exceeds CAD budget')):
                    stat['region_retry_skipped_deterministic']=stat.get('region_retry_skipped_deterministic',0)+1
                    trace.mark('revision_material_regions_retry','SKIP_DETERMINISTIC_FAILURE',
                               a_index=i,b_index=j,reason=reason_text)
                    mark_failure(i,j,'Niepotwierdzony podział materiału (bez ponawiania identycznej operacji): '+reason_text)
                    continue
                # Critical: initial Common can succeed but the final region split
                # can fail in the large assembly. Retry this SAME verified pair
                # independently, with no cached Common or translated regions.
                stat['region_retry_attempted']+=1
                trace.mark('revision_material_regions_retry','BEGIN',a_index=i,b_index=j,reason=str(exc))
                try:
                    reg=measured_brep('revision_material_regions_fresh_retry',i,j,
                                        calculate,a[i],b[j],tolerance)
                    bound=verify_regions(reg,i,j)
                    stat['region_retry_recovered']+=1
                    trace.mark('revision_material_regions_retry','RECOVERED',a_index=i,b_index=j)
                    if progress:progress(f'Zweryfikowano ponownie podział materiału A[{i}] / B[{j}]')
                except Exception as retry_exc:
                    stat['region_retry_failed']+=1
                    mark_failure(i,j,f'Podział materiału: {exc}; niezależna próba: {retry_exc}')
                    continue
        rename=_name_changed(a[i],b[j])
        d=b[j].center-a[i].center
        record=Record(i,j,'CHANGED',
            f'Wspólna geometria {reg.common_mm3/max(a[i].volume,b[j].volume):.1%}; '+
            f'dodano {reg.added_mm3:.2f} mm³, usunięto {reg.removed_mm3:.2f} mm³'+
            (f'; zmiana nazwy {a[i].name} → {b[j].name}' if rename else ''),
            float(np.linalg.norm(d)),float(d[0]),float(d[1]),float(d[2]),
            float(b[j].volume-a[i].volume),None,'Zweryfikowano OCC Common i Cut',name_changed=rename)
        accepted[i]=(j,record);regions[i]=bound
        # Cache only complete, source-bound material partitions. An unverified
        # result must NEVER be reused by a later occurrence.
        if reuse is None:
            region_cache.save(a[i],b[j],reg)
    used_a=set(accepted);used_b={v[0] for v in accepted.values()}
    out=[r for r in records if not (
      (r.status=='REMOVED' and r.b_index is None and r.a_index in used_a) or
      (r.status=='ADDED' and r.a_index is None and r.b_index in used_b))]
    out.extend(record for j,record in accepted.values())
    if recover_failures and (failed_old or failed_new):
        from dataclasses import replace
        reason='Niepotwierdzona geometria tej części (awaria operacji lub limit); inne pary są nadal analizowane.'
        # Keep the specific failed candidate and native error attached to each
        # UNCERTAIN occurrence, not only in the global failure statistics.
        # Never turn a failed proof into CHANGED, ADDED or REMOVED.
        failure_notes_a=defaultdict(list)
        failure_notes_b=defaultdict(list)
        for failure in failures:
            i,j=failure['a_index'],failure['b_index']
            detail=' '.join(str(failure['error']).split())
            if len(detail)>240:detail=detail[:237]+'...'
            failure_notes_a[i].append(f'A[{i}] / B[{j}]: {detail}')
            failure_notes_b[j].append(f'A[{i}] / B[{j}]: {detail}')
        def uncertain_note(record):
            details=[]
            if record.a_index is not None:
                details.extend(failure_notes_a.get(record.a_index,()))
            if record.b_index is not None:
                details.extend(failure_notes_b.get(record.b_index,()))
            details=list(dict.fromkeys(details))
            suffix='; '.join(details[:2])
            if len(details)>2:suffix+=f'; oraz {len(details)-2} innych par'
            return reason+(' '+suffix if suffix else '')
        out=[replace(r,status='UNCERTAIN',note=uncertain_note(r),
                     confidence='Raport częściowy — wymaga sprawdzenia',
                     distance_mm=None,delta_x=None,delta_y=None,delta_z=None,
                     volume_delta_mm3=None,rotation_deg=None)
             if ((r.a_index in failed_old and r.a_index not in used_a) or
                 (r.b_index in failed_new and r.b_index not in used_b))
                and r.status in ('ADDED','REMOVED','CHANGED') else r for r in out]
    out.sort(key=lambda r:(r.b_index is None,r.b_index if r.b_index is not None else r.a_index))
    precalc={idx:regions[r.a_index] for idx,r in enumerate(out)
             if r.status=='CHANGED' and r.a_index in regions and r.b_index==accepted[r.a_index][0]}
    assert len({r.a_index for r in out if r.a_index is not None})==len(a)
    assert len({r.b_index for r in out if r.b_index is not None})==len(b)
    stat['common_cache_entries']=common_cache.saved
    stat['common_cache_candidates_checked']=common_cache.candidates_checked
    stat['region_cache_entries']=region_cache.saved
    stat['region_cache_candidates_checked']=region_cache.candidates_checked
    stat['accepted']=len(accepted)
    stat['incomplete']=bool(failures)
    if failures:
        stat.update(reason=f"Niepotwierdzonych par: {len(failures)}; zachowano pozostałe zweryfikowane wyniki.",
                    failed_pair={'a_index':failures[0]['a_index'],'b_index':failures[0]['b_index']},
                    failed_pairs=failures[:100],failed_pairs_total=len(failures),
                    unverified_A=len(failed_old-used_a),unverified_B=len(failed_new-used_b),
                    recovered_verified=len(accepted))
    trace.mark('revision_overlap_guard','END',guarded=guarded_large,checks=stat['boolean_checks'],seconds=round(perf_counter()-guarded_started,2),incomplete=stat['incomplete'])
    if progress:progress(f'R17: zmienione rewizje {len(accepted)}; nierozstrzygnięte {stat["ambiguous"]}.')
    return out,precalc,stat
