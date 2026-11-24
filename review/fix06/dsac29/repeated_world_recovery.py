"""One isolated, fixed-position recovery for a repeated native definition pair.

Both operands receive the same translation. A rigid congruence witness must
also preserve the original placement to certify a stationary occurrence.
"""
from collections import Counter
from time import monotonic
import numpy as np
from .native_guard import NativeGeometryFailure


class RepeatedWorldRecovery:
    def __init__(self, a, b, groups_a, groups_b, tolerance, geometry_context=None):
        self.geometry_context=geometry_context
        self.a,self.b=a,b
        self.groups_a,self.groups_b=groups_a,groups_b
        self.counts_a,self.counts_b=Counter(groups_a),Counter(groups_b)
        self.tolerance=tolerance
        self.attempts=set()
        self.exhausted_pairs=set()
        self.alternatives=set()

    def alternative(self,i,j,failed):
        family=(self.groups_a[i],self.groups_b[j])
        if family in self.alternatives or not failed:
            return None
        from .compare import _relative_location_is_same
        for aa,bb in failed:
            if ((aa,bb) in self.exhausted_pairs and i!=aa and j!=bb
                    and _relative_location_is_same(self.a[i],self.a[aa],self.b[j],self.b[bb],self.tolerance)):
                self.alternatives.add(family)
                return (i,j)
        return None

    def verify_alternative(self,i,j,progress=None):
        from .alignment import _relocate
        from .native_guard import guarded_world_reexport
        from . import trace_r22 as trace
        center=(np.asarray(self.a[i].center)+np.asarray(self.b[j].center))*.5
        if not np.isfinite(center).all():
            raise NativeGeometryFailure('Druga para reprezentatywna: nieprawidłowe współrzędne')
        left=_relocate(self.a[i],np.eye(3),-center)
        right=_relocate(self.b[j],np.eye(3),-center)
        count_a = self.counts_a[self.groups_a[i]]
        count_b = self.counts_b[self.groups_b[j]]
        # One completed partition can certify the placement of many copies.
        # Spend the longer budget once per large family, after the standard
        # proof failed, so a small fixed deadline cannot discard all copies.
        timeout_s = 120. if min(count_a, count_b) >= 16 else 30.
        problems = []
        alerts = []
        for baked in (False, True):
            operation = 'world_fixed_partition_baked' if baked else 'world_fixed_partition'
            stage = ('repeated_alternative_baked_partition' if baked
                     else 'repeated_alternative_material_partition')
            trace.mark(stage, 'BUDGET', a_id=i, b_id=j,
                       copies_a=count_a, copies_b=count_b, timeout_s=timeout_s)
            if progress:
                progress(f'Powtórzenia: podział B-Rep pary A[{i}] / B[{j}], '
                         f'próba {2 if baked else 1}, limit {timeout_s:g} s.')
            stages = []
            try:
                matched = trace.brep_call(stage,i,j,guarded_world_reexport,left,right,
                    self.tolerance,timeout_s=timeout_s,operation=operation,proof_stages_out=stages)
            except NativeGeometryFailure as exc:
                outcome = str(exc)
                retry = bool(stages and stages[-1]=='fixed_partition_intersections'
                             and ('timeout' in outcome.casefold() or 'limit' in outcome.casefold()))
            else:
                if matched:
                    return True
                outcome = stages[-1] if stages else 'brak dowodu B-Rep'
                retry = outcome == 'fixed_partition_unverified_intersections'
            alerts.extend(phase for phase in stages
                          if phase.startswith(('fixed_partition_warning ', 'fixed_partition_error ')))
            problems.append(outcome)
            if not retry:
                break
        details = '; '.join([*dict.fromkeys(alerts), *problems])
        raise NativeGeometryFailure(f'Druga para reprezentatywna: {details}')

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
        if family in self.attempts:return None
        self.attempts.add(family)
        origin=(np.asarray(self.a[i].center)+np.asarray(self.b[j].center))*.5
        if not np.isfinite(origin).all():return None
        left=_relocate(self.a[i],np.eye(3),-origin)
        right=_relocate(self.b[j],np.eye(3),-origin)
        if progress:
            progress(f'Powtórzenia: pełna weryfikacja pary A[{i}] / B[{j}] '
                     f'we wspólnym lokalnym układzie, limit {60 if rigid_witness else 75} s.')
        try:
            if rigid_witness:
                deadline = monotonic() + 60.
                try:
                    fixed, _, _ = trace.brep_call(
                        'repeated_fixed_cells', i, j, guarded_rigid,
                        left, right, self.tolerance, timeout_s=45., repeated_cells=True)
                except NativeGeometryFailure as exc:
                    trace.mark('repeated_fixed_cells','UNVERIFIED',a_id=i,b_id=j,error=str(exc))
                    fixed = False
                if fixed:
                    if self.geometry_context is not None:
                        self.geometry_context.remember_equivalence(self.a[i],self.b[j],self.tolerance)
                    return True
                remaining = min(40., deadline - monotonic())
                if remaining <= 0:
                    return None
                match, rotation, translation = trace.brep_call(
                    'repeated_rigid_placement_witness', i, j, guarded_rigid,
                    left, right, self.tolerance, timeout_s=remaining,
                    registered_reexport=not candidate(left,right,self.tolerance))
                if match:
                    if self.geometry_context is not None:
                        self.geometry_context.remember_equivalence(self.a[i],self.b[j],self.tolerance)
                    from .world_bounds import WorldBoundsCache
                    box = WorldBoundsCache().broad_bounds(right)
                    radius = np.linalg.norm(np.maximum(np.abs(box[:3]), np.abs(box[3:])))
                    displacement = (np.linalg.norm(translation) +
                                    radius * np.linalg.norm(rotation - np.eye(3), ord=2))
                    stationary = bool(displacement <= min(1e-6, self.tolerance * .001))
                    trace.mark('repeated_rigid_placement_witness', 'PLACEMENT', a_id=i, b_id=j,
                               displacement_bound_mm=float(displacement), stationary=stationary)
                    return stationary
                return None
            return bool(trace.brep_call('repeated_world_local_recovery',i,j,
                guarded_registered_world,left,right,self.tolerance,timeout_s=75.0))
        except NativeGeometryFailure as exc:
            trace.mark('repeated_world_local_recovery','UNVERIFIED',a_id=i,b_id=j,error=str(exc))
            return None
