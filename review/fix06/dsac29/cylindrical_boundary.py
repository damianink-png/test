"""Bound rational patches against analytic surfaces of revolution."""
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


def _positive(net, margin, depth=0):
    """Prove positivity everywhere by convex hulls of Bernstein coefficients."""
    if net.min() > margin:
        return True
    if depth >= 10 or np.min(net[np.ix_([0,-1],[0,-1])]) <= margin:
        return False
    variation = [np.max(abs(np.diff(net,axis=k))) if net.shape[k]>1 else 0. for k in (0,1)]
    axis = int(np.argmax(variation))
    level = np.moveaxis(net,axis,0)
    left, right = [level[0]], [level[-1]]
    while len(level)>1:
        level = (level[:-1]+level[1:])*.5
        left.append(level[0])
        right.append(level[-1])
    return all(_positive(np.moveaxis(np.array(half),0,axis),margin,depth+1)
               for half in (left,right[::-1]))


def _radial_match(x, y, w, error, details=None):
    # With positive weights, these two polynomials enclose the squared
    # radius over the complete rational patch. The original control hull
    # can straddle the limit even for a very accurate cubic arc.
    numerator = _multiply(x, x) + _multiply(y, y)
    denominator = _multiply(w, w)
    if not np.isfinite(numerator).all() or not np.isfinite(denominator).all():
        return False
    margin = 64*np.finfo(float).eps*max(1.,np.max(abs(numerator)),np.max(denominator))
    good = (_positive(numerator-(1.-error)**2*denominator,margin)
            and _positive((1.+error)**2*denominator-numerator,margin))
    if not good and details is not None:
        ratio = numerator/denominator
        details.update(reason='radial_bound', squared_radius_ratio_hull=(float(ratio.min()),float(ratio.max())))
    return good


def _product_range(a, b):
    products = (a.min()*b.min(), a.min()*b.max(), a.max()*b.min(), a.max()*b.max())
    return min(products), max(products)


def _local_net(patch,frame,origin):
    u_count, v_count = patch.NbUPoles(), patch.NbVPoles()
    poles = np.array([[patch.Pole(u, v).Coord() for v in range(1, v_count+1)]
                      for u in range(1, u_count+1)])
    w = np.array([[patch.Weight(u, v) for v in range(1, v_count+1)]
                  for u in range(1, u_count+1)])
    if not np.isfinite(poles).all() or not np.isfinite(w).all() or w.min() <= 0:
        return None
    w /= w.max()
    if w.min() < 1e-8:
        return None

    points = (poles-origin) @ frame.T
    return points,w


def _patch_matches(patch, frame, origin, radius, radius_error, orientation, details):
    net = _local_net(patch,frame,origin)
    if net is None:
        return False
    points,w = net
    points[..., :2] /= radius
    heights = points[..., 2] - points[0, 0, 2]
    height = np.abs(heights).max()
    if height <= 0:
        return False
    x, y = np.moveaxis(points[..., :2] * w[..., None], -1, 0)
    z = heights / height * w
    if not _radial_match(x, y, w, radius_error, details):
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
    if (lo-other_hi > margin if orientation > 0 else other_lo-hi > margin):
        return True
    # Products taken separately lose their correlation for a skewed UV
    # parameterization. Bound the signed determinant itself before rejecting.
    jacobian = orientation*(_multiply(angle_u,height_v)-_multiply(angle_v,height_u))
    good = np.isfinite(jacobian).all() and _positive(jacobian,margin)
    if not good and details is not None:
        details.update(reason='oriented_jacobian',jacobian_hull=(float(jacobian.min()),float(jacobian.max())))
    return good


def _torus_orientation(points,w,sense,depth=0):
    """Bound the signed surface normal against the normal of the torus tube."""
    h = points*w[...,None]
    # A common offset cancels in rational derivatives and tightens the bounds.
    local = (points-points[0,0])*w[...,None]
    tangents = []
    for axis in (0,1):
        dw = np.diff(w,axis=axis)
        tangents.append([_multiply(w,np.diff(local[...,k],axis=axis))-_multiply(local[...,k],dw)
                         for k in range(3)])
    du,dv = tangents
    def bounds(v):
        return np.array([v.min(),v.max()])
    cross = []
    for i,j in ((1,2),(2,0),(0,1)):
        cross.append(np.array(_product_range(du[i],dv[j]))-np.array(_product_range(du[j],dv[i]))[::-1])
    xyz = [bounds(points[...,k]) for k in range(3)]
    # With the major radius normalized to one, the nearest tube normal
    # is proportional to (x*(1-1/rho), y*(1-1/rho), z).
    low = np.hypot(*(max(0.,v[0],-v[1]) for v in xyz[:2]))
    high = np.hypot(*(max(abs(v)) for v in xyz[:2]))
    if low>1e-12:
        factor = 1.-1./np.array([low,high])
        normal = [np.array(_product_range(v,factor)) for v in xyz[:2]]+[xyz[2]]
        terms = np.array([_product_range(c,n*sense) for c,n in zip(cross,normal)])
        margin = 1e-12*max(1e-15,np.abs(terms).sum())
        if terms[:,0].sum()>margin:
            return True
        if terms[:,1].sum()<=margin:
            return False
    if depth>=10:
        return False
    axis = depth%2
    level = np.moveaxis(np.concatenate((h,w[...,None]),axis=-1),axis,0)
    left,right = [level[0]],[level[-1]]
    while len(level)>1:
        level = (level[:-1]+level[1:])*.5
        left.append(level[0])
        right.append(level[-1])
    for half in (left,right[::-1]):
        part = np.moveaxis(np.array(half),0,axis)
        weights = part[...,3]
        if not _torus_orientation(part[...,:3]/weights[...,None],weights,sense,depth+1):
            return False
    return True


