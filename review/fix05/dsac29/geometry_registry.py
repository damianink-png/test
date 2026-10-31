"""In-memory exact STEP definition registry shared by matching and reporting.

Only a native TopoDS TShape identity, identical serialized local B-Rep or a
successful rigorous equivalence test can establish equality. Numeric
properties merely select possible candidates and never prove a match.
Nothing persists between processes or analyses.
"""
from __future__ import annotations

import hashlib
import tempfile
from collections import defaultdict


class GeometryRegistry:
    def __init__(self):
        self._by_hash = defaultdict(list)
        self._definitions = []
        self._native_handles = []
        self._part_ids = {}
        self._digests = {}
        self._digest_directory = None
        self._rigid_checks = {}
        self.stats = defaultdict(int)
        self.bom_errors = []
        self.slow_checks = []

    def definition(self, part):
        """Stable id for the underlying native STEP shape *definition*.

        Shape position and name do not affect TShape identity. Keep the actual
        part and validate IsPartner to protect against native hash collisions.
        """
        identifier = id(part)
        if identifier in self._part_ids:
            return self._part_ids[identifier]
        handle = part.shape.TShape()
        for index in self._by_hash[hash(handle)]:
            if part.shape.IsPartner(self._definitions[index].shape):
                self._part_ids[identifier] = index
                self.stats['native_definition_hits'] += 1
                return index
        index = len(self._definitions)
        self._definitions.append(part)
        self._native_handles.append(handle)  # prevent OCP wrapper identity recycling
        self._by_hash[hash(handle)].append(index)
        self._part_ids[identifier] = index
        return index

    def exact_digest(self, part):
        """SHA-256 of full *local* B-Rep serialization, once per definition."""
        key = self.definition(part)
        if key not in self._digests:
            from OCP.TopLoc import TopLoc_Location
            try:
                if self._digest_directory is None:
                    self._digest_directory=tempfile.TemporaryDirectory(prefix='dscompare_definition_digest_')
                from pathlib import Path
                from .brep_transport import write_brep
                path=Path(self._digest_directory.name)/f'{key}.brep'
                try:
                    write_brep(part.shape.Located(TopLoc_Location()),path)
                    self._digests[key]=hashlib.sha256(path.read_bytes()).digest()
                finally:
                    path.unlink(missing_ok=True)
                self.stats['serializations'] += 1
            except Exception:
                self._digests[key] = None
                self.stats['serialization_errors'] += 1
        else:
            self.stats['digest_cache_hits'] += 1
        return self._digests[key]

    def same_definition(self, left, right):
        if self.definition(left) == self.definition(right):
            return True
        ld = self.exact_digest(left)
        return ld is not None and ld == self.exact_digest(right)

    def remember_equivalence(self,left,right,tolerance,same=True):
        l,r=self.definition(left),self.definition(right)
        self._rigid_checks[(min(l,r),max(l,r),float(tolerance))]=bool(same)
        self.stats['proofs_shared']+=1

    def rigid_equivalent(self, left, right, tolerance=0.01):
        """Proof of rigid congruence, memoized only within this invocation.

        Cache keys include the supplied tolerance. We never treat matching
        volume, dimensions, surface area, names, or a numeric signature alone
        as geometric identity.
        """
        from .geometry import candidate, equivalent_rigid
        l, r = self.definition(left), self.definition(right)
        if l==r:
            self.stats['rigid_shortcuts'] += 1
            return True
        key = (min(l, r), max(l, r), float(tolerance))
        if key in self._rigid_checks:
            self.stats['rigid_cache_hits'] += 1
            return self._rigid_checks[key]
        if self.same_definition(left,right):
            self.remember_equivalence(left,right,tolerance)
            self.stats['rigid_shortcuts']+=1
            return True
        if not candidate(left, right, tolerance):
            self._rigid_checks[key] = False
            self.stats['numeric_rejections'] += 1
            return False
        self.stats['rigid_brep_checks'] += 1
        # Do not cache exceptions: error must not be converted to a negative
        # geometry decision, and the caller can report it explicitly.
        from time import perf_counter
        started=perf_counter();failed=None
        try:
            same=bool(equivalent_rigid(left,right,tolerance)[0])
            self._rigid_checks[key]=same
            return same
        except Exception as exc:
            failed=str(exc);raise
        finally:
            elapsed=perf_counter()-started
            entry={'left':left.name,'right':right.name,'left_path':left.path,
                   'right_path':right.path,'seconds':round(elapsed,6),'error':failed}
            self.slow_checks.append(entry)
            self.slow_checks.sort(key=lambda item:item['seconds'],reverse=True)
            del self.slow_checks[50:]
