"""Conservative overlap evidence for assembly candidate matching.

This module never converts an uncertain pair into a confirmed revision.
It only rejects a candidate when validated common volume is small relative
to BOTH solids. The caller must still search all competing candidates.
"""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class OverlapEvidence:
    fraction_a: float
    fraction_b: float
    decision: str
    reason: str

def classify_overlap(volume_a, volume_b, common_volume, *,
                     valid_boolean, tolerance=1e-6,
                     low_overlap=0.20, review_overlap=0.50):
    """Return REJECT_CANDIDATE, REVIEW_CANDIDATE or POSSIBLE_REVISION.

    A rejected candidate may become REMOVED+ADDED only after matching
    has exhausted alternative candidates; never make that decision here.
    """
    values = (volume_a, volume_b, common_volume, tolerance,
              low_overlap, review_overlap)
    if not all(isinstance(x, (int, float)) and isfinite(x) for x in values):
        return OverlapEvidence(0, 0, "UNKNOWN", "Nonfinite input")
    if not valid_boolean or volume_a <= 0 or volume_b <= 0 or tolerance < 0:
        return OverlapEvidence(0, 0, "UNKNOWN", "Invalid geometry/evidence")
    if not 0 < low_overlap < review_overlap < 1:
        raise ValueError("Invalid overlap thresholds")
    slack = tolerance * max(volume_a, volume_b)
    if common_volume < -slack or common_volume > min(volume_a, volume_b) + slack:
        return OverlapEvidence(0, 0, "UNKNOWN", "Inconsistent common volume")
    common = max(0.0, min(common_volume, volume_a, volume_b))
    pa, pb = common / volume_a, common / volume_b
    if pa < low_overlap and pb < low_overlap:
        decision, reason = "REJECT_CANDIDATE", "Low overlap on both solids"
    elif pa >= review_overlap and pb >= review_overlap:
        decision, reason = "POSSIBLE_REVISION", "Substantial mutual overlap"
    else:
        decision, reason = "REVIEW_CANDIDATE", "Asymmetric/intermediate overlap"
    return OverlapEvidence(pa, pb, decision, reason)
