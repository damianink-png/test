"""Translation hypotheses from completed comparison; never an import preflight.

Descriptors propose candidates only. Every accepted placement needs full B-Rep
support. Bounded sampling can miss a transform; it never proves no displacement.
"""
from collections import defaultdict
from math import ceil
from types import SimpleNamespace
import numpy as np
from .geometry import signature, candidate
from .compare import _spatial_index, _nearby, Cancelled
from .alignment import _relocate
from .registration_gate import frame_support,FrameProofCache
from .step_reexport_tolerance import coarse_candidate,world_candidate,search_radius


def propose(a,b,records,tolerance,progress=None,cancelled=None):
    population=min(len(a),len(b))
    baseline=sum(r.status in ('SAME','RENAMED') for r in records)
    # The former 15% requirement made legitimate large revision shifts
    # undetectable as soon as most geometry changed. Eight independent,
    # world-B-Rep-proven anchors are sufficient to *propose* a placement;
    # the operator still has to confirm it explicitly.
    minimum=max(2,ceil(.60*population)) if population<40 else 8
    low_overlap=population>=40 and minimum<ceil(.15*population)
    moved=[r for r in records if r.status in ('MOVED','UNCERTAIN') and r.a_index is not None and r.b_index is not None and candidate(a[r.a_index],b[r.b_index],tolerance)]
    # A few local moves do not justify global registration. Unmatched repeated
    # definitions are also considered: periodic overlap can hide global motion.
    left_a={r.a_index for r in records if r.a_index is not None and r.b_index is None}
    left_b={r.b_index for r in records if r.b_index is not None and r.a_index is None}
    keys_a={signature(a[i]) for i in left_a}
    keys_b={signature(b[j]) for j in left_b}
    repeated=keys_a & keys_b
    if baseline and moved:
        # One displaced end of a periodic row can hide an entire pitch shift.
        # Centroid checks are cheap; they do not authorize a transformation.
        counts=defaultdict(int)
        for p in a:counts[signature(p)]+=1
        repeated.update(signature(a[r.a_index]) for r in moved
                        if counts[signature(a[r.a_index])]>1)
    if len(a)!=len(b) and (left_a or left_b):
        keys_a.update(signature(a[r.a_index]) for r in moved)
        keys_b.update(signature(b[r.b_index]) for r in moved)
        repeated=keys_a & keys_b
    if len(moved)<minimum and not repeated:
        return None
    def check_cancel():
        if cancelled and cancelled():raise Cancelled('Przerwano analizę')
    histogram={}
    def add(t,weight=1):
        if np.linalg.norm(t)<=tolerance:return
        key=tuple(np.round(t/max(tolerance*.1,1e-5)).astype('int64'))
        if key not in histogram:histogram[key]=[0,t]
        histogram[key][0]+=weight
    for r in moved:add(a[r.a_index].center-b[r.b_index].center)
    sa=defaultdict(list);sb=defaultdict(list)
    for i,p in enumerate(a):sa[signature(p)].append(i)
    for j,p in enumerate(b):sb[signature(p)].append(j)
    # Independent rare-shape consensus supplements the existing candidate
    # histogram. It does NOT classify parts or authorize relocation: the
    # original world B-Rep frame_support/ambiguity checks below remain intact.
    try:
        from .robust_translation import Anchor, propose_translation
        rare_a=[Anchor(i,signature(p),tuple(float(v) for v in p.center))
                for i,p in enumerate(a)]
        rare_b=[Anchor(j,signature(p),tuple(float(v) for v in p.center))
                for j,p in enumerate(b)]
        robust=propose_translation(
            rare_a,rare_b,tolerance=tolerance,
            min_support=max(3,min(12,minimum)),
            max_signature_multiplicity=4,
            max_hypotheses=192)
        if robust is not None:
            candidate_offset=np.asarray(robust.shift,dtype=float)
            add(candidate_offset,weight=min(96,robust.support*3))
            if progress:progress(
                f'Wyrównanie: {robust.support} par rzadkich sygnatur; '
                'potwierdzenie B-Rep nadal wymagane.')
    except (TypeError,ValueError,KeyError) as exc:
        if progress:progress(f'Wyrównanie: pominięto wstępny konsensus ({exc}).')

    def sample(ids):
        return ids if len(ids)<=13 else [ids[round(k*(len(ids)-1)/12)] for k in range(13)]
    # Cohort-centroid offsets are highly informative when identical shapes
    # repeat many times or sample(13) skips the correct assembly pitch.
    # No descriptor alone can approve a translation: real B-Rep verification
    # below remains mandatory.
    for key in sorted(sa.keys() & sb.keys(),key=str):
        ai,bi=sa[key],sb[key]
        if len(ai)==len(bi):
            offset=(np.mean([a[i].center for i in ai],axis=0)
                    -np.mean([b[j].center for j in bi],axis=0))
            add(offset,weight=min(12,len(ai)))
        check_cancel()
        if key not in repeated and len(moved)<minimum:continue
        for i in sample(sa[key]):
            for j in sample(sb[key]):
                if candidate(a[i],b[j],tolerance):add(a[i].center-b[j].center)
    if not histogram:return None
    # No Boolean work until a hypothesis improves on the ordinary comparison.
    radius=search_radius(tolerance)
    cells=_spatial_index(a,range(len(a)),radius)
    ranked=[]
    for _,offset in sorted(histogram.values(),key=lambda v:-v[0])[:96]:
        check_cancel();used=set()
        for p in b:
            center=p.center+offset
            for i in _nearby(cells,SimpleNamespace(center=center),radius):
                if i in used or np.linalg.norm(a[i].center-center)>radius:continue
                if world_candidate(a[i],p,tolerance):used.add(i);break
        if len(used)>=minimum and len(used)>baseline:
            # For equal occurrence support, prioritize the shift explaining
            # more physical material (large structural anchors over bolts).
            covered_volume=sum(max(0.0,float(a[i].volume)) for i in used)
            ranked.append((len(used),offset,covered_volume))
    if not ranked:return None
    if progress:progress('Wynik porównania wskazuje wspólne przesunięcie. Weryfikacja położenia B-Rep…')
    # First test hypotheses using virtual center offsets (above) and a bounded
    # world-BRep sample. A sample is NEVER a proof of the whole assembly.
    # The expensive full proof runs only for viable top-ranked hypotheses.
    # Verify the best-ranked candidate immediately. Once a fully proven frame
    # exists, apply the SAME existing coarse-score pruning heuristic before
    # sampling further candidates. This avoids spending 24 expensive native
    # checks on each of 16 weak hypotheses before starting any full proof.
    winners=[];evaluated=[]
    identity=np.eye(3)
    for coarse,offset,_covered_volume in sorted(ranked,key=lambda v:(-v[0],-v[2])):
        if any(np.linalg.norm(offset-old)<=tolerance for old in evaluated):continue
        if len(evaluated)>=16:break
        if winners:
            best=max(w[0] for w in winners)
            margin=max(1,ceil(.10*best)) if low_overlap else 0
            if coarse<best-margin:continue
        evaluated.append(offset)
        check_cancel()
        # Each unique offset is evaluated once; retaining all shifted OCCT
        # shapes provides no cache hits and unnecessarily increases peak RAM.
        shifted=[_relocate(p,identity,offset) for p in b]
        # Both passes inspect the SAME immutable placed B-Rep inputs. Reuse
        # completed proofs, never descriptor votes or native failures.
        proof_cache=FrameProofCache()
        preliminary=frame_support(a,shifted,tolerance,proofs=24,
                                  progress=progress,cancelled=cancelled,proof_cache=proof_cache)
        checked=preliminary['checked'];confirmed=preliminary['proofs']
        # A sample is ONLY a negative filter. Never classify from it.
        if (preliminary['count']>=minimum
                and preliminary['count']>baseline
                and checked>=min(8,preliminary['count'])
                and confirmed>=min(preliminary['count'],max(4,ceil(.65*checked)))):
            # All accepted pairs must still be independently B-Rep proven.
            support=frame_support(a,shifted,tolerance,verify_all=True,
                                  progress=progress,cancelled=cancelled,proof_cache=proof_cache)
            if support['count']>=minimum and support['count']>baseline:
                winners.append((support['count'],offset,support['pairs']))
        from . import trace_r22 as trace
        trace.mark('registration_proof_cache','END',hits=proof_cache.hits,
                   proof_calls=proof_cache.proof_calls,stored=len(proof_cache.results),
                   exact_definition_reuse=proof_cache.exact_anchor_hits)
        if progress:
            progress(f'Przesunięcie: próbka B-Rep {confirmed}/{checked}, '
                     f'pełne dowody {len(winners)}, kandydaci {len(evaluated)}')
    if not winners:return {'status':'unresolved','reason':'Hipotezy nie przeszły kontroli geometrii.'}
    winners.sort(key=lambda v:-v[0]);votes,offset,certified=winners[0]
    # Sparse revisions (e.g. 8/80 unchanged parts) require a convincing
    # winner, not just any 8 matching generic bolts. Compare all verified
    # runner-ups with a tolerance for nearly identical vote totals.
    ambiguity_margin=max(1,ceil(.10*votes)) if low_overlap else 0
    if any(score>=votes-ambiguity_margin and np.linalg.norm(other-offset)>tolerance
           for score,other,_ in winners[1:]):
        return {'status':'unresolved',
                'reason':'Kilka przesunięć ma podobne potwierdzenie B-Rep. '
                         'Nie zmieniono układu bez jednoznacznego wyniku.'}
    return {'status':'registered','method':'comparison_translation_consensus',
            'translation_B_to_A_mm':offset.tolist(),'rotation_B_to_A':np.eye(3).tolist(),
            'votes':votes,'previous_world_matches':baseline,
            'support_ratio':round(votes/max(1,population),4),
            'requested':True,'enabled':True,'certified_pairs':certified,
            'full_pair_map':certified if len(certified)==len(a)==len(b) else []}


