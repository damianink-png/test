# Integration review — 2026-10-27

Base main: 63258824c08f64648f11df52084b8b8f589c94bb. The personal-context search did not recover the latest second-chat messages; commits and actual Actions logs were used instead.

## Latest verified results
Main run 40451600331: build PASS; V2 revision PASS; Trident revision PASS; Trident revision_shift PASS; V2 shift FAIL (1702 SAME,12 ADDED,1 MOVED,12 REMOVED); Trident shift FAIL (1588 SAME,7 ADDED,7 REMOVED); V2 revision_shift native exit 3221225477 (0xC0000005).
Previous efficient branch run 40410645715: build PASS, V2 revision PASS, other five FAIL. Do not advertise the earlier optimizations as resolving alignment.

## Compared projects and choices
- Open3D, MIT: https://github.com/isl-org/Open3D/blob/main/LICENSE ; https://www.open3d.org/docs/latest/tutorial/pipelines/global_registration.html . Candidate pruning and robust registration are useful architectural patterns. Keep translation-only consensus, index candidates and validate with native B-Rep. Do not use ICP mesh distance or RANSAC fitness as proof of identical CAD geometry; no new heavy Open3D runtime dependency.
- Online3DViewer, MIT: https://github.com/kovacsv/Online3DViewer . Browser model exploration and object isolation are useful patterns. Extend existing offline viewer with A/B pair isolation and reliable reset of hidden occurrences. Keep bidirectional tree selection and names.
- three.js, MIT: https://github.com/mrdoob/three.js/blob/dev/LICENSE ; https://threejs.org/docs/pages/InstancedMesh.html . Shared mesh/occurrence representation retained from previous branch. It reduces serialized duplicate geometry; full GPU instancing/draw-call batching is NOT implemented here.
- CloudCompare: https://github.com/CloudCompare/CloudCompare . Useful registration reference, but no source is copied or binary bundled. It is not treated as an MIT dependency.

All additions here are original DS Compare code informed by general algorithmic patterns, not copied implementations. Existing dependencies and license notices are unchanged. No claim is made that these projects provide interchangeable STEP revision classification engines.

## Combined implementation
- Preserve current main face AABB candidate and bounded micro-seam patches unchanged.
- Retain exact HTML mesh-definition reuse and indexed translation voting from efficient branch.
- Replace greedy pairing inside small candidate families with deterministic maximum-cardinality 1:1 matching, tested against all 512 3x3 bipartite graphs. A proposal remains only a proposal: strict B-Rep gates and tolerances unchanged.
- Preserve strict incomplete-analysis errors for Common/Cut; no successful report is inferred from failed proof. This deliberately differs from main optional-Common suppression and follows the user's stated completeness requirement.
- Add pair A/B isolation; reset hidden items on global modes; include changed-removed material and old moved occurrence in the removed/old view.
- Keep one compiled EXE across six real scenarios, RAM sampling, logs, exact patched sources, existing expected counts.

## Validation
Local: 25 PASS, 1 Windows-only skipped, 1 GUI test deselected (PySide6 absent); Node behavior test PASS for restore-all, removed material and pair selection. Original world-coordinate and occurrence assertions retained through a schema decoder. Full Windows regression/build and six compiled-EXE cases are required before acceptance.

Still unresolved until demonstrated: native crash, false changes in shifted assemblies, exact STEP/BOM/HTML correspondence on all six models, ZW3D 2019 import, GPU rendering speed. These changes are not a declaration of six-case PASS.
