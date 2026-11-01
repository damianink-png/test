"""Numerical STEP re-export equivalence, restricted to an independently proven frame.

This verifies actual CAD face types, topology counts, world face bounds, areas
and face centroids. Names and STEP labels NEVER establish equivalence.
Only enabled *after* a strong global-translation consensus. It does not replace
ordinary strict Boolean B-Rep comparison for unchanged CAD frames.
"""
from __future__ import annotations
from collections import defaultdict
from math import floor, sqrt
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS



def _face_type_orientation_compatible(left, right):
    from collections import Counter
    return Counter((f[0], f[1]) for f in left) == Counter((f[0], f[1]) for f in right)


def _perfect_face_owner(options):
    """Iterative augmenting paths; return right-face -> left-face matching."""
    from collections import deque
    # Necessary, never sufficient, perfect-matching conditions.
    # A repeated trimmed face may produce dense candidate lists, but
    # missing/empty right-face coverage means matching is impossible.
    if any(not candidates for candidates in options):
        return None
    if len(set().union(*options)) < len(options):
        return None
    owner, reverse = {}, {}
    for first in sorted(range(len(options)), key=lambda i: len(options[i])):
        queue = deque([first])
        seen_left, seen_right, parent = {first}, set(), {}
        free = None
        while queue and free is None:
            i = queue.popleft()
            for j in options[i]:
                if j in seen_right:
                    continue
                seen_right.add(j)
                parent[j] = i
                if j not in owner:
                    free = j
                    break
                other = owner[j]
                if other not in seen_left:
                    seen_left.add(other)
                    queue.append(other)
        if free is None:
            return None
        while True:
            i = parent[free]
            old = reverse.get(i)
            owner[free] = i
            reverse[i] = free
            if old is None:
                break
            free = old
    return owner

def coarse_candidate(a,b,tol):
    """Only a hypothesis prefilter, never proof of identity."""
    if min(a.volume,b.volume)<=0:return False
    if abs(a.volume-b.volume)>max(1e-3,1e-4*max(a.volume,b.volume)):return False
    if abs(a.area-b.area)>max(1e-3,1e-4*max(a.area,b.area)):return False
    return bool(np.allclose(a.eigenvalues,b.eigenvalues,rtol=2.e-4,atol=.1))


def world_candidate(a,b,tol):
    """Permissive search filter, NEVER identity proof.

    STEP p-curve reconstruction changes integrated properties even when all
    original 3-D surfaces and oriented trims agree within the requested tol.
    Volume differences cannot replace the full geometric proof. Area remains
    a coarse proposal filter to avoid filling sparse-revision samples with
    unrelated parts; it never establishes a positive geometric result.
    """
    # Integrated mass can drift by >3% on the captured 52-face STEP pair
    # despite unchanged analytic supports and trims. It cannot reject the
    # independent complete geometric proof. Spatial lookup remains bounded.
    return (all(np.isfinite(v) and v>0 for v in (a.volume,b.volume,a.area,b.area))
            and abs(a.area-b.area)<=max(1.,.02*max(a.area,b.area)))

def search_radius(tolerance):
    # Integrated centroids are not geometric bounds. This radius is only for
    # candidate lookup; exact solid/face bounds retain the user's tolerance.
    # Captured folded STEP patches changed the integrated solid centroid by
    # 0.199 mm while every original surface and trim still matched at 0.01 mm.
    # This is a lookup radius only; no geometric proof budget is increased.
    return max(float(tolerance),.5)


def _faces(part):
    result=[]
    ex=TopExp_Explorer(part.shape,TopAbs_FACE)
    while ex.More():
        f=TopoDS.Face_s(ex.Current())
        p=GProp_GProps();BRepGProp.SurfaceProperties_s(f,p)
        center=p.CentreOfMass()
        bound=Bnd_Box();BRepBndLib.AddOptimal_s(f,bound,False,False)
        result.append((str(BRepAdaptor_Surface(f).GetType()),int(f.Orientation()),float(p.Mass()),
                       np.array([center.X(),center.Y(),center.Z()]),np.array(bound.Get())))
        ex.Next()
    return result