def _torus_patch(patch,frame,origin,major,minor,tolerance,orientation,details):
    net = _local_net(patch,frame,origin)
    if net is None:
        return False
    points,w = net
    points /= major
    x,y,z = np.moveaxis(points*w[...,None],-1,0)
    ww = _multiply(w,w)
    xy = _multiply(x,x)+_multiply(y,y)
    base = xy+_multiply(z,z)+ww
    radial = 4.*_multiply(xy,ww)
    # For a ring torus F(s) factors as (distance_to_core**2-s**2)
    # times a strictly positive factor. Test both bounding tubes in mm.
    for radius,sign in ((minor-tolerance,1.),(minor+tolerance,-1.)):
        offset = base-(radius/major)**2*ww
        square = _multiply(offset,offset)
        margin = 256*np.finfo(float).eps*max(1.,abs(square).max(),abs(radial).max())
        if not _positive(sign*(square-radial),margin):
            if details is not None:
                details['reason']='torus_tube_bound'
            return False
    if not _torus_orientation(points,w,orientation):
        if details is not None:
            details['reason']='torus_orientation'
        return False
    return True


def _axis_segments(knots, lo, hi, periodic):
    # Outside a nonperiodic domain OCCT evaluates the terminal polynomial.
    # A periodic domain instead wraps the requested interval around the seam.
    if not np.isfinite([lo,hi]).all() or not lo < hi or not np.all(np.diff(knots)>0):
        return []
    shifts = (0.,)
    if periodic:
        period = knots[-1]-knots[0]
        if hi-lo > period*(1.+1e-12):
            return []
        shift = np.floor((lo-knots[0])/period)*period
        shifts = (shift,shift+period,shift+2*period)
    result = []
    for shift in shifts:
        for i,(first,last) in enumerate(zip(knots[:-1],knots[1:])):
            a,b = first+shift,last+shift
            low = lo if i==0 and not periodic else max(lo,a)
            high = hi if i==len(knots)-2 and not periodic else min(hi,b)
            if high > low:
                result.append((i+1,(low-a)/(last-first),(high-a)/(last-first)))
    if not periodic:
        return result
    merged = []
    for i,a,b in sorted(result):
        if merged and merged[-1][0]==i and a<=merged[-1][2]:
            merged[-1] = (i,merged[-1][1],max(b,merged[-1][2]))
        else:
            merged.append((i,a,b))
    return merged


