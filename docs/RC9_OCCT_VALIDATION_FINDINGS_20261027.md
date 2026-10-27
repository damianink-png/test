# RC9 OCCT validation findings — 2026-10-27

Status: **diagnosis only; no change to classification logic and no new CI requested**.

Evidence: existing real-assembly run https://github.com/damianink-png/test/actions/runs/40463488094 and its V2/Trident shift artifacts.

## V2 shift
- Alignment proposal: translation B->A [-1275.0000000003693, 394.9999999999919, -209.99999999999065] mm.
- 1702 SAME, 12 ADDED, 12 REMOVED, 1 MOVED; 1702 certified frame matches (99.24%).
- 6 of 12 optional Common checks timed out at 35 seconds.
- Archived world_negative_01 A and B B-Rep have nearly identical exact world bounds (<1e-9 mm difference) and close volumes (~19945.99939 vs 19945.99519 mm3).
- **Both are invalid** per BRepCheck_Analyzer: a face reports UnorientableShape and a wire reports SelfIntersectingWire.

## Trident shift
- 1588 SAME, 7 ADDED, 7 REMOVED; 1588 certified frame matches (99.56%).
- 6 of 7 optional Common checks timed out.
- Archived world_negative_01: A invalid (UnorientableShape face / SelfIntersectingWire), B valid.
- Exact bounds differ by <1e-9 mm; volumes ~43101.34946 vs ~43104.55982 mm3.
- ShapeFix_Shape alone did **not** validate the invalid sample; targeted ShapeFix_Wire.FixSelfIntersection on a deep copy yielded valid topology in a diagnostic attempt. This does **not** prove that the repair preserves geometry or authorise SAME.

## Implications
- The existing strict world comparison rejects invalid topology before surface/trim proof, leaving false revision classifications after otherwise successful global registration.
- Do not lower the 0.01 mm tolerance, infer SAME from near-equal bounds/volume, or suppress failed Boolean checks.
- Proposed safe integration: isolated BRep validation, selective copy-only wire repair, **independent proof that the repair preserved original 3D surfaces and oriented trims**, then original strict SAME verification. A repair without that proof remains inconclusive.
- Reuse cached Common in Common/Cut only when inputs were not modified; invalidate it after repair.
- The latest integrated run https://github.com/damianink-png/test/actions/runs/40469591174 failed its small regressions (27 passed, 1 failed: test_incompatible_equal_support_rejected), so it never reached the six large CAD scenarios.
- Keep CI idle until the complete OCCT integration is ready. Existing runs were not cancelled.
