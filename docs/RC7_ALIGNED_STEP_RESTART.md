# DS Compare RC7 — aligned STEP restart (experimental)

After a global B→A transform has been **independently verified and approved** by the existing alignment logic, RC7 writes the transformed B assembly to `_WYROWNANY_STEP/B_WYROWNANY.step`, reimports it as a new STEP source, clears stale pair certificates and geometry-registry cache, and runs the ordinary full comparison again in A's frame. The original A/B source files are never overwritten.

This path is enabled by default only after `alignment.applied=True`. For a controlled comparison, set `DSCOMPARE_REIMPORT_ALIGNED_STEP=0` to use the original in-memory relocation path. This is an environment variable, not a new UI setting.

The STEP writer uses XCAF assembly occurrences to preserve multiplicity and part names. It rejects missing occurrences or significant changes to name, center, volume or area; metadata is restored only after a one-to-one validation. **These checks are not a geometry identity proof.** Every SAME result still requires the normal comparison's B-Rep verification. The writer does not change user tolerances or accept unresolved parts as SAME. No alignment means no extra STEP export or reimport.

Files:
- `scripts/rc7_aligned_step_restart.py`: new runtime module copied into the unpacked RC7 source tree.
- `scripts/rc7_aligned_step_restart_patch.py`: guarded patch to `dsac29/cli.py`.
- `tests/test_rc7_aligned_step_restart.py`: 3 round-trip and negative tests.
- `.github/workflows/rc7-aligned-step-restart.yml`: Windows build, existing regressions, UI smoke and 6 real V2/Trident CAD cases.

The Windows CI uses the original Work RC7 test harness; its large CAD scenarios include `--no-bom`, so their success alone would **not** validate BOM output. A synthetic local 12-solid assembly translated (+1275, -395, +210) mm was successfully realigned, written, reimported and compared with 12 SAME; the three unit tests passed. This is not yet evidence of correctness on large real assemblies.

Base: `audit/dscompare-rc7-revision-overlap-diagnosis-20261026` with existing conservative parametric proof and alignment-only Common guard applied by the workflow. Do not merge before six real scenarios and export checks pass.
