"""Conservative rigid-pose proposals for CAD assemblies.

Volume descriptors and centroid consensus are SEARCH indices, never geometry
proof. Only the unchanged native B-Rep verifier may certify parts.
"""
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import ceil, floor, isfinite, log
import random
import numpy as np


@dataclass(frozen=True)
class Pose:
    rotation: tuple
    translation: tuple
    support: int
    distinct_definitions: int
    matched_volume: float


def _key(part):
    """Rotation-invariant, coarse descriptor; a collision is harmless here."""
    volume = float(getattr(part, 'volume', 0.0))
    if not isfinite(volume) or volume <= 0.0:
        return None
    area = getattr(part, 'area', None)
    try:
        area = float(area)
    except (TypeError, ValueError):
        area = 0.0
    return (round(log(volume), 3),
            round(log(area), 3) if isfinite(area) and area > 0 else None)


def _spread_sample(ids, centers, limit):
    if len(ids) <= limit:
        return list(ids)
    selected = [max(ids, key=lambda i: (float(np.linalg.norm(centers[i])), -i))]
    while len(selected) < limit:
        remaining = (i for i in ids if i not in selected)
        best = max(remaining, key=lambda i: (
            min(float(np.sum((centers[i]-centers[j])**2)) for j in selected), -i))
        selected.append(best)
    return selected


def _kabsch(b, a):
    """Map B onto A using a proper rotation (det=+1), never a reflection."""
    aa = np.asarray(a, dtype=float)
    bb = np.asarray(b, dtype=float)
    if aa.shape != bb.shape or aa.ndim != 2 or aa.shape[1] != 3 or len(aa) < 3:
        return None
    ca, cb = aa.mean(axis=0), bb.mean(axis=0)
    x, y = bb-cb, aa-ca
    if np.linalg.matrix_rank(x, tol=1e-8) < 2 or np.linalg.matrix_rank(y, tol=1e-8) < 2:
        return None
    u, _, vt = np.linalg.svd(x.T @ y)
    flip = np.eye(3)
    flip[-1,-1] = 1.0 if np.linalg.det(u @ vt) > 0 else -1.0
    row_rotation = u @ flip @ vt
    rotation = row_rotation.T
    translation = ca - cb @ rotation.T
    if not (np.isfinite(rotation).all() and np.isfinite(translation).all()):
        return None
    return rotation, translation


def _evaluate(rotation, translation, a_centers, b_centers, a_groups, b_groups, gate):
    """One-to-one coarse centroid support; never a geometry verdict."""
    moved_b = b_centers @ rotation.T + translation
    neighbors = [(x,y,z) for x in (-1,0,1) for y in (-1,0,1)
                 for z in (-1,0,1)]
    chosen = []
    distinct = 0
    for key in a_groups.keys() & b_groups.keys():
        cells = defaultdict(list)
        for i in a_groups[key]:
            cell = tuple(floor(float(v)/gate) for v in a_centers[i])
            cells[cell].append(i)
        used = set()
        group_matches = 0
        for j in b_groups[key]:
            pos = moved_b[j]
            origin = tuple(floor(float(v)/gate) for v in pos)
            near = []
            for shift in neighbors:
                cell = tuple(origin[k]+shift[k] for k in range(3))
                near.extend(i for i in cells.get(cell, ()) if i not in used)
            if near:
                i = min(near, key=lambda idx: float(np.linalg.norm(a_centers[idx]-pos)))
                if np.linalg.norm(a_centers[i]-pos) <= gate:
                    used.add(i)
                    chosen.append((i,j))
                    group_matches += 1
        if group_matches:
            distinct += 1
    return chosen, distinct


