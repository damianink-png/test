"""Translation hypotheses from completed comparison; never an import preflight.

Descriptors propose candidates only. Every accepted placement needs full B-Rep
support. Bounded sampling can miss a transform; it never proves no displacement.
"""
from math import ceil
from collections import Counter
import numpy as np
from .registration_gate import frame_support


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
    # For a mostly stationary, same-size revision this O(n) median check
    # rules out a periodic whole-model translation before expensive hypotheses.
    # A true pitch shift moves the center median and still gets verified.
    if len(a)==len(b) and baseline>=ceil(.90*population):
        ca=np.asarray([p.center for p in a],dtype=float)
        cb=np.asarray([p.center for p in b],dtype=float)
        if (np.isfinite(ca).all() and np.isfinite(cb).all() and
            np.max(np.abs(np.median(ca,axis=0)-np.median(cb,axis=0)))
                     <=max(1e-6,float(tolerance))):
            return False
    from .cad_pose_search import landmarks,hypotheses,match_pose
    aa,bb=landmarks(a),landmarks(b)
    # The 90% in-place shortcut must not hide the new unique-anchor route
    # when repeated-pitch occurrences already match at the wrong indices.
    from .unique_anchors import unique_pairs
    from itertools import islice
    from time import monotonic
    mass=(np.asarray([p.center for p in a]),np.asarray([p.center for p in b]))
    for i,j in islice(unique_pairs(a,b,deadline=monotonic()+2.),3):
        for shift in (a[i].center-b[j].center,aa[i]-bb[j]):
            if np.linalg.norm(shift)<=tolerance:continue
            pairs=match_pose(a,b,aa,bb,np.eye(3),shift,max(tolerance,1e-6),mass)
            if len(pairs)>baseline:return True
    for pose in hypotheses(a,b,tolerance,features=(aa,bb)):
        if len(pose.pairs)<=baseline:continue
        exact_candidates=match_pose(a,b,aa,bb,pose.rotation,pose.translation,max(tolerance,1e-6))
        if len(exact_candidates)>baseline:return True
    return False


def _stationary_unique_frame(a,b,matched,tolerance):
    """Cheap no-shift gate using ALREADY verified native world matches.

    A re-exported STEP can have a large number of changed/topologically
    repartitioned solids, even when most stationary material stays in place.
    Reuse verified SAME records rather than launching a speculative global
    translation. Require strong volume, count, unique-geometry and spatial
    coverage; the all-repeated periodic-pitch case stays on the legacy
    candidate-veto path because it has no unique geometric anchors.
    """
    n=min(len(a),len(b))
    if n<8 or len(matched)<ceil(.35*n):
        return False
    from .geometry import signature
    if not all(hasattr(p,'volume') and hasattr(p,'center') for p in a+b):
        return False
    vol=sum(max(0.,float(p.volume)) for p in a)
    if not np.isfinite(vol) or vol<=0:
        return False
    verified=[r for r in matched if r.status in ('SAME','RENAMED')
              and r.a_index is not None and r.b_index is not None]
    matched_volume=sum(max(0.,float(a[r.a_index].volume)) for r in verified)
    if matched_volume < .60*vol:
        return False
    # Only unique *geometry* in BOTH revisions counts as a world anchor.
    # Different names or copies of one bolt cannot satisfy this condition.
    sa=[signature(p) for p in a]
    sb=[signature(p) for p in b]
    count_a=Counter(sa);count_b=Counter(sb)
    anchors=[]
    kinds=set()
    for row in verified:
        i,j=row.a_index,row.b_index
        if (count_a[sa[i]]==1 and count_b[sb[j]]==1
                and sa[i] not in kinds):
            anchors.append(np.asarray(a[i].center,dtype=float))
            kinds.add(sa[i])
    if len(anchors)<3:
        return False
    points=np.asarray(anchors)
    if not np.isfinite(points).all():
        return False
    return np.linalg.matrix_rank(points-points.mean(axis=0),
                                 tol=max(.001,float(tolerance)))>=2

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
    if _stationary_unique_frame(a,b,matched,tolerance):
        if progress:
            progress(f'Etap 1: {baseline}/{population} brył SAME w miejscu; '
                     'niezależne unikatowe kotwice i większość objętości '
                     'potwierdzają oryginalny układ CAD. Pomijam wyrównanie.')
        return None
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
    # Original-frame evidence does not interrupt/restart ordinary compare.
    return None if strict and strict.get('status')=='already_aligned' else strict
