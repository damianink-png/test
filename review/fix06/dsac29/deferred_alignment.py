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


def propose(a,b,records,tolerance,progress=None,cancelled=None,*,search_state=None,extended=False):
    """The public comparison path delegates to ONE CAD registration engine."""
    from .cad_registration import propose as register
    return register(a,b,records,tolerance,progress,cancelled,
                    search_state=search_state,extended=extended,support=frame_support)


def _periodic_global_offset_possible(a,b,tolerance,population,free_a=(),free_b=(),baseline=0):
    """Cheap CAD-point veto against hiding a whole repeated-pitch shift.

    Evaluate the candidate gain at the ORIGINAL tolerance, so a local move
    cannot turn a permissive registration lookup into evidence of global motion.
    """
    if population<4:return False
    from .cad_pose_search import landmarks,hypotheses,match_pose
    aa,bb=landmarks(a),landmarks(b)
    for pose in hypotheses(a,b,tolerance,features=(aa,bb)):
        if len(pose.pairs)<=baseline:continue
        exact_candidates=match_pose(a,b,aa,bb,pose.rotation,pose.translation,max(tolerance,1e-6))
        if len(exact_candidates)>baseline:return True
    return False


def propose_from_stage1(a,b,matched,free_a,free_b,tolerance,progress=None,cancelled=None,*,search_state=None):
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
        not _periodic_global_offset_possible(a,b,tolerance,population,free_a,free_b,baseline)):
        if progress:progress(f'Etap 1: {baseline}/{population} brył zgodnych w miejscu; pomijam wyrównanie.')
        return None
    # The matched records have WORLD-space B-Rep proof from compare stage 1.
    # The unmatched records are placeholders, not a second geometry pass.
    records=list(matched)
    records.extend(Record(i,None,'REMOVED','Wstępnie niezwiązany') for i in free_a)
    records.extend(Record(None,j,'ADDED','Wstępnie niezwiązany') for j in free_b)
    if progress:progress(f'Etap 1: {baseline}/{population} zgodnych w miejscu; sprawdzam globalne przesunięcie.')
    if search_state is not None:
        search_state.bind(a,b,tolerance)
        search_state.stage1_records=list(matched)
        search_state.free_a=frozenset(free_a);search_state.free_b=frozenset(free_b)
        strict=propose(a,b,records,tolerance,progress,cancelled,search_state=search_state)
    else:
        strict=propose(a,b,records,tolerance,progress,cancelled)
    return strict


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
        if max(len(a),len(b))>=80:
            # Keep validity, exact bounds and face/edge operations in the same
            # crash-contained path as the main hypothesis verifier.
            shifted_all=[_relocate(p,np.eye(3),off) for p in b]
            # Legacy fallback did up to 600+ native checks before the final
            # comparison. Sample at most 48 real B-Rep proofs. Every unproven
            # part must still pass the independent final comparison.
            from .registration_gate import FrameProofCache
            evidence=FrameProofCache()
            support=frame_support(a,shifted_all,tolerance,proofs=48,
                                  progress=progress,cancelled=cancelled,proof_cache=evidence)
            checked=int(support.get('checked',0))
            verified=int(support.get('proofs',0))
            count=int(support.get('count',0))
            if (count>=minimum and count>baseline and checked>=min(40,count)
                    and verified>=max(24,ceil(.90*checked))):
                certified=sorted(evidence.results)
                winners.append((count,off,certified,True,checked,verified))
            elif suspect is None or len(pairs)>suspect['candidate_pairs']:
                suspect={'status':'unresolved','method':'step_reexport_not_certified',
                         'candidate_pairs':len(pairs),'verified_pairs':verified,
                         'translation_candidate_mm':off.tolist(),
                         'reason':'Próbka B-Rep nie potwierdziła przesunięcia; '
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
            winners.append((proof,off,proven,False,proof,proof))
    if not winners:return suspect
    winners.sort(key=lambda row:-row[0]);votes,off,proven,sampled,checked,verified=winners[0]
    if any(score>=votes-max(1,ceil(.1*votes)) and np.linalg.norm(other-off)>tolerance
           for score,other,*_ in winners[1:]):
        return {'status':'unresolved','reason':'Niejednoznaczne przesunięcie po ponownym zapisie STEP.'}
    if progress:
        progress(f'B-Rep STEP: {verified}/{checked} sprawdzonych dowodów, '
                 f'{votes}/{population} kandydatów po przesunięciu. '+
                 ('Reszta wymaga końcowej kontroli.' if sampled else 'Pełne dowody.'))
    return {'status':'registered','method':'step_reexport_translation_consensus',
            'translation_B_to_A_mm':off.tolist(),'rotation_B_to_A':np.eye(3).tolist(),
            'votes':votes,'previous_world_matches':baseline,'support_ratio':round(votes/population,4),
            'requested':True,'enabled':True,'step_reexport_tolerance':True,
            'verification_scope':('sample_then_final_compare' if sampled else 'full_brep'),
            'checked_sample_count':checked,'verified_sample_count':verified,
            'certified_pairs':sorted(proven),
            'full_pair_map':sorted(proven) if not sampled and len(proven)==len(a)==len(b) else []}
