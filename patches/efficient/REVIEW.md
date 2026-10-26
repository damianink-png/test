# DS Compare: exact preview reuse and strict completion

Base: caa8e8c4cff5aa8b52074680912e915cad2836fc; pinned RC9 Stability source artifact 12650346634.

Changes:
- Preserve original-coordinate-first deferred alignment and strict native B-Rep gates.
- Deduplicate exactly equal translation hypotheses, spatially index votes, reuse identical scoring for ambiguity checks. Do not merge nearby vectors or relax tolerance. Require support from two signature families.
- Keep strict RC9 timeout/error propagation for material Common/Cut. Remove the later optional-Common behavior that silently preserved ADDED/REMOVED after an incomplete calculation. Unexpected native errors also propagate as incomplete analysis.
- Offline HTML now stores each exact native mesh definition once plus occurrence transforms, names, colors and pair IDs. Identity uses IsSame, orientation and tessellation quality, never shape-size heuristics. Both local and scene coordinates are centered before float32 conversion.
- Keep all occurrence picking/tree logic. This is shared file representation, not GPU instanced rendering: GPU draw-call reduction remains future work.
- Existing geometric definition/import caches are retained, not duplicated. No changes to STEP export, classification tolerance or per-operation timeout.

Validation before CI:
- 21 passed, 1 Windows-only skipped, 1 GUI test deselected (local PySide6 unavailable).
- 600 rendered occurrences: one mesh definition, all 600 IDs and positions retained.
- Rotation and large coordinate offsets, removed opacity, distinct geometry non-merging.
- 3000 anchors, ambiguity rejection, single-family rejection.
- 600-anchor microbenchmark with 192 proposal limit: old 0.1042 s, new 0.00289 s; same vector/support. This is NOT an end-to-end CAD speedup measurement.

CI workflow efficient-strict.yml runs new tests, unchanged strict stability assertions, all TESTUJ regressions, Windows build, then all six real V2/Trident scenarios on the compiled EXE. Existing preview tests decode the new payload to world-space arrays and retain their original assertions. No expected classification counts were changed.

Limitations: no claim of six large-case PASS before the run completes. Strict completion may expose previously hidden Common timeouts; do not interpret a clean partial result as proof. ZW3D 2019 import requires separate application verification.