def _periodic_global_offset_possible(a,b,tolerance,population,free_a=(),free_b=()):
    """Don't bypass shift checks on high (but misleading) stage-1 overlap.

    Offsets of balanced repeated definitions may indicate a whole assembly
    shifted by one pitch while N-1 of N identical occurrences still overlap.
    This returns only a suspicion; the B-Rep hypothesis verifier decides.
    """
    if population<4:return False
    buckets_a=defaultdict(list);buckets_b=defaultdict(list)
    for p in a:buckets_a[signature(p)].append(p.center)
    for p in b:buckets_b[signature(p)].append(p.center)
    unmatched_keys={signature(a[i]) for i in free_a} & {signature(b[j]) for j in free_b}
    for key in buckets_a.keys() & buckets_b.keys():
        aa,bb=buckets_a[key],buckets_b[key]
        if min(len(aa),len(bb))<max(3,ceil(population*.10)):
            continue
        if len(aa)!=len(bb):
            if key in unmatched_keys:return True
            continue
        delta=np.mean(aa,axis=0)-np.mean(bb,axis=0)
        if np.linalg.norm(delta)>tolerance:return True
    return False


def propose_from_stage1(a,b,matched,free_a,free_b,tolerance,progress=None,cancelled=None):
    """Check a whole-frame shift BEFORE costly rigid per-part comparisons.

    Uses the exact same B-Rep-verified candidate ranking as propose(), so
    stage 1 has one source of translation hypotheses, not a forked algorithm.
    """
    from .compare import Record
    population=min(len(a),len(b))
    baseline=len(matched)
    if not population or not free_a or not free_b:return None
    # Exact equality of both occurrence lists means no global relocation.
    if baseline==population:return None
    if (baseline/population>=.90 and
        not _periodic_global_offset_possible(a,b,tolerance,population,free_a,free_b)):
        if progress:progress(f'Etap 1: {baseline}/{population} brył zgodnych w miejscu; pomijam wyrównanie.')
        return None
    # The matched records have WORLD-space B-Rep proof from compare stage 1.
    # The unmatched records are placeholders, not a second geometry pass.
    records=list(matched)
    records.extend(Record(i,None,'REMOVED','Wstępnie niezwiązany') for i in free_a)
    records.extend(Record(None,j,'ADDED','Wstępnie niezwiązany') for j in free_b)
    if progress:progress(f'Etap 1: {baseline}/{population} zgodnych w miejscu; sprawdzam globalne przesunięcie.')
    strict=propose(a,b,records,tolerance,progress,cancelled)
    if strict is not None and strict.get('status')=='registered':return strict
    soft=_step_reexport_fallback(a,b,baseline,tolerance,progress,cancelled)
    return soft if soft is not None else strict


