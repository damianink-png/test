# DS Compare RC9 — OCCT integration evidence (2026-10-27)

Branch: `fix/integrated-proof-matching`. Base: pinned RC9 Stability source artifact 12650346634. This is a code integration, **not** a declaration of six large-case PASS.

## Techniques and source comparisons

- **OCCT**: use native `BOPAlgo_PaveFiller` once per shape pair for `Common` and both directional `Cut` operations. Enable `SetNonDestructive(True)`, `SetUseOBB(True)`, and preserve the existing `max(tolerance/100, 1e-6)` fuzzy setting. The OCCT boolean guide explicitly supports reusing a prepared PaveFiller and non-destructive operation: https://github.com/Open-Cascade-SAS/OCCT/wiki/boolean_operations . This does not mean all Boolean results are valid: check `IsDone`, topology, and volume conservation.
- **FreeCAD**: Part Boolean features use OCCT B-Rep operations (see https://freecad.github.io/SourceDoc/da/d3a/classPart_1_1Boolean.html ). DS Compare does not copy FreeCAD's UI or treat a CAD application's display as evidence of shape equality. The shared native kernel is the transferable technique.
- **CadQuery**: CadQuery uses OCP/OCCT for programmable CAD operations (https://github.com/CadQuery/cadquery and https://github.com/CadQuery/OCP ). It is not a ready-made revision-classification engine. DS Compare uses the same OCCT primitives but retains its own 1:1 occurrence matching, status rules, and artifact contract.
- **Registration alternatives**: mesh/point-cloud registration (e.g. Open3D ICP/RANSAC) may propose transforms but cannot prove equal trimmed CAD surfaces. DS Compare keeps descriptor hypotheses separate from native oriented face/trim proof and uses maximum-cardinality 1:1 support for repeated occurrences.

## Repair policy

1. Validate original B-Rep; never modify imported source objects.
2. Only if invalid: deep-copy, attempt bounded `ShapeFix_Shape`, then selective `ShapeFix_Wire.FixSelfIntersection` on copied invalid faces.
3. Accept a repaired copy **only** if it is valid and the original/repaired exact world bounds, volume and every oriented surface/wire pass an independent strict boundary proof. An inconclusive repair is rejected.
4. For invalid STEP inputs, a SAME verdict still requires original-to-original oriented surface and trim matching. Repair alone, volume, bounding box or mesh can never establish SAME.
5. Repaired inputs invalidate any previously computed Common; the original STEP, HTML and BOM geometries are unchanged. Unproven Boolean failures remain unresolved rather than silently producing SAME/CHANGED.

Tolerance stays 0.01 mm; the repair proof uses a tighter fraction. The MOVED equal-occurrence rule in `revision_rules.py` is unchanged. One region calculation feeds STEP/HTML/CSV.

## Reproducible local measurements — **not** large-assembly benchmarks

Linux Python 3.13, installed OCP binding, 15 warm operations per process, same overlapping 20×10×10 and 25×10×10 mm boxes, three separate processes per implementation. Median per-call times (seconds):

| Run | Pinned RC9 independent Booleans | Integrated shared PaveFiller |
|---|---:|---:|
| 1 | 0.010340 | 0.008856 |
| 2 | 0.009556 | 0.008128 |
| 3 | 0.009037 | 0.007881 |

Peak process RSS (KiB) in those runs: baseline 328596 / 328592 / 328596; integrated 328860 / 328736 / 328732. This includes the entire Python/OCP process and is too coarse to attribute differences to the algorithm. Small boxes cannot establish speed or RAM improvement for V2/Trident. The six compiled Windows EXE scenarios will provide comparable measurements and actual exported artifacts.

## Local correctness evidence

- Integrated source regressions: 28 passed, 1 Windows-only skipped (small suite: strict repair, Boolean Common/Cut, alignment candidate consensus, HTML shared meshes).
- Initial test revealed `BRepAlgoAPI_Common` in this OCP binding does not expose `HasErrors`; replaced with `IsDone` and validated result topology. The separate `BOPAlgo_PaveFiller` **does** expose `HasErrors`.
- A second regression revealed `report.py` imports `material_deltas.all_changes`; restored the shared export function.
- A longer optional regression set was not completed locally. No Windows EXE/large-assembly PASS has been observed for this integrated commit.

## Pending acceptance gate

Run the manual six-case Windows workflow only once integration is complete. Verify the six real V2/Trident outcomes and the generated STEP, 3D HTML, report, and revision BOM occurrence mappings. A failed test, missing artifact, native crash, timeout, unproven SAME, or false MOVED is a blocker. Report PASS only from actual artifacts and run logs.

## Real failed B-Rep fixtures inspected locally (archived run 40463488094)

These are archived **old failed-run** B-Rep files, not six new EXE test outcomes.

- V2 `world_negative_01`: both original shapes invalid. `ShapeFix_Shape` alone leaves both invalid. The targeted `ShapeFix_Wire` attempt did not produce a provably valid replacement. `validated_copy` correctly rejects both (local diagnostic wall times ~1.43 s and ~0.55 s).
- Trident `world_negative_01`: original A invalid, B valid. A's deep-copy repair passed the strict original-boundary gate and produced a valid repaired copy in ~28.76 s; B needed no repair. **Original A versus B did not pass strict face/wire identity** (False in ~9.89 s). A separate repaired-A versus B strict attempt exceeded 70 s without a result. None of these measurements proves SAME or fixes the shifted assembly.
- This exposes a concrete acceptance blocker: the existing 35 s native-world timeout is too short for some real repair-plus-proof paths. The workflow must not silently classify a timeout as SAME. Further work must either reduce the proof cost or retain an explicit inconclusive outcome; simply increasing the timeout is not evidence of geometric correctness.

Archived evidence: https://github.com/damianink-png/test/actions/runs/40463488094

## Static artifact-accounting hardening (2026-10-27, not yet CI-tested)

The six-case artifact auditor now requires exact occurrence conservation rather
than the weaker check that the total status count is at least the larger assembly.
For the supported status set SAME/MOVED/CHANGED/ADDED/REMOVED, let
`matched = SAME + MOVED + CHANGED`. The audit enforces
`matched + REMOVED == solids_A` and `matched + ADDED == solids_B`.
Unexpected status categories or negative/non-integer counts fail closed.
STEP/HTML/report SHA-256 fingerprints are emitted for reproducibility.
This verifies **accounting**, not geometric truth: STEP colors, triangle
topology, and HTML selection still require independent inspection.

Technique comparison: OCCT, FreeCAD Part and CadQuery/OCP expose B-Rep
operations but none of those Boolean primitives proves DS Compare's
application-specific occurrence/status accounting. A count-conservation
invariant is therefore independent of the CAD kernel and complements
strict oriented B-Rep SAME proof; it is not a replacement for it.
Open3D-style mesh registration also cannot establish the occurrence
ledger or exact trimmed-surface equality. No new runtime or RAM
measurement was made for this static audit change, and no workflow
was triggered. The six real cases remain unverified after the CI fix.
