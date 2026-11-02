"""Fail-closed assembly candidate selection policy.

A pair may be classified as REMOVED+ADDED only when the caller has exhausted
other plausible matches. Similar size alone is never positive evidence.
"""
from dataclasses import dataclass
from math import isfinite
from .overlap_evidence import classify_overlap

@dataclass(frozen=True)
class CandidateDecision:
    action: str
    reason: str
    fraction_a: float = 0.0
    fraction_b: float = 0.0
    overlap_class: str = "UNKNOWN"

def decide_pair(*, volume_a, volume_b, common_volume=None, valid_boolean=False,
                other_candidates_exhausted=False, same_geometry_signature=False,
                name_matches=False, shape_evidence=False):
    if same_geometry_signature:
        return CandidateDecision("KEEP_GEOMETRY_MATCH", "Matching verified geometry")
    if common_volume is None:
        return CandidateDecision("RETRY_ISOLATED", "Missing validated common volume")
    e = classify_overlap(volume_a, volume_b, common_volume,
                         valid_boolean=valid_boolean)
    if e.decision == "UNKNOWN":
        return CandidateDecision("RETRY_ISOLATED", e.reason)
    if e.decision == "REJECT_CANDIDATE":
        if other_candidates_exhausted:
            return CandidateDecision("UNMATCHED_A_AND_B",
                                     "Low overlap; no better candidates",
                                     e.fraction_a, e.fraction_b, e.decision)
        return CandidateDecision("SEARCH_ALTERNATIVES",
                                 "Low overlap; search other candidates",
                                 e.fraction_a, e.fraction_b, e.decision)
    if e.decision == "POSSIBLE_REVISION" and (name_matches or shape_evidence):
        return CandidateDecision("VERIFY_CHANGED", "Substantial overlap and independent evidence",
                                 e.fraction_a, e.fraction_b, e.decision)
    return CandidateDecision("REVIEW_CANDIDATE",
                             "Insufficient evidence for a revision",
                             e.fraction_a, e.fraction_b, e.decision)
