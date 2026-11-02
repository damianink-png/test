# Trident exact-pair — iteration 4 (2026-11-03, Europe/Warsaw)

## Inputs (verified on CI, no substitutions)
- A: `Trident_Assembly1.step`, 192710725 bytes, SHA256 `e26006c887004d1dcacac36e08ca083268336d80668ea2d868a16e2b20aee370`.
- B: `trident_assembly.step`, 185183500 bytes, SHA256 `416eda4e9212b894ed6f78ad3a6af55757115ebfcc4c18db933743d97dd48ccf`.
- Provenance: CI runs [41530141584](https://github.com/damianink-png/test/actions/runs/41530141584), [41530511339](https://github.com/damianink-png/test/actions/runs/41530511339).

## Previous full run: FAIL, no complete comparison
- Run [41538362160](https://github.com/damianink-png/test/actions/runs/41538362160), commit `aa3e91c0030f3eaa1cccb669c844c833647343ef`.
- Imported A 1551 and B 1595 solids; 651 B-Rep matches observed during stage 1. These are NOT final SAME counts.
- Isolated world proof reported three `UnprovenRepair` pairs (240/349, 241/350, 319/273); analysis continued after these failures.
- At ~2931 seconds, stage 2 native rigid comparison caused SIGSEGV, exit code 139.
- Faulthandler stack: `compare.py:322 -> equivalent_rigid -> try_transform -> _is_common_equal -> _common_volume -> BRepAlgoAPI_Common.Build`. Native C++ crash in the **parent**, not the already-isolated world worker.
- Root cause in dispatch: `use_native_guard = len(a)>=600 and len(certified_pairs)>=max(100, 0.4*len(a))`. Normal revision started with `certified_pairs=[]`, so rigid Boolean ran in-process despite >1500 solids.
- Artifacts: [diagnostics](https://github.com/damianink-png/test/actions/runs/41538362160/artifacts/13187932981), [FAILED-BREP](https://github.com/damianink-png/test/actions/runs/41538362160/artifacts/13187932986). Read and verified with [artifact inspection CI](https://github.com/damianink-png/test/actions/runs/41546621101).
- No `PODSUMOWANIE.json`, no final STEP/HTML, and no final SAME/CHANGED/ADDED/REMOVED/MOVED/UNCERTAIN numbers. **Full CAD verdict: FAIL.**

## Fix
- `review/fix06/ci/patch_trident_rigid_isolation.py`: use subprocess `guarded_rigid` for all assemblies with >=600 solids, even with zero certified pairs.
- Keep the original candidate lookup and `world_candidate` activation condition in `registered_native_mode` so normal revision matching is not broadened. No tolerance change.
- Preserve original rigid proof `equivalent_rigid` inside the child for ordinary revision comparisons; use registered proof only in the originally qualified registered mode.
- Extend whole-stage timeout budget from fixed 240s to bounded size-aware budget; exhaustion remains fatal/incomplete.
- A native crash/timeout becomes `NativeGeometryFailure`, which the existing isolated-pair policy marks `UNCERTAIN`; never SAME or a fabricated deletion.
- Added/updated regression tests for 600+ parts, native worker failures, global budget, and small assembly behavior.
- Exact-pair full rerun is required after regression PASS; **do not mark complete from unit tests**.

## Status
Awaiting verified regression run and next full exact-pair run. Full PASS is not claimed.
