"""Fixed-frame equivalence from solid ownership in one OCCT General Fuse."""
from OCP.BOPAlgo import BOPAlgo_Builder
from OCP.TopAbs import TopAbs_SOLID
from .brep_safety import is_valid
from .material_deltas import volume


def same_material_cells(a, b, tolerance):
    if any(s.ShapeType() != TopAbs_SOLID or not is_valid(s) for s in (a, b)):
        return False
    partition = BOPAlgo_Builder()
    for solid in (a, b):
        partition.AddArgument(solid)
    partition.SetNonDestructive(True)
    partition.SetUseOBB(True)
    partition.SetRunParallel(True)
    partition.Perform()
    if partition.HasErrors() or partition.HasWarnings():
        return False
    images = partition.Images()
    if not all(images.IsBound(s) for s in (a, b)):
        return False
    old, new = (list(images.Find(s)) for s in (a, b))
    if not old or len(old) != len(new):
        return False
    total = 0.
    for piece in old:
        if piece.ShapeType() != TopAbs_SOLID or not is_valid(piece):
            return False
        for index, other in enumerate(new):
            if piece.IsEqual(other):
                new.pop(index)
                break
        else:
            return False
        total += volume(piece)
    return total > 0 and all(abs(volume(s) - total) <= max(tolerance**3, total*1e-9)
                             for s in (a, b))