def reexport_equivalent_world(a,b,tolerance=.01, *, allow_boolean=True, progress=None, _repair_boundary_only=False, _original_boundary_only=False):
    """Face prefilter followed by independent solid Boolean verification.

    Small STEP round-trip fluctuations are permitted only within the supplied
    coordinate tolerance; a truly added/removed feature changes the face set
    or fails an original-face geometry requirement. A positive result does not
    mean byte-identical STEP files.
    """
    # Original-to-original proof spends no budget on repair displacement.
    # Ordinary faces retain the half-budget surface/curve proof. Collapsed
    # micro-cylinders instead have a direct uniform bound for their complete
    # patches and real line edges, with no repair displacement to budget.
    # Repair proof keeps its separate, stricter budget and policy.
    if _original_boundary_only and (allow_boolean or _repair_boundary_only):
        raise ValueError('Original boundary proof cannot repair or use Booleans')
    report=progress or (lambda phase: None)
    report('prefilter')
    if not world_candidate(a,b,tolerance):return False
    # SolidInfo.bbox uses a conservative, triangulation-inflated bounding box.
    # STEP retransfers can change its deflection by millimetres for the SAME
    # analytic surface. Conservative OCCT bounds below are only a necessary candidate filter; full surface/trim proof is mandatory.
    report('conservative_bounds_prefilter')
    exact_a=Bnd_Box();BRepBndLib.AddOptimal_s(a.shape,exact_a,False,False)
    exact_b=Bnd_Box();BRepBndLib.AddOptimal_s(b.shape,exact_b,False,False)
    # Even AddOptimal returns conservative bounds for some trimmed surfaces.
    # Different endpoints do not prove different geometry after STEP export.
    # Disjoint boxes can reject a pair; overlapping boxes only admit it to
    # the independent oriented surface-and-trim proof below.
    box_a=np.asarray(exact_a.Get());box_b=np.asarray(exact_b.Get())
    if np.any(np.maximum(box_a[:3],box_b[:3])-np.minimum(box_a[3:],box_b[3:])>tolerance):return False
    report('face_descriptors')
    fa=_faces(a);fb=_faces(b)
    if len(fa)!=len(fb) or not fa:return False
    different_orientation=not _face_type_orientation_compatible(fa,fb)
    allow_micro_cylinders=not allow_boolean and not _repair_boundary_only
    actual_a=actual_b=None
    if different_orientation or allow_micro_cylinders:
        from collections import Counter
        if Counter(f[0] for f in fa)!=Counter(f[0] for f in fb):return False
        from .parametric_identity import items,collapsed_strip_orientation,collapsed_cylinder_equal
        actual_a=items(a.shape,TopAbs_FACE,TopoDS.Face_s)
        actual_b=items(b.shape,TopAbs_FACE,TopoDS.Face_s)
    # Spatially indexed CAD face matching handles STEP face ordering changes.
    cell=max(.03,3*tolerance)
    buckets=defaultdict(list)
    box_buckets=defaultdict(list)
    for i,(typ,ori,area,c,box) in enumerate(fb):
        buckets[(typ,ori,*(floor(float(v)/cell) for v in c))].append(i)
        box_buckets[(typ,ori,*(floor(float(v)/cell) for v in box[:3]))].append(i)
    from itertools import product
    offsets=tuple(product((-1,0,1),repeat=3))
    options=[]
    for face_index,(typ,ori,area,c,box) in enumerate(fa):
        index=tuple(floor(float(v)/cell) for v in c)
        box_index=tuple(floor(float(v)/cell) for v in box[:3])
        indices=set()
        for d in offsets:
            indices.update(buckets.get((typ,ori,*(index[k]+d[k] for k in range(3))),()))
            indices.update(box_buckets.get((typ,ori,*(box_index[k]+d[k] for k in range(3))),()))
            if (different_orientation and 'BSpline' in typ) or (allow_micro_cylinders and 'Cylinder' in typ):
                indices.update(buckets.get((typ,1-ori,*(index[k]+d[k] for k in range(3))),()))
                indices.update(box_buckets.get((typ,1-ori,*(box_index[k]+d[k] for k in range(3))),()))
        available=[]
        for j in sorted(indices):
            _,other_ori,area_b,cb,bb=fb[j]
            strip_candidate=bool(ori!=other_ori and collapsed_strip_orientation(actual_a[face_index],actual_b[j],tolerance))
            micro_candidate=bool(allow_micro_cylinders and collapsed_cylinder_equal(actual_a[face_index],actual_b[j],tolerance))
            if ori!=other_ori and not (strip_candidate or micro_candidate):continue
            dc=float(np.linalg.norm(c-cb))
            db=float(np.max(np.abs(box-bb)))
            # Both are lookup filters. The original strict face/wire proof
            # below remains mandatory and uses the original tolerance.
            if dc>tolerance and db>tolerance and not (strip_candidate or micro_candidate):continue
            da=abs(area-area_b)
            area_lim=max(.1,2*tolerance*sqrt(max(1.,area,area_b)))
            # Integrated area is numerically unstable on folded STEP patches.
            # Use it to rank candidates only; the complete parametric surface
            # and every oriented trim must independently agree below.
            # Conservative analytic-face AABBs can differ after STEP re-export.
            # A near centroid admits only a candidate; full face/wire proof follows.
            score=min(dc,db)/max(tolerance,1e-6)+da/area_lim+int(ori!=other_ori)
            available.append((score,j))
        if not available:return False
        options.append([j for score,j in sorted(available)])
    # Maximum bipartite matching, no recursion or geometric shortcuts.
    owner=_perfect_face_owner(options)
    if owner is None:return False
    if len(owner)!=len(fa):return False
    report('solid_validity')
    if not shape_valid(a.shape) or not shape_valid(b.shape):
        if not (_repair_boundary_only or _original_boundary_only) or allow_boolean:return False
    from .parametric_identity import prove
    report('surface_and_trim_proof')
    if _original_boundary_only:
        return bool(prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=False,
                          allow_original_micro_degenerate=True,allow_micro_cylinders=True))
    if (prove(a.shape,b.shape,owner,fa,tolerance) or (not allow_boolean and not _repair_boundary_only and prove(a.shape,b.shape,owner,fa,tolerance,strict_repair=False,allow_strip_orientation=True,allow_original_micro_degenerate=True,allow_micro_cylinders=True))):return True
    if _repair_boundary_only:return False  # No volume-based repair proof
    report('boolean_residual' if allow_boolean else 'inconclusive')
    return _verified_difference_empty(a.shape,b.shape,tolerance) if allow_boolean else False


