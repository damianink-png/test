"""Full oriented CAD boundary proof under a proposed native placement.

For an already registered STEP assembly, integrated mass can drift on re-export.
CAD placement matrices propose a proper rigid transform; only all original
surfaces and trims within tolerance can confirm it. Run in a disposable worker.
"""
import numpy as np
from .geometry import describe,transform
from .step_reexport_tolerance import reexport_equivalent_world


def prove_native_placement(a,b,tolerance):
    def matrix(part):
        tr=part.shape.Location().Transformation()
        return np.asarray([[tr.Value(i,j) for j in range(1,5)] for i in range(1,4)],float)
    ma,mb=matrix(a),matrix(b)
    if not np.isfinite(ma).all() or not np.isfinite(mb).all():return False,None,None
    for m in (ma,mb):
        r=m[:,:3]
        if not np.allclose(r.T@r,np.eye(3),rtol=0,atol=1e-9) or abs(np.linalg.det(r)-1.)>1e-9:
            return False,None,None
    rotation=ma[:,:3]@mb[:,:3].T
    offset=ma[:,3]-rotation@mb[:,3]
    proposed=describe(transform(b.shape,rotation,offset),'B','registered-rigid/proposed-B')
    if not reexport_equivalent_world(a,proposed,float(tolerance),allow_boolean=False,_original_boundary_only=True):
        return False,None,None
    return True,rotation,offset