def _step_reexport_fallback(a,b,baseline,tolerance,progress=None,cancelled=None):
    """Conservative rescue of translation after STEP re-serialization noise.

    Invoked ONLY after ordinary strict B-Rep shift detection fails. The
    translation is established by an unambiguous large CAD-face consensus,
    never by a filename or by bulk-centroid displacement alone.
    """
    from collections import defaultdict
    from types import SimpleNamespace
    from .step_reexport_tolerance import coarse_candidate,reexport_equivalent_world,shape_valid
    population=min(len(a),len(b))
    if population<4 or baseline>=max(2,ceil(.30*population)):
        return None
    # Bound wide-assembly work; the original strict detection already handles
    # standard STEP copies and sparse changed assemblies.
    selected=sorted(range(len(a)),key=lambda i:(-a[i].volume,str(a[i].name)))
    if len(selected)>64:
        selected=[selected[round(k*(len(selected)-1)/63)] for k in range(64)]
    histogram=defaultdict(list)
    cell=max(.03,3*tolerance)
    attempts=0
    for i in selected:
        if cancelled and cancelled():raise Cancelled('Przerwano analizę')
        for j,p in enumerate(b):
            if attempts>=125000:break
            attempts+=1
            if not coarse_candidate(a[i],p,tolerance):continue
            off=np.asarray(a[i].center-p.center,dtype=float)
            if np.linalg.norm(off)<=tolerance:continue
            key=tuple(int(round(float(q)/cell)) for q in off)
            histogram[key].append(off)
        if attempts>=125000:break
    if not histogram:return None
    cells=_spatial_index(a,range(len(a)),tolerance)
    minimum=max(3,ceil(.70*population))
    winners=[]
    suspect=None
    validity={}
    for samples in sorted(histogram.values(),key=len,reverse=True)[:12]:
        if len(samples)<min(3,ceil(.15*population)):continue
        off=np.median(np.asarray(samples),axis=0)
        if cancelled and cancelled():raise Cancelled('Przerwano analizę')
        # Locate original B solids WITHOUT running rigid matching. Only
        # candidates with one-to-one locations and like physical descriptors.
        used=set();pairs=[]
        for j,p in enumerate(b):
            c=p.center+off
            for i in _nearby(cells,SimpleNamespace(center=c),tolerance):
                if i in used or np.linalg.norm(a[i].center-c)>tolerance:continue
                if not coarse_candidate(a[i],p,tolerance):continue
                used.add(i);pairs.append((i,j));break
        if len(pairs)<minimum:continue
        if max(len(a),len(b))>=600:
            # Keep validity, exact bounds and face/edge operations in the same
            # crash-contained path as the main hypothesis verifier.
            shifted_all=[_relocate(p,np.eye(3),off) for p in b]
            support=frame_support(a,shifted_all,tolerance,verify_all=True,
                                  progress=progress,cancelled=cancelled)
            if support['count']>=minimum and support['count']>baseline:
                winners.append((support['count'],off,support['pairs']))
            elif suspect is None or len(pairs)>suspect['candidate_pairs']:
                suspect={'status':'unresolved','method':'step_reexport_not_certified',
                         'candidate_pairs':len(pairs),'verified_pairs':support['count'],
                         'translation_candidate_mm':off.tolist(),
                         'reason':'Nie potwierdzono wystarczającej liczby par B-Rep; '
                                  'nie zastosowano przesunięcia.'}
            continue
        # A strong geometric-descriptor consensus is a suspicion, never proof.
        # Invalid source solids cannot be repaired by a Boolean comparison.
        invalid=[];eligible=[]
        for i,j in pairs:
            if cancelled and cancelled():raise Cancelled('Przerwano analizę')
            for role,index,part in (('A',i,a[i]),('B',j,b[j])):
                key=(role,index)
                if key not in validity:validity[key]=shape_valid(part.shape)
            if validity['A',i] and validity['B',j]:eligible.append((i,j))
            else:invalid.append((i,j))
        if suspect is None or len(pairs)>suspect['candidate_pairs']:
            suspect={'status':'unresolved','method':'step_reexport_not_certified',
                     'candidate_pairs':len(pairs),'invalid_pairs':len(invalid),
                     'translation_candidate_mm':off.tolist(),
                     'reason':('Wykryto możliwe wspólne przesunięcie, ale nie potwierdzono geometrii. '
                               f'Pary z nieprawidłowym B-Rep: {len(invalid)}/{len(pairs)}. '
                               'Nie zastosowano przesunięcia. Sprawdź lub ponownie wyeksportuj STEP; '
                               'porównanie oryginalnych współrzędnych wymaga świadomego wyboru.')}
        if invalid or len(eligible)<minimum:continue
        pairs=eligible
        # Every accepted occurrence still requires actual B-Rep proof.
        shifted={}
        proof=0
        proven=[]
        for pair_number,(i,j) in enumerate(pairs,1):
            if progress:progress(f'B-Rep STEP: weryfikacja geometrii {pair_number}/{len(pairs)}…')
            if cancelled and cancelled():raise Cancelled('Przerwano analizę')
            if j not in shifted:shifted[j]=_relocate(b[j],np.eye(3),off)
            if proof+len(pairs)-pair_number+1<minimum:break
            if reexport_equivalent_world(a[i],shifted[j],tolerance):
                proof+=1
                proven.append((i,j))
        if proof>=minimum and proof>baseline:
            winners.append((proof,off,proven))
    if not winners:return suspect
    winners.sort(key=lambda row:-row[0]);votes,off,proven=winners[0]
    if any(score>=votes-max(1,ceil(.1*votes)) and np.linalg.norm(other-off)>tolerance
           for score,other,_ in winners[1:]):
        return {'status':'unresolved','reason':'Niejednoznaczne przesunięcie po ponownym zapisie STEP.'}
    if progress:progress(f'B-Rep STEP: {votes}/{population} niezależnie potwierdzonych odpowiadających powierzchni po przesunięciu.')
    return {'status':'registered','method':'step_reexport_translation_consensus',
            'translation_B_to_A_mm':off.tolist(),'rotation_B_to_A':np.eye(3).tolist(),
            'votes':votes,'previous_world_matches':baseline,'support_ratio':round(votes/population,4),
            'requested':True,'enabled':True,'step_reexport_tolerance':True,
            # Certified 1:1 face topology mapping; reuse when FULLY matching
            # instead of serializing / comparing complex shapes a third time.
            'certified_pairs':sorted(proven),
            'full_pair_map':sorted(proven) if len(proven)==len(a)==len(b) else []}
