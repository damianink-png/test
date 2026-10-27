"""Robust global *translation proposal* from matched part signatures.

Pure Python, no OpenCascade dependency.  It does not prove shape identity:
callers must validate every final SAME pair using strict B-Rep comparison.
"""
from collections import defaultdict
from dataclasses import dataclass
from math import dist, floor, isfinite
from itertools import product
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

def match_candidates(candidates):
    """Maximum 1:1 support inside a small signature family, deterministic.

    Unique choices are prioritized; remaining components use augmenting
    paths. Unlike greedy nearest pairing, a close pair cannot strand another
    valid occurrence. This proposes a frame, never proves CAD identity.
    """
    options=defaultdict(list)
    for residual,i,j in sorted(candidates):
        if j not in options[i]: options[i].append(j)
    owner={}
    def augment(i,seen):
        for j in options[i]:
            if j in seen:continue
            seen.add(j)
            if j not in owner or augment(owner[j],seen):
                owner[j]=i;return True
        return False
    # Fewest options first is deterministic and prioritizes unique anchors.
    for i in sorted(options,key=lambda i:(len(options[i]),i)):augment(i,set())
    return sorted((i,j) for j,i in owner.items())

def propose_translation(a: Sequence[Anchor], b: Sequence[Anchor],
                        tolerance: float = 1e-4,
                        min_support: int = 3,
                        max_signature_multiplicity: int = 4,
                        max_hypotheses: int = 10000) -> Proposal | None:
    """Find robust translation B->A, excluding repeated ambiguous anchors.

    No alignment is returned when the evidence is insufficient or ambiguous.
    The input signature must be translation-invariant and preferably B-Rep based.
    """
    if not isfinite(tolerance) or tolerance <= 0 or min_support < 1 or max_hypotheses < 1:
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
    # Exact deduplication only: close hypotheses may have different support at
    # the tolerance boundary and must not be merged.
    hypotheses=list(dict.fromkeys(hypotheses))
    grid=defaultdict(list)
    def cell(v): return tuple(floor(x/tolerance) for x in v)
    for k in keys:
        for x in ga[k]:
            for y in gb[k]:
                delta=tuple(x.center[n]-y.center[n] for n in range(3))
                grid[cell(delta)].append((k,x,y))
    eligible=sum(min(len(ga[k]),len(gb[k])) for k in keys)
    scores=[]
    for shift in hypotheses:
        near=defaultdict(list);c=cell(shift)
        for off in product((-1,0,1),repeat=3):
            for k,x,y in grid.get(tuple(c[n]+off[n] for n in range(3)),()):
                residual=dist(x.center,tuple(y.center[n]+shift[n] for n in range(3)))
                if residual<=tolerance: near[k].append((residual,x.index,y.index))
        pairs=[];families=0
        for candidates in near.values():
            matches=match_candidates(candidates)
            pairs.extend(matches);families+=bool(matches)
        # Two eligible families are insufficient if only one supports this
        # particular vector (a repeated bolt family cannot establish a frame).
        if families>=2:
            scores.append(Proposal(shift,len(pairs),eligible,tuple(sorted(pairs))))
    if not scores:return None
    best=max(scores,key=lambda p:p.support)
    if best.support<min_support:return None
    # Reuse the SAME matching result for ambiguity detection; the previous
    # second pass used a different greedy order and repeated all distances.
    if any(p.support>=best.support and dist(p.shift,best.shift)>tolerance for p in scores):
        return None
    return best

