"""Full-patch NURBS equivalence under UV axis swaps/reversals.

A UV reflection changes the parametric normal. It must be compensated by the
TopoDS face orientation; merely ignoring FORWARD/REVERSED is never sufficient.
"""
import numpy as np
from itertools import product


def oriented_surface_equal(left,right,tolerance):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomConvert import GeomConvert_BSplineSurfaceToBezierSurface
    from .parametric_identity import pole_bound
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
                if pole_bound(x[i][j],(p,w))>tolerance:
                    good=False;break
            if not good:break
        if good:return True
    from .bernstein_partition import surfaces_equal
    return surfaces_equal(a.BSpline(),b.BSpline(),required_flip,tolerance)