def equivalent(a, b, tolerance, details=None):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_BSplineSurface, GeomAbs_Cylinder, GeomAbs_Torus
    from OCP.GeomConvert import GeomConvert_BSplineSurfaceToBezierSurface
    from OCP.Precision import Precision
    from OCP.TColStd import TColStd_Array1OfReal

    left, right = BRepAdaptor_Surface(a), BRepAdaptor_Surface(b)
    if left.GetType() not in (GeomAbs_Cylinder,GeomAbs_Torus):
        a, b = b, a
        left, right = right, left
    if left.GetType() not in (GeomAbs_Cylinder,GeomAbs_Torus) or right.GetType() != GeomAbs_BSplineSurface:
        return False
    if any(int(face.Orientation()) not in (0, 1) for face in (a, b)):
        return False
    toroidal = left.GetType()==GeomAbs_Torus
    carrier = left.Torus() if toroidal else left.Cylinder()
    radius = carrier.MajorRadius() if toroidal else carrier.Radius()
    if toroidal:
        minor = carrier.MinorRadius()
        if details is not None:
            details.update(minor_radius_mm=minor,reason='unsupported_torus')
        if not tolerance < minor < radius-tolerance:
            return False
    if radius <= Precision.Confusion_s():
        return False
    radius_error = min(.25, tolerance/radius)-1e-12
    if radius_error <= 0:
        return False

    spline = right.BSpline()
    bounds = (right.FirstUParameter(), right.LastUParameter(),
              right.FirstVParameter(), right.LastVParameter())
    if details is not None:
        details.update(reason='spline_layout',radius_mm=radius,tol_mm=tolerance,
                       degree=(spline.UDegree(),spline.VDegree()),knots=(spline.NbUKnots(),spline.NbVKnots()),
                       trim=bounds,support=spline.Bounds(), orientations=(int(a.Orientation()),int(b.Orientation())))
    if max(spline.UDegree(), spline.VDegree()) > 8 or spline.NbUKnots()*spline.NbVKnots() > 4096:
        return False
    spans = GeomConvert_BSplineSurfaceToBezierSurface(spline)
    axes_segments = []
    for axis,lo,hi in (('U',*bounds[:2]),('V',*bounds[2:])):
        knots = TColStd_Array1OfReal(1,getattr(spans,'Nb'+axis+'Patches')()+1)
        getattr(spans,axis+'Knots')(knots)
        axes_segments.append(_axis_segments(np.asarray(list(knots)),lo,hi,getattr(spline,'Is'+axis+'Periodic')()))
    if not 0 < len(axes_segments[0])*len(axes_segments[1]) <= 1024:
        return False

    axes = carrier.Position()
    x, y = axes.XDirection().Coord(), axes.YDirection().Coord()
    normal = np.cross(x, y)
    frame = np.asarray((x, y, normal))
    orientation = np.dot(normal, axes.Direction().Coord())
    if a.Orientation() != b.Orientation():
        orientation = -orientation
    origin = np.array(carrier.Location().Coord())
    for i,u0,u1 in axes_segments[0]:
        for j,v0,v1 in axes_segments[1]:
            patch = spans.Patch(i,j)
            if (u0,u1,v0,v1) != (0.,1.,0.,1.):
                patch = patch.Copy()
                patch.Segment(u0,u1,v0,v1)
            good = (_torus_patch(patch,frame,origin,radius,minor,tolerance,orientation,details)
                    if toroidal else _patch_matches(patch,frame,origin,radius,radius_error,orientation,details))
            if not good:
                if details is not None:
                    details['patch'] = (i,j)
                    if details['reason'] in ('radial_bound','torus_tube_bound'):
                        # Diagnostics only. Samples do not certify a surface.
                        probes = np.array([patch.Value(u,v).Coord() for u in (0.,.5,1.) for v in (0.,.5,1.)])
                        local = (probes-origin) @ frame.T
                        radii = np.linalg.norm(local[:,:2],axis=1)
                        if toroidal:
                            tube_radii = np.hypot(radii-radius,local[:,2])
                            details['probe_tube_error_mm'] = float(np.max(np.abs(tube_radii-minor)))
                        else:
                            details['probe_radial_error_mm'] = float(np.max(np.abs(radii-radius)))
                    if details['reason']=='spline_layout':
                        details['reason'] = 'degenerate_or_weights'
                return False
    if details is not None:
        details['reason'] = 'torus_surface_proven' if toroidal else 'cylinder_surface_proven'
    return True


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
    from OCP.BRep import BRep_Tool
    from .parametric_identity import edge_data, edge_equal

    try:
        left, right = BRepAdaptor_Curve(a), BRepAdaptor_Curve(b)
        closed = BRep_Tool.IsClosed_s(a) and BRep_Tool.IsClosed_s(b)
        if closed and left.GetType() == right.GetType() == GeomAbs_Circle:
            x, y = edge_data(a), edge_data(b)
            return (all(abs(d[6]-2*np.pi) <= 1e-12 for d in (x,y))
                    and edge_equal(x,y,tolerance))
        if left.GetType() == right.GetType() == GeomAbs_BSplineCurve:
            from OCP.GC import GC_MakeCircle
            from OCP.ElCLib import ElCLib
            from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
            from OCP.TopoDS import TopoDS
            lo, hi = left.FirstParameter(), left.LastParameter()
            start, end = left.Value(lo), left.Value(hi)
            guess = GC_MakeCircle(start, left.Value(lo+(hi-lo)/3), left.Value(lo+2*(hi-lo)/3))
            if not guess.IsDone():
                return False
            circle = guess.Value().Circ()
            first = ElCLib.Parameter_s(circle, start)
            sweep = (ElCLib.Parameter_s(circle, end)-first) % (2*np.pi)
            if start.Distance(end) < 1e-8:
                sweep = 2*np.pi
            builder = BRepBuilderAPI_MakeEdge(circle, first, first+sweep)
            if not builder.IsDone():
                return False
            reference = TopoDS.Edge_s(builder.Edge().Oriented(a.Orientation()))
            return (circular_edge_equal(reference, a, tolerance/2)
                    and circular_edge_equal(reference, b, tolerance/2))
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
        full = closed and abs(sweep-2*np.pi) <= 1e-12
        if not full and max(np.linalg.norm(start-arcs[0][0][0]), np.linalg.norm(end-arcs[-1][0][-1])) > tolerance/2:
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
            arc_error = error
            if full:
                # Radial and axial deviations are orthogonal. Reserve half
                # the distance budget for any angular gap at the closure.
                axial = np.max(np.abs(local[:,2]))
                radial = np.sqrt((tolerance/2)**2-axial**2)
                arc_error = min(.25,radial/radius)-1e-12
            arc = _arc_sweep(np.column_stack((local[:, :2]*weights[:, None]/radius, weights)), arc_error)
            if arc is None:
                return False
            total += arc
        return bool(abs(total-sweep)*radius <= tolerance/2)
    except Exception:
        return False
