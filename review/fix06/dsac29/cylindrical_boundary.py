"""Bounds for a rational surface projected onto an analytic cylinder."""
from functools import lru_cache
from math import comb

import numpy as np


@lru_cache(maxsize=32)
def _product_coefficients(left_shape, right_shape):
    def indices_and_weights(shape):
        u, v = np.indices(shape).reshape(2, -1)
        weight = np.array([comb(shape[0]-1, int(i)) * comb(shape[1]-1, int(j))
                           for i, j in zip(u, v)])
        return u, v, weight

    u, v, left_weight = indices_and_weights(left_shape)
    s, t, right_weight = indices_and_weights(right_shape)
    shape = tuple(a+b-1 for a, b in zip(left_shape, right_shape))
    i, j = u[:, None]+s, v[:, None]+t
    _, _, output_weight = indices_and_weights(shape)
    bins = i * shape[1] + j
    scale = left_weight[:, None] * right_weight / output_weight[bins]
    return bins.ravel(), scale, shape


def _multiply(a, b):
    bins, scale, shape = _product_coefficients(a.shape, b.shape)
    terms = a.ravel()[:, None] * b.ravel() * scale
    return np.bincount(bins, terms.ravel(), minlength=shape[0]*shape[1]).reshape(shape)


def _radial_match(x, y, w, error):
    # A quotient of Bernstein polynomials with positive denominator
    # coefficients is bounded by the ratios of corresponding coefficients.
    radial = (_multiply(x, x) + _multiply(y, y)) / _multiply(w, w)
    return bool(np.isfinite(radial).all() and radial.min() >= (1-error)**2
                and radial.max() <= (1+error)**2)


def _product_range(a, b):
    products = (a.min()*b.min(), a.min()*b.max(), a.max()*b.min(), a.max()*b.max())
    return min(products), max(products)


def _patch_matches(patch, frame, origin, radius, radius_error, orientation):
    u_count, v_count = patch.NbUPoles(), patch.NbVPoles()
    poles = np.array([[patch.Pole(u, v).Coord() for v in range(1, v_count+1)]
                      for u in range(1, u_count+1)])
    w = np.array([[patch.Weight(u, v) for v in range(1, v_count+1)]
                  for u in range(1, u_count+1)])
    if not np.isfinite(poles).all() or not np.isfinite(w).all() or w.min() <= 0:
        return False
    w /= w.max()
    if w.min() < 1e-8:
        return False

    points = (poles-origin) @ frame.T
    points[..., :2] /= radius
    heights = points[..., 2] - points[0, 0, 2]
    height = np.abs(heights).max()
    if height <= 0:
        return False
    x, y = np.moveaxis(points[..., :2] * w[..., None], -1, 0)
    z = heights / height * w
    if not _radial_match(x, y, w, radius_error):
        return False

    # Bound the local Jacobian of (angle, height) in homogeneous coordinates.
    # Positive denominators cancel for its sign. A folded or oppositely
    # oriented patch cannot supply an original-boundary proof.
    def differentiated(axis):
        degree = w.shape[axis] - 1
        dx, dy, dz, dw = (degree*np.diff(net, axis=axis) for net in (x, y, z, w))
        return (_multiply(x, dy)-_multiply(y, dx), _multiply(w, dz)-_multiply(z, dw))

    angle_u, height_u = differentiated(0)
    angle_v, height_v = differentiated(1)
    lo, hi = _product_range(angle_u, height_v)
    other_lo, other_hi = _product_range(angle_v, height_u)
    margin = 1e-12 * max(1., abs(lo), abs(hi), abs(other_lo), abs(other_hi))
    return bool(lo-other_hi > margin if orientation > 0 else other_lo-hi > margin)


