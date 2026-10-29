# RC9 analysis: 2026-10-29

Baseline: 465350193a07db97f1ff2108ed52c2e649f269ef, run 40899644069.
Build and packaged ZIP validation passed. All five CAD scenarios failed.

## Evidence
All four shift scenarios stopped in guarded_world_reexport with UnprovenRepair.
Trident shift: original pair A273/B273, artifact 12909884338.
A SHA256 cbf1716af80bddcaa92031809b213d4e493308d6689a3813c0fddb6c0d6e1f13
B SHA256 49aa727ace4cf67ed6b2b02ddc9e5769bb8e961463cb011dfec4f923d4b636ba

Trident revision: artifact 12911775490. Common returned -122.581594 mm3
and invalid topology. Both inputs passed BRepCheck and local BRepAlgoAPI_Check.
OBB off, parallel, swapped arguments and GlueFull did not produce valid output
in the Windows diagnostic. Local fuzzy values 0, 1e-6, 1e-5, 1e-4, 1e-3,
CheckInverted false, and Cut also failed. This issue is NOT fixed.

## Implemented correction
Original-to-original boundary proof was using the stricter repair budget
(tolerance/8 per curve), although no repaired copies were involved.
A separate original-boundary-only mode now uses the existing half-budget
proof, retaining every edge. No micro-edge removal, Boolean, ShapeFix,
bounding-box-only or volume-only identity is accepted in this mode.
Copy-repair proof and failure propagation are unchanged.

## Validation and limits
Local OCP 7.8.1.1; Windows CI uses 7.9.3.1.1.
Captured Trident shift pair: original proof false before, native worker true
after, with repair forbidden by the regression test. The captured Trident
revision_shift pair also passed the corrected native worker replay.
A further 0.02 mm displacement is rejected. Seven regression controls
cover within-budget/out-of-budget displacement, dimension change, hole
changes, mode separation and failed repair propagation. Existing repair
budget, source tolerance and fail-fast checks passed locally.
V2 captured shapes validate locally but failed validation on Windows;
therefore local V2 success is NOT proof that the Windows failures are fixed.
The full Windows matrix must run again. No complete assembly PASS is claimed.

Replay: python ci/test_rc9_original_boundary.py <artifact>/evidence/comparison/FAILED_BREP/world
The optional replay expects the Trident invalid pair. Synthetic controls
run on every build without requiring expiring artifacts.

OCCT reference consulted:
https://www.occt3d.com/dev/doc/overview/html/specification__boolean_operations.html
BRepCheck validity alone is not sufficient for Boolean suitability.
No third-party source code copied.