def propose_rigid_hypotheses(a, b, tolerance, *, max_hypotheses=4, max_trials=900):
    """Deterministic distance-invariant RANSAC with centroid-only refinement.

    Missing/revised occurrences are allowed. No part names or Boolean
    operations participate in hypothesis generation.
    """
    if len(a) < 3 or len(b) < 3 or not isfinite(float(tolerance)) or tolerance <= 0:
        return []
    centers_a = np.asarray([p.center for p in a], dtype=float)
    centers_b = np.asarray([p.center for p in b], dtype=float)
    if not (np.isfinite(centers_a).all() and np.isfinite(centers_b).all()):
        return []
    groups_a, groups_b = defaultdict(list), defaultdict(list)
    for i,p in enumerate(a):
        key = _key(p)
        if key is not None:
            groups_a[key].append(i)
    for j,p in enumerate(b):
        key = _key(p)
        if key is not None:
            groups_b[key].append(j)
    common = groups_a.keys() & groups_b.keys()
    if not common:
        return []
    sorted_keys = sorted(common, key=lambda k:(
        len(groups_a[k])*len(groups_b[k]), -float(k[0]), str(k)))
    pairs = []
    for key in sorted_keys:
        for i in _spread_sample(groups_a[key], centers_a, 4):
            for j in _spread_sample(groups_b[key], centers_b, 4):
                pairs.append((i,j,key))
        if len(pairs) >= 192:
            break
    pairs = pairs[:192]
    if len(pairs) < 3:
        return []
    # This is a broad PROPOSAL gate only; final native CAD tolerance is unchanged.
    gate = max(0.05, float(tolerance)*5)
    rng = random.Random(19460119)
    triplets = list(combinations(range(min(10,len(pairs))), 3))
    while len(triplets) < max_trials:
        triplets.append(tuple(rng.sample(range(len(pairs)),3)))
    candidates, tested = [], set()
    for triple in triplets[:max_trials]:
        picks = [pairs[i] for i in triple]
        ii, jj = [x[0] for x in picks], [x[1] for x in picks]
        if len(set(ii)) < 3 or len(set(jj)) < 3:
            continue
        pa, pb = centers_a[ii], centers_b[jj]
        if max(np.linalg.norm(pa[x]-pa[y]) for x,y in
               ((0,1),(0,2),(1,2))) < gate*10:
            continue
        if any(abs(np.linalg.norm(pa[x]-pa[y]) -
                   np.linalg.norm(pb[x]-pb[y])) > gate for x,y in
               ((0,1),(0,2),(1,2))):
            continue
        proposal = _kabsch(pb, pa)
        if proposal is None:
            continue
        rotation, offset = proposal
        if (np.linalg.norm(rotation-np.eye(3)) < 1e-8 and
                np.linalg.norm(offset) <= tolerance):
            continue
        digest = (tuple(np.round(rotation.flatten(),4)) +
                  tuple(np.round(offset/max(gate,.001),0)))
        if digest in tested:
            continue
        tested.add(digest)
        chosen, distinct = _evaluate(rotation,offset,centers_a,centers_b,
                                     groups_a,groups_b,gate)
        if len(chosen) < 3:
            continue
        # Constrained point ICP: refine only existing invariant-descriptor
        # correspondence pairs. Do not distort the underlying CAD.
        refined = _kabsch(centers_b[[j for i,j in chosen]],
                          centers_a[[i for i,j in chosen]])
        if refined is not None:
            rr, tt = refined
            newer, newer_distinct = _evaluate(rr,tt,centers_a,centers_b,
                                               groups_a,groups_b,gate)
            if len(newer) >= len(chosen):
                rotation,offset,chosen,distinct = rr,tt,newer,newer_distinct
        volume = sum(float(a[i].volume) for i,j in chosen)
        candidates.append((len(chosen),distinct,volume,rotation,offset))
        if len(candidates) >= 64:
            break
    candidates.sort(key=lambda c:(-c[0],-c[1],-c[2]))
    best = []
    for count,distinct,volume,rotation,offset in candidates:
        if any(np.linalg.norm(rotation-np.asarray(x.rotation)) < 1e-5 and
               np.linalg.norm(offset-np.asarray(x.translation)) <= gate for x in best):
            continue
        best.append(Pose(tuple(tuple(float(y) for y in row) for row in rotation),
                         tuple(float(y) for y in offset),
                         count,distinct,volume))
        if len(best) >= max_hypotheses:
            break
    return best


def _independent_anchors(pairs, parts, tolerance):
    """Require three non-collinear world B-Rep-proven locations."""
    indices = sorted({int(i) for i,j in pairs if 0 <= i < len(parts)})
    if len(indices) < 3:
        return False
    points = np.asarray([parts[i].center for i in indices], dtype=float)
    extent = max(float(np.max(np.linalg.norm(points-points[0],axis=1))),1.0)
    threshold = max(float(tolerance),1e-6)*extent
    for i in range(1,len(points)):
        v = points[i]-points[0]
        for j in range(i+1,len(points)):
            if np.linalg.norm(np.cross(v,points[j]-points[0])) > threshold:
                return True
    return False