def equivalent(a, b, tolerance):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_BSplineSurface, GeomAbs_Cylinder
    from OCP.GeomConvert import GeomConvert_BSplineSurfaceToBezierSurface
    from OCP.Precision import Precision

    left, right = BRepAdaptor_Surface(a), BRepAdaptor_Surface(b)
    if left.GetType() != GeomAbs_Cylinder:
        a, b = b, a
        left, right = right, left
    if left.GetType() != GeomAbs_Cylinder or right.GetType() != GeomAbs_BSplineSurface:
        return False
    if any(int(face.Orientation()) not in (0, 1) for face in (a, b)):
        return False
    cylinder = left.Cylinder()
    radius = cylinder.Radius()
    if radius <= Precision.Confusion_s():
        return False
    radius_error = min(.25, tolerance/radius)-1e-12
    if radius_error <= 0:
        return False

    spline = right.BSpline()
    if max(spline.UDegree(), spline.VDegree()) > 8 or spline.NbUKnots()*spline.NbVKnots() > 512:
        return False
    bounds = (right.FirstUParameter(), right.LastUParameter(),
              right.FirstVParameter(), right.LastVParameter())
    if not np.isfinite(bounds).all():
        return False
    spans = GeomConvert_BSplineSurfaceToBezierSurface(spline, *bounds, Precision.PConfusion_s())
    if not 0 < spans.NbUPatches()*spans.NbVPatches() <= 256:
        return False

    axes = cylinder.Position()
    x, y = axes.XDirection().Coord(), axes.YDirection().Coord()
    normal = np.cross(x, y)
    frame = np.asarray((x, y, normal))
    orientation = np.dot(normal, axes.Direction().Coord())
    if a.Orientation() != b.Orientation():
        orientation = -orientation
    origin = np.array(cylinder.Location().Coord())
    return all(_patch_matches(spans.Patch(u, v), frame, origin, radius, radius_error, orientation)
               for u in range(1, spans.NbUPatches()+1) for v in range(1, spans.NbVPatches()+1))


def _arc_sweep(net, error, depth=0):
    # Restrict with exact homogeneous de Casteljau subdivision until the
    # whole arc is in a half-plane. Then its oriented angle cannot wrap.
    xy = net[:, :2]
    if np.all(xy @ (xy[0]+xy[-1]) > 1e-12):
        x, y, w = net.T[:, :, None]
        degree = len(net)-1
        derivative = degree*(_multiply(x, np.diff(y, axis=0))-_multiply(y, np.diff(x, axis=0)))
        if _radial_match(x, y, w, error) and derivative.min() > 1e-12:
            start, end = xy[0], xy[-1]
            return np.arctan2(start[0]*end[1]-start[1]*end[0], start @ end)
    if depth >= 8:
        return None
    first, last = [net[0]], [net[-1]]
    while len(net) > 1:
        net = (net[:-1] + net[1:]) * .5
        first.append(net[0])
        last.append(net[-1])
    a = _arc_sweep(np.array(first), error, depth+1)
    if a is None:
        return None
    b = _arc_sweep(np.array(last[::-1]), error, depth+1)
    return None if b is None else a+b


def circular_edge_equal(a, b, tolerance):
    """Prove one analytic circle and its oriented rational trimming curve."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_BSplineCurve, GeomAbs_Circle
    from .parametric_identity import edge_data

    try:
        left, right = BRepAdaptor_Curve(a), BRepAdaptor_Curve(b)
        if left.GetType() != GeomAbs_Circle:
            a, b = b, a
            left, right = right, left
        if left.GetType() != GeomAbs_Circle or right.GetType() != GeomAbs_BSplineCurve:
            return False
        if any(int(edge.Orientation()) not in (0, 1) for edge in (a, b)):
            return False
        _, start, end, origin, radius, _, sweep = edge_data(a)
        data = edge_data(b, force_spline=True)
        if data[0]!='bezier' or not 0 < len(data[1]) <= 128 or not 0 < sweep <= 2*np.pi+1e-10:
            return False
        arcs = data[1]
        if max(np.linalg.norm(start-arcs[0][0][0]), np.linalg.norm(end-arcs[-1][0][-1])) > tolerance/2:
            return False
        error = min(.25, tolerance/(4*radius))-1e-12
        if error <= 0:
            return False
        axes = left.Circle().Position()
        x, y = np.array(axes.XDirection().Coord()), np.array(axes.YDirection().Coord())
        normal = np.cross(x, y)
        if int(a.Orientation()) == 1:
            y = -y
        frame = np.asarray((x, y, normal))
        total = 0.
        for poles, weights in arcs:
            if not 2 <= len(weights) <= 9 or not np.isfinite(weights).all() or weights.min() <= 0:
                return False
            local = (poles-origin) @ frame.T
            if not np.isfinite(local).all() or np.max(np.abs(local[:, 2])) > tolerance/4:
                return False
            weights = weights / weights.max()
            if weights.min() < 1e-8:
                return False
            arc = _arc_sweep(np.column_stack((local[:, :2]*weights[:, None]/radius, weights)), error)
            if arc is None:
                return False
            total += arc
        return bool(abs(total-sweep)*radius <= tolerance/2)
    except Exception:
        return False
