"""One isolated, fixed-position recovery for a repeated native definition pair.

Both operands receive the same translation. A rigid congruence witness must
also preserve the original placement to certify a stationary occurrence.
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
        self.exhausted_pairs=set()

    def recover(self,i,j,error,progress=None):
        from .geometry import candidate
        from .alignment import _relocate
        from .native_guard import guarded_registered_world, guarded_rigid
        from . import trace_r22 as trace
        family=(self.groups_a[i],self.groups_b[j])
        if min(self.counts_a[family[0]],self.counts_b[family[1]])<2:
            return None
        if 'timeout' not in str(error).casefold() and 'limit' not in str(error).casefold():
            return None
        # The full registered proof has already reached (and timed out in)
        # its final solid subtraction. Recentring and replaying that same
        # pipeline consumed another 75 s without new evidence in 0.6.39.
        # Keep UNKNOWN, and avoid another copy at the same relative pose.
        rigid_witness = any(stage in str(error) for stage in
                            ('validated_solid_symmetric_difference', 'original_equivalent_world'))
        if rigid_witness:
            self.exhausted_pairs.add((i,j))
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
                     'we wspólnym lokalnym układzie, limit {60 if rigid_witness else 75} s.')
        try:
            if rigid_witness:
                # Prove congruence once. Only an effectively identity witness
                # certifies the current placement of this representative.
                match, rotation, translation = trace.brep_call(
                    'repeated_rigid_placement_witness', i, j, guarded_rigid,
                    left, right, self.tolerance, timeout_s=60.,
                    registered_reexport=not candidate(left,right,self.tolerance))
                if not match:
                    return None
                from .world_bounds import WorldBoundsCache
                box = WorldBoundsCache().broad_bounds(right)
                radius = np.linalg.norm(np.maximum(np.abs(box[:3]), np.abs(box[3:])))
                displacement = (np.linalg.norm(translation) +
                                radius * np.linalg.norm(rotation - np.eye(3), ord=2))
                stationary = bool(displacement <= min(1e-6, self.tolerance * .001))
                trace.mark('repeated_rigid_placement_witness', 'PLACEMENT', a_id=i, b_id=j,
                           displacement_bound_mm=float(displacement), stationary=stationary)
                return stationary
            return bool(trace.brep_call('repeated_world_local_recovery',i,j,
                guarded_registered_world,left,right,self.tolerance,timeout_s=75.0))
        except NativeGeometryFailure as exc:
            trace.mark('repeated_world_local_recovery','UNVERIFIED',a_id=i,b_id=j,error=str(exc))
            return None
