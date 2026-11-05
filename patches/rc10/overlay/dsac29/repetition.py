"""Conservative exclusion of repeated geometry from material pairing.

Count the complete revision, including already matched occurrences. Native
definitions and compatible physical descriptors veto Common; descriptors
never establish equality or authorize a pair. Names and placements do not
identify a unique component.
"""
from .compare import _VolumeIndex
from .geometry import candidate
from .geometry_registry import GeometryRegistry


def repeated_ids(parts, tolerance=0.01, context=None):
    registry = context if context is not None else GeometryRegistry()
    definitions = {}
    repeated = set()
    index = _VolumeIndex(parts, range(len(parts)))
    for i, part in enumerate(parts):
        group = registry.definition(part)
        if group in definitions:
            repeated.update((i, definitions[group]))
        else:
            definitions[group] = i
        if i in repeated:
            continue
        for j in index.query(part.volume, tolerance):
            if j > i and candidate(part, parts[j], tolerance):
                repeated.update((i, j))
    return repeated