def propose_verified_rigid(a,b,baseline,tolerance,progress=None,cancelled=None):
    """B-Rep-validated rigid registration. No unproven parts become SAME/MOVED."""
    from .alignment import _relocate
    from .registration_gate import frame_support, FrameProofCache
    from .compare import Cancelled
    population = min(len(a),len(b))
    poses = propose_rigid_hypotheses(a,b,tolerance,max_hypotheses=3)
    if not poses:
        return None
    if progress:
        progress(f'Wyrównanie sztywne: {len(poses)} kandydatów RANSAC/Kabsch; wymagam dowodów B-Rep.')
    minimum = max(3,ceil(.50*population)) if population<8 else (
        max(5,ceil(.40*population)) if population<40 else 8)
    winners = []
    for pose in poses:
        if cancelled and cancelled():
            raise Cancelled('Przerwano analizę')
        if pose.support <= baseline or pose.support < minimum:
            continue
        rotation = np.asarray(pose.rotation,dtype=float)
        offset = np.asarray(pose.translation,dtype=float)
        moved = [_relocate(p,rotation,offset) for p in b]
        cache = FrameProofCache()
        pre = frame_support(a,moved,tolerance,proofs=24,
                            progress=progress,cancelled=cancelled,proof_cache=cache)
        checked,positive = int(pre['checked']),int(pre['proofs'])
        if (int(pre['count']) < minimum or int(pre['count']) <= baseline or
                checked < min(8,int(pre['count'])) or
                positive < max(3,ceil(.80*checked))):
            continue
        sampled = population >= 80
        if sampled:
            evidence = frame_support(a,moved,tolerance,proofs=48,
                                     progress=progress,cancelled=cancelled,
                                     proof_cache=cache)
        else:
            evidence = frame_support(a,moved,tolerance,verify_all=True,
                                     progress=progress,cancelled=cancelled,
                                     proof_cache=cache)
        checked,positive = int(evidence['checked']),int(evidence['proofs'])
        votes = int(evidence['count'])
        certified = sorted(cache.results)
        if (votes < minimum or votes <= baseline or
                checked < min(8,votes) or
                positive < max(3,ceil(.85*checked)) or
                len(certified) < min(3,positive) or
                not _independent_anchors(certified,a,tolerance)):
            continue
        # Only actual B-Rep-positive pairs contribute to verified volume.
        covered = sum(max(0.,float(a[i].volume)) for i in {i for i,j in certified})
        verified_ratio = covered / max(
            1e-12,sum(max(0.,float(p.volume)) for p in a))
        winners.append((positive,votes,covered,pose,certified,
                        checked,sampled,verified_ratio))
    if not winners:
        return {'status':'unresolved',
                'reason':'RANSAC nie uzyskał niezależnych potwierdzeń B-Rep dla sztywnego położenia.'}
    winners.sort(key=lambda w:(-w[0],-w[2],-w[1]))
    best = winners[0]
    for other in winners[1:]:
        if (other[0]>=ceil(.90*best[0]) and other[2]>=.90*best[2] and
            (np.linalg.norm(np.asarray(other[3].rotation)-np.asarray(best[3].rotation))>1e-5 or
             np.linalg.norm(np.asarray(other[3].translation)-np.asarray(best[3].translation))>tolerance)):
            return {'status':'unresolved',
                    'reason':'Symetryczne położenia mają podobne dowody B-Rep; nie wybrano arbitralnej transformacji.'}
    positive,votes,covered,pose,certified,checked,sampled,verified_ratio = best
    weak = votes < ceil(.50*population) and verified_ratio < .15
    if progress:
        progress(f'Wyrównanie RANSAC: przesunięcie {list(pose.translation)} mm, '
                 f'obrót B→A, potwierdzono {positive}/{checked} próbek B-Rep; '
                 'pozostałe części wymagają końcowej weryfikacji.')
    full_map = certified if not sampled and len(certified)==len(a)==len(b) else []
    return {'status':'registered','method':'rigid_ransac_kabsch_native_brep',
            'translation_B_to_A_mm':list(pose.translation),
            'rotation_B_to_A':[list(row) for row in pose.rotation],
            'votes':votes,'previous_world_matches':baseline,
            'requires_confirmation':bool(weak),
            'verified_volume_ratio':round(verified_ratio,4),
            'support_ratio':round(votes/max(1,population),4),
            'requested':True,'enabled':True,
            'certified_pairs':certified,
            'verification_scope':'sample_then_final_compare' if sampled else 'full_brep',
            'checked_sample_count':checked,'verified_sample_count':positive,
            'full_pair_map':full_map}
