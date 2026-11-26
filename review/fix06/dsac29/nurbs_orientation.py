"""Full-patch NURBS equivalence under UV axis swaps/reversals.

A UV reflection changes the parametric normal. It must be compensated by the
TopoDS face orientation; merely ignoring FORWARD/REVERSED is never sufficient.
"""
import numpy as np
from itertools import product


def patch_equal(left, right, tolerance):
    """Uniform rational Bézier bound, allowing a monotone UV reparameterization."""
    from .parametric_identity import pole_bound
    from .cylindrical_boundary import _multiply

    p, w = left
    q, v = right
    if not all(np.isfinite(a).all() for a in (p, w, q, v)) or min(w.min(), v.min()) <= 0:
        return False
    corners = ([0, 0, -1, -1], [0, -1, 0, -1])
    if np.max(np.linalg.norm(p[corners]-q[corners], axis=-1)) > tolerance:
        return False
    if pole_bound(left, right) <= tolerance:
        return True
    if p.shape == q.shape and np.all(w == w.flat[0]) and np.all(v == v.flat[0]):
        rounding = 1e-13 * max(1., np.max(abs(p)), np.max(abs(q)))
        return _difference_within(p-q, tolerance-rounding)
    if max(*w.shape, *v.shape) > 9:
        return False

    # Scaling weights by c**i * d**j is a bijective, increasing change of
    # each Bézier parameter fixing 0 and 1. Normalize each patch separately.
    def normalized(weights):
        u, v = weights.shape
        log_w = np.log(weights)
        log_w = (log_w + np.linspace(0., log_w[0,0]-log_w[-1,0], u)[:, None]
                 + np.linspace(0., log_w[0,0]-log_w[0,-1], v))
        return np.exp(log_w-log_w.max())

    # (P/W - Q/V) = (PV - QW)/(WV). Positive denominator coefficients
    # give a convex hull of difference vectors covering the entire patch.
    origin = p[0,0]
    left_points, right_points = p-origin, q-origin
    rounding = 1e-12 * max(1., np.max(abs(left_points)), np.max(abs(right_points)))
    for lw,rw in ((w/w.max(),v/v.max()), (normalized(w),normalized(v))):
        if min(lw.min(), rw.min()) < 1e-8:
            continue
        denominator = _multiply(lw, rw)
        differences = [(_multiply(left_points[...,k]*lw, rw)
                        - _multiply(right_points[...,k]*rw, lw))/denominator for k in range(3)]
        if np.max(np.linalg.norm(differences, axis=0)) + rounding <= tolerance:
            return True
    return False


def oriented_surface_equal(left,right,tolerance):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomConvert import GeomConvert_BSplineSurfaceToBezierSurface
    a,b=BRepAdaptor_Surface(left),BRepAdaptor_Surface(right)
    if not all('BSpline' in str(s.GetType()) for s in (a,b)):return False
    if int(left.Orientation()) not in (0,1) or int(right.Orientation()) not in (0,1):return False
    def patches(surface):
        pieces=GeomConvert_BSplineSurfaceToBezierSurface(surface.BSpline())
        if pieces.NbUPatches()*pieces.NbVPatches()>10000:return None
        grid=[]
        for i in range(1,pieces.NbUPatches()+1):
            row=[]
            for j in range(1,pieces.NbVPatches()+1):
                p=pieces.Patch(i,j)
                row.append((np.array([[p.Pole(u,v).Coord() for v in range(1,p.NbVPoles()+1)] for u in range(1,p.NbUPoles()+1)]),
                            np.array([[p.Weight(u,v) for v in range(1,p.NbVPoles()+1)] for u in range(1,p.NbUPoles()+1)])))
            grid.append(row)
        return grid
    x,y=patches(a),patches(b)
    if x is None or y is None:return False
    required_flip=int(left.Orientation())!=int(right.Orientation())
    for swap,reverse_u,reverse_v in product((False,True),repeat=3):
        if bool(swap^reverse_u^reverse_v)!=required_flip:continue
        grid=[list(row) for row in zip(*y)] if swap else y
        if reverse_u:grid=grid[::-1]
        if reverse_v:grid=[row[::-1] for row in grid]
        if len(x)!=len(grid) or any(len(a)!=len(b) for a,b in zip(x,grid)):continue
        good=True
        for i,row in enumerate(grid):
            for j,(p,w) in enumerate(row):
                if swap:p,w=p.swapaxes(0,1),w.swapaxes(0,1)
                if reverse_u:p,w=p[::-1],w[::-1]
                if reverse_v:p,w=p[:,::-1],w[:,::-1]
                if not patch_equal(x[i][j],(p,w),tolerance):
                    good=False;break
            if not good:break
        if good:return True
    from .bernstein_partition import surfaces_equal
    return surfaces_equal(a.BSpline(),b.BSpline(),required_flip,tolerance)


