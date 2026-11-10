"""Translation hypotheses from completed comparison; never an import preflight.

Descriptors propose candidates only. Every accepted placement needs full B-Rep
support. Bounded sampling can miss a transform; it never proves no displacement.
"""
from math import ceil
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
    # Original-frame evidence does not interrupt/restart ordinary compare.
    return None if strict and strict.get('status')=='already_aligned' else strict
