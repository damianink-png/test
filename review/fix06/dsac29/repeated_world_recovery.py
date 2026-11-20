"""One isolated, fixed-position recovery for a repeated native definition pair.

Both operands receive the SAME translation. No rotation/translation fitting,
name matching, volume heuristic, or mesh can certify equality here.
"""
from collections import Counter, defaultdict
import numpy as np
from .native_guard import NativeGeometryFailure


class RepeatedWorldRecovery:
    def __init__(self, a, b, groups_a, groups_b, tolerance):
        self.a,self.b=a,b
        self.groups_a,self.groups_b=groups_a,groups_b
        self.counts_a,self.counts_b=Counter(groups_a),Counter(groups_b)
        self.tolerance=tolerance
        self.attempts=defaultdict(list)

    def recover(self,i,j,error,progress=None):
        from .compare import _relative_location_is_same
        from .alignment import _relocate
        from .native_guard import guarded_registered_world
        from . import trace_r22 as trace
        family=(self.groups_a[i],self.groups_b[j])
        if min(self.counts_a[family[0]],self.counts_b[family[1]])<2:
            return None
        if 'timeout' not in str(error).casefold() and 'limit' not in str(error).casefold():
            return None
        if any(_relative_location_is_same(self.a[i],self.a[x],self.b[j],self.b[y],1e-8)
               for x,y in self.attempts[family]):
            return None
        # Cap attempts per native family too: different relative placements
        # must not launch an unbounded search through its Cartesian pairs.
        if self.attempts[family]:return None
        self.attempts[family].append((i,j))
        origin=(np.asarray(self.a[i].center)+np.asarray(self.b[j].center))*.5
        if not np.isfinite(origin).all():return None
        left=_relocate(self.a[i],np.eye(3),-origin)
        right=_relocate(self.b[j],np.eye(3),-origin)
        if progress:
            progress(f'Powtórzenia: pełna weryfikacja pary A[{i}] / B[{j}] '
                     'we wspólnym lokalnym układzie, bez szukania ruchu; limit 75 s.')
        try:
            return bool(trace.brep_call('repeated_world_local_recovery',i,j,
                guarded_registered_world,left,right,self.tolerance,timeout_s=75.0))
        except NativeGeometryFailure as exc:
            trace.mark('repeated_world_local_recovery','UNVERIFIED',a_id=i,b_id=j,error=str(exc))
            return None
