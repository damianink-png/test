"""Exact bounds shared by candidate selection and material comparison.

Reuse requires the same native geometry and exactly the same linear transform.
Translations shift an existing AABB; rotations, scale and replaced geometry
require a new OCCT calculation. No descriptor/name can establish a cache hit.
"""
from collections import defaultdict
from time import perf_counter
import numpy as np


class WorldBoundsCache:
    def __init__(self):
        self._entries = defaultdict(list)
        self._handles = []
        self.calculations = self.hits = 0
        self.seconds = 0.0
        self.broad_calculations = self.broad_hits = 0
        self.broad_seconds = 0.0

    @classmethod
    def shared(cls, context):
        if context is None:
            return cls()
        cache = getattr(context, '_dscompare_world_bounds', None)
        if cache is None:
            cache = cls()
            context._dscompare_world_bounds = cache
        return cache

    def bounds(self, part):
        return self._bounds(part, precise=True)

    def broad_bounds(self, part):
        """Conservative non-meshed bounds, for disjoint rejection ONLY."""
        return self._bounds(part, precise=False)

    def _bounds(self, part, *, precise):
        from .geometry import _precise_world_bounds
        shape = part.shape
        handle = shape.TShape()
        transform = shape.Location().Transformation()
        linear = tuple(transform.Value(i, j) for i in (1, 2, 3) for j in (1, 2, 3))
        offset = np.array([transform.Value(i, 4) for i in (1, 2, 3)])
        key = (hash(handle), linear, int(shape.Orientation()), precise)
        for saved, saved_offset, bounds in self._entries[key]:
            if shape.IsPartner(saved):
                if precise:
                    self.hits += 1
                else:
                    self.broad_hits += 1
                delta = offset - saved_offset
                return bounds + np.concatenate((delta, delta))
        start = perf_counter()
        if precise:
            bounds = np.asarray(_precise_world_bounds(shape), dtype=float)
            self.seconds += perf_counter() - start
            self.calculations += 1
        else:
            from OCP.BRepBndLib import BRepBndLib
            from OCP.Bnd import Bnd_Box
            box = Bnd_Box()
            BRepBndLib.Add_s(shape, box, False)
            bounds = np.asarray(box.Get(), dtype=float)
            self.broad_seconds += perf_counter() - start
            self.broad_calculations += 1
        if bounds.shape != (6,) or not np.isfinite(bounds).all():
            raise ValueError('Nieprawidłowa obwiednia bryły')
        # Snapshot placement and keep the TShape wrapper alive (OCP hash identity).
        self._handles.append(handle)
        self._entries[key].append((shape.Located(shape.Location()), offset, bounds.copy()))
        return bounds.copy()

    def statistics(self):
        return dict(calculations=self.calculations, hits=self.hits,
                    calculation_seconds=round(self.seconds, 6),
                    broad_calculations=self.broad_calculations, broad_hits=self.broad_hits,
                    broad_seconds=round(self.broad_seconds, 6))
