# DS Compare — exact Trident, iteration 5 (2026-11-03)

## Exact input provenance
- A: \`Trident_Assembly1.step\`, 192710725 bytes, SHA256 \`e26006c887004d1dcacac36e08ca083268336d80668ea2d868a16e2b20aee370\`.
- B: \`trident_assembly.step\`, 185183500 bytes, SHA256 \`416eda4e9212b894ed6f78ad3a6af55757115ebfcc4c18db933743d97dd48ccf\`.
- Source retrieval is pinned and SHA verified; no older Trident fixture substituted.

## Prior run: confirmed full geometry FAIL
- [Run 41547342189](https://github.com/damianink-png/test/actions/runs/41547342189), commit \`cea1cf4d7ecfc5e23eb7be4d13e92aae0e44a615\`, completed 2026-11-03 00:08 UTC, conclusion **failure**.
- A imported 1551 solids; B imported 1595 solids; import from cache ~2.1 s and ~2.2 s.
- Stage-1/initial classification reached 1968 positions; material revision phase had 381 unmatched old and 711 unmatched new occurrences. These are **not** final REMOVED/ADDED counts.
- Native isolation prevented the prior SIGSEGV. Geometry instead stopped after 1583.082 s at A[31] \`B_Drive_Frame_Lower:1\` vs B[44] \`b_stepper_lower:1\` (third Common test), with \`UnprovenRepair\`, exit 70 from the child. Alternative isolated Common/Cut also failed.
- Inspection of the captured \`common/A.brep\` shows \`BRepCheck_Analyzer.IsValid()==False\`; \`common/B.brep\` is valid. \`validated_copy(A, 0.01)\` fails \`UnprovenRepair\`, while B validates. This establishes that the **captured isolated A B-Rep** cannot currently be repaired within the unchanged 0.01 mm tolerance; it does not by itself prove the original STEP source is defective.
- The strict noninteractive material comparison aborted on the first unresolved native pair because \`recover_failures=review_approval is not None\`. Consequently no final \`PODSUMOWANIE.json\`, STEP or HTML, and no defensible SAME/CHANGED/ADDED/REMOVED/MOVED/UNCERTAIN counts.
- [Diagnostics artifact](https://github.com/damianink-png/test/actions/runs/41547342189/artifacts/13191706018), [captured BRep artifact](https://github.com/damianink-png/test/actions/runs/41547342189/artifacts/13192175393).

## Change in this iteration: explicit diagnostic-only continuation
- New \`review/fix06/ci/patch_trident_diagnostic_continuation.py\` patches the restored engine to accept \`diagnostic_only=False\` (strict behavior remains the default).
- Only the exact-pair CI runner opts into diagnostic continuation. It uses existing isolated pair-failure handling and retry, records unresolved occurrences as UNCERTAIN, preserves independently verified CHANGED/SAME, and checks complete occurrence coverage.
- **No simulated user approval:** diagnostic continuation returns partial data without invoking the interactive approval callback. \`revision_overlap.diagnostic_only=True\` and \`analysis_complete=False\` mark incomplete results.
- \`trident_exact_run.py\` now emits status \`INCOMPLETE\` and exits code 3 if any UNCERTAIN or incomplete material analysis remains. The strict final audit and workflow **must stay FAIL** for partial diagnostics; they cannot be interpreted as a successful geometry comparison.
- No geometry matching thresholds, pair selection, tolerance, or source inputs were changed.
- Four new synthetic regressions in \`test_trident_diagnostic_ci.py\` passed locally, including no fake deletions, all occurrence coverage, strict mode unchanged, and successful proof not downgraded.

## Re-test
- [New exact-pair workflow run 41553622949](https://github.com/damianink-png/test/actions/runs/41553622949), head commit \`ff919e4be5751f5f690cf5b79f3c2eefbfb38d67\`.
- The CI preparation, regression, SHA verification and import-cache steps have completed successfully; full geometry is running at the time of this note.
- This is **not** full PASS. Inspect its final strict audit and artifacts before reporting any status counts. Do not launch a duplicate while it is active.