def shape_valid(shape):
    from OCP.BRepCheck import BRepCheck_Analyzer
    return not shape.IsNull() and BRepCheck_Analyzer(shape).IsValid()


def _verified_difference_empty(a,b,tolerance):
    """Build intersections once, then verify both independent residual regions."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BOPAlgo import BOPAlgo_PaveFiller
    from OCP.TopTools import TopTools_ListOfShape
    from .material_deltas import volume
    if not np.isfinite(tolerance) or tolerance<=0:return False
    arguments=TopTools_ListOfShape();arguments.Append(a);arguments.Append(b)
    filler=BOPAlgo_PaveFiller();filler.SetArguments(arguments)
    filler.SetNonDestructive(True);filler.SetFuzzyValue(float(tolerance));filler.Perform()
    if filler.HasErrors():return False
    for first,second in ((a,b),(b,a)):
        left=TopTools_ListOfShape();left.Append(first)
        right=TopTools_ListOfShape();right.Append(second)
        op=BRepAlgoAPI_Cut(filler)
        try:
            op.SetArguments(left);op.SetTools(right)
            op.SetNonDestructive(True);op.SetFuzzyValue(float(tolerance));op.Build()
            if not op.IsDone():return False
            residual=op.Shape()
            if not shape_valid(residual):return False
            if volume(residual)>tolerance**3:return False
        finally:
            # The operator borrows the native filler; destroy it first.
            del op
    return True
