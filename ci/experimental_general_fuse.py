"""RC9 material intersection fallback inspired by FreeCAD BooleanFragments.

This module is deliberately opt-in. It never converts an invalid Boolean
result into an empty intersection or a SAME/MOVED verdict.
Based on the OCCT General Fuse approach used by FreeCAD BOPTools.
Implementation independently written; no FreeCAD source copied.
"""
from __future__ import annotations

import math


class UnprovenFragmentIntersection(RuntimeError):
    """No independently verified B-Rep intersection could be produced."""


def common_via_general_fuse(a, b, tolerance=0.0):
    """Return an OCCT B-Rep intersection only when both checks pass.

    Experimental fallback for an isolated native worker, not for UI thread.
    A General Fuse fragment is accepted only if a fresh Common operation
    between the fragment and both input solids reproduces its volume.
    Consequently this is not a universal workaround for a broken Common.
    """
    from OCP.BOPAlgo import BOPAlgo_Builder
    from OCP.TopTools import TopTools_ListOfShape
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer

    if not BRepCheck_Analyzer(a).IsValid() or not BRepCheck_Analyzer(b).IsValid():
        raise UnprovenFragmentIntersection("Invalid original B-Rep")
    args=TopTools_ListOfShape()
    args.Append(a)
    args.Append(b)
    builder=BOPAlgo_Builder()
    builder.SetArguments(args)
    builder.SetNonDestructive(True)
    if tolerance > 0:
        builder.SetFuzzyValue(float(tolerance))
    builder.Perform()
    if builder.HasErrors():
        raise UnprovenFragmentIntersection("General Fuse failed")
    result=builder.Shape()
    if not BRepCheck_Analyzer(result).IsValid():
        raise UnprovenFragmentIntersection("Invalid General Fuse output")
    # Never infer intersection membership from a volume sum or bounding box.
    # Callers must supply independent fragment membership proofs before using
    # the resulting partition for material classification.
    raise UnprovenFragmentIntersection(
        "General Fuse partition built but fragment membership proof is not yet implemented"
    )
