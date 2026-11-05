"""Refine translation proposals from original CAD bounds, never certify parts.

Integrated STEP centroids can drift while the actual surfaces stay unchanged.
Bounds are search hints only: all resulting poses still need native B-Rep proof.
"""
import numpy as np


def refine_translations(a, b, offsets, tolerance, cancelled=None):
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    from .compare import _spatial_index, _nearby, Cancelled
    from .registration_gate import _select_diverse_proof_pairs
    from .step_reexport_tolerance import world_candidate, search_radius
    from types import SimpleNamespace

    radius=search_radius(tolerance)
    cells=_spatial_index(a,range(len(a)),radius)
    bounds={}
    def bound(side,index):
        key=(side,index)
        if key not in bounds:
            box=Bnd_Box()
            BRepBndLib.AddOptimal_s((a if side=='a' else b)[index].shape,box,False,False)
            if box.IsVoid() or box.IsOpen():
                bounds[key]=None
            else:
                values=np.asarray(box.Get(),dtype=float)
                bounds[key]=values if np.isfinite(values).all() else None
        return bounds[key]
    proposals=[]
    for seed in list(offsets)[:4]:
        if cancelled and cancelled():raise Cancelled('Przerwano analizę')
        pairs=[];used=set()
        for j,p in enumerate(b):
            center=p.center+seed
            choices=[i for i in _nearby(cells,SimpleNamespace(center=center),radius)
                     if i not in used and np.linalg.norm(a[i].center-center)<=radius
                     and world_candidate(a[i],p,tolerance)]
            if choices:
                i=min(choices,key=lambda i:(np.linalg.norm(a[i].center-center),i))
                used.add(i);pairs.append((i,j))
        shifts=[]
        for i,j in _select_diverse_proof_pairs(pairs,a,12):
            if cancelled and cancelled():raise Cancelled('Przerwano analizę')
            aa,bb=bound('a',i),bound('b',j)
            if aa is None or bb is None:continue
            lower,upper=aa[:3]-bb[:3],aa[3:]-bb[3:]
            # Different extents cannot refine a pure translation. Conservative
            # bounds may miss a useful proposal, but can never prove identity.
            if np.max(np.abs(lower-upper))>max(2*tolerance,1e-6):continue
            shift=(lower+upper)*.5
            if np.linalg.norm(shift-seed)>2*radius:continue
            shifts.append(shift)
        if shifts:
            for shift in [np.median(shifts,axis=0),*shifts]:
                if (np.linalg.norm(shift)>tolerance and
                    not any(np.linalg.norm(shift-old)<=tolerance*.1 for old in proposals)):
                    proposals.append(shift)
    return proposals
