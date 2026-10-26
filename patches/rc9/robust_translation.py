"""Robust global *translation proposal* from matched part signatures.

Pure Python, no OpenCascade dependency.  It does not prove shape identity:
callers must validate every final SAME pair using strict B-Rep comparison.
"""
from collections import defaultdict
from dataclasses import dataclass
from math import dist
from typing import Hashable, Iterable, Sequence

@dataclass(frozen=True)
class Anchor:
    index: int
    signature: Hashable
    center: tuple[float, float, float]

@dataclass(frozen=True)
class Proposal:
    shift: tuple[float, float, float]
    support: int
    eligible: int
    inlier_pairs: tuple[tuple[int, int], ...]

def propose_translation(a: Sequence[Anchor], b: Sequence[Anchor],
                        tolerance: float = 1e-4,
                        min_support: int = 3,
                        max_signature_multiplicity: int = 4,
                        max_hypotheses: int = 10000) -> Proposal | None:
    """Find robust translation B->A, excluding repeated ambiguous anchors.

    No alignment is returned when the evidence is insufficient or ambiguous.
    The input signature must be translation-invariant and preferably B-Rep based.
    """
    if tolerance <= 0 or min_support < 1:
        raise ValueError("invalid tolerance/support")
    ga, gb = defaultdict(list), defaultdict(list)
    for x in a: ga[x.signature].append(x)
    for x in b: gb[x.signature].append(x)
    keys = [k for k in ga.keys() & gb.keys()
            if len(ga[k]) <= max_signature_multiplicity
            and len(gb[k]) <= max_signature_multiplicity]
    keys.sort(key=lambda k: (len(ga[k])*len(gb[k]), str(k)))
    # One repeated family (e.g. bolts) cannot establish a global transform.
    if len(keys) < 2:
        return None
    hypotheses = []
    for k in keys:
        for x in ga[k]:
            for y in gb[k]:
                hypotheses.append(tuple(x.center[i]-y.center[i] for i in range(3)))
                if len(hypotheses) >= max_hypotheses: break
            if len(hypotheses) >= max_hypotheses: break
        if len(hypotheses) >= max_hypotheses: break
    if not hypotheses: return None
    best = None
    eligible = sum(min(len(ga[k]),len(gb[k])) for k in keys)
    for shift in hypotheses:
        pairs = []
        for k in keys:
            candidates = []
            for x in ga[k]:
                for y in gb[k]:
                    residual = dist(x.center, tuple(y.center[i]+shift[i] for i in range(3)))
                    if residual <= tolerance:
                        candidates.append((residual,x.index,y.index))
            used_a, used_b = set(),set()
            for _,i,j in sorted(candidates):
                if i not in used_a and j not in used_b:
                    used_a.add(i); used_b.add(j); pairs.append((i,j))
        if best is None or len(pairs)>best.support:
            best=Proposal(shift,len(pairs),eligible,tuple(sorted(pairs)))
    if best is None or best.support < min_support: return None
    # Prevent an arbitrary transform when multiple incompatible hypotheses tie.
    for shift in hypotheses:
        if dist(shift,best.shift) <= tolerance: continue
        count=0
        for k in keys:
            matched_a,matched_b=set(),set()
            for x in ga[k]:
                for y in gb[k]:
                    if x.index in matched_a or y.index in matched_b: continue
                    if dist(x.center,tuple(y.center[i]+shift[i] for i in range(3))) <= tolerance:
                        matched_a.add(x.index);matched_b.add(y.index);count+=1
        if count >= best.support:
            return None
    return best