def _difference_within(net, limit, depth=0):
    """Enclose the polynomial difference everywhere by its Bézier hull."""
    if np.max(np.linalg.norm(net, axis=-1)) <= limit:
        return True
    if depth >= 8 or np.max(np.linalg.norm(net[[0,0,-1,-1],[0,-1,0,-1]], axis=-1)) > limit:
        return False
    axis = depth % 2 if min(net.shape[:2]) > 1 else int(net.shape[0] == 1)
    level = np.moveaxis(net, axis, 0)
    left, right = [level[0]], [level[-1]]
    while len(level) > 1:
        level = (level[:-1]+level[1:])*.5
        left.append(level[0])
        right.append(level[-1])
    return all(_difference_within(np.moveaxis(np.array(half), 0, axis), limit, depth+1)
               for half in (left, right[::-1]))


def native_polynomial_equal(left_face, right_face, tolerance, details=None):
    """Compare original polynomial spans with a bound for unequal trim boxes."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_BSplineSurface
    from OCP.GeomConvert import GeomConvert_BSplineSurfaceToBezierSurface

    def reject(label, reason):
        if details is not None:
            details[label] = reason

    def definition(face, label):
        adaptor = BRepAdaptor_Surface(face)
        if adaptor.GetType() != GeomAbs_BSplineSurface or int(face.Orientation()) not in (0,1):
            reject(label, 'unsupported_face')
            return None
        s = adaptor.BSpline()
        if s.IsURational() or s.IsVRational() or s.IsUPeriodic() or s.IsVPeriodic():
            reject(label, 'rational_or_periodic')
            return None
        domain, basis, overhang, dimensions = [], [], [], []
        for axis in ('U','V'):
            knots = np.asarray(list(getattr(s, axis+'Knots')()), dtype=float)
            mults = tuple(getattr(s, axis+'Multiplicities')())
            basis.append((tuple(knots),mults))
            first = getattr(s,'First'+axis+'KnotIndex')()
            last = getattr(s,'Last'+axis+'KnotIndex')()
            knots = knots[first-1:last]
            dimensions.append(len(knots)-1)
            bounds = [getattr(adaptor,'First'+axis+'Parameter')(), getattr(adaptor,'Last'+axis+'Parameter')()]
            if not np.isfinite(bounds).all() or not bounds[0] < bounds[1]:
                reject(label, axis+'_invalid_domain')
                return None
            # A STEP p-curve may run just outside the support knots. OCCT
            # evaluates the terminal polynomial there. Keep its displacement
            # in the proof budget, measured in units of the terminal span.
            excess = max(0., (knots[0]-bounds[0])/(knots[1]-knots[0]),
                         (bounds[1]-knots[-1])/(knots[-1]-knots[-2]))
            if excess > .01 or bounds[1] <= knots[0] or bounds[0] >= knots[-1]:
                reject(label, f'{axis}_outside_span({excess:.8g})')
                return None
            overhang.append(excess)
            domain.append(np.interp(bounds, knots, np.arange(len(knots))))
        if np.prod(dimensions)*(s.UDegree()+1)*(s.VDegree()+1) > 32768:
            reject(label, 'span_budget')
            return None
        return s, tuple(dimensions), np.asarray(domain), basis, np.array(overhang)

    def extract(s, dimensions):
        spans = GeomConvert_BSplineSurfaceToBezierSurface(s)
        if (spans.NbUPatches(), spans.NbVPatches()) != dimensions:
            return None
        grid = np.empty((*dimensions, s.UDegree()+1, s.VDegree()+1, 3))
        for i,j in np.ndindex(dimensions):
            patch = spans.Patch(i+1,j+1)
            grid[i,j] = [[patch.Pole(u,v).Coord() for v in range(1,patch.NbVPoles()+1)]
                         for u in range(1,patch.NbUPoles()+1)]
        if not np.isfinite(grid).all():
            return None
        return grid

    left, right = definition(left_face,'A'), definition(right_face,'B')
    if left is None or right is None:
        return False
    s, dims_a, bounds_a, basis_a, excess_a = left
    t, dims_b, original_bounds_b, basis_b, excess_b = right
    required_flip = left_face.Orientation() != right_face.Orientation()
    # With identical basis functions the surface difference is a convex
    # combination of corresponding pole differences in the world frame.
    if (not required_flip and not (excess_a.any() or excess_b.any()) and basis_a == basis_b and np.array_equal(bounds_a, original_bounds_b)
            and (s.UDegree(), s.VDegree()) == (t.UDegree(), t.VDegree())):
        def poles(surface):
            return np.asarray([[surface.Pole(i,j).Coord() for j in range(1,surface.NbVPoles()+1)]
                               for i in range(1,surface.NbUPoles()+1)])
        p, q = poles(s), poles(t)
        bound = np.max(np.linalg.norm(p-q, axis=-1)) + 1e-13*max(1.,np.max(abs(p)),np.max(abs(q)))
        if bound <= tolerance:
            if details is not None:
                details['certified'] = float(bound)
            return True

    a, original_b = extract(s,dims_a), extract(t,dims_b)
    if a is None or original_b is None:
        reject('span_layout', 'conversion_failed')
        return False

    def extension_bound(grid, excess):
        if not excess.any():
            return 0.
        # On [-e,1+e] the sum of absolute Bernstein basis values is at
        # most (1+2e)**degree. Apply this to both derivative control nets.
        degrees = np.asarray(grid.shape[2:4])-1
        growth = np.prod((1.+2.*excess)**degrees)
        slopes = [degree*np.max(np.linalg.norm(np.diff(grid,axis=k+2),axis=-1))
                  for k,degree in enumerate(degrees)]
        return float(growth*(excess @ slopes))

    extension = extension_bound(a,excess_a) + extension_bound(original_b,excess_b)
    if details is not None:
        details['extension_mm'] = extension
    for swap,ru,rv in product((False,True),repeat=3):
        if (swap ^ ru ^ rv) != required_flip:
            continue
        b, bounds_b = original_b, original_bounds_b
        if swap:
            b = b.transpose(1,0,3,2,4)
            bounds_b = bounds_b[::-1]
        if b.shape != a.shape:
            continue
        bounds_b = bounds_b.copy()
        if ru:
            b = b[::-1,:,::-1]
            bounds_b[0] = b.shape[0]-bounds_b[0,::-1]
        if rv:
            b = b[:,::-1,:,::-1]
            bounds_b[1] = b.shape[1]-bounds_b[1,::-1]

        # Each span occupies one unit in this coordinate system. The affine
        # map between the face boxes displaces UV by at most these endpoint
        # differences. Bound its world displacement using derivative hulls.
        delta = np.max(np.abs(bounds_a-bounds_b), axis=1)
        lower = np.maximum(0,np.floor(np.minimum(bounds_a[:,0],bounds_b[:,0])).astype(int))
        upper = np.minimum(a.shape[:2],np.ceil(np.maximum(bounds_a[:,1],bounds_b[:,1])).astype(int))
        region = np.s_[lower[0]:upper[0],lower[1]:upper[1]]
        x, y = a[region], b[region]
        if not x.size:
            continue
        slope = [np.max(np.linalg.norm(np.diff(y,axis=k),axis=-1))*(y.shape[k]-1) for k in (2,3)]
        trim_error = float(delta @ slope) + extension
        residual = x-y
        hull = float(np.max(np.linalg.norm(residual,axis=-1)))
        if details is not None and hull+trim_error < details.get('bound',float('inf')):
            details.update(bound=hull+trim_error, poles=hull, trim=trim_error)
        rounding = 1e-13 * max(1.,np.max(abs(x)),np.max(abs(y)))
        limit = tolerance-trim_error-rounding
        if limit > 0 and (hull <= limit or all(_difference_within(residual[i,j],limit)
                                               for i,j in np.ndindex(residual.shape[:2]))):
            if details is not None:
                details['certified'] = min(tolerance, hull+trim_error+rounding)
            return True
    return False
