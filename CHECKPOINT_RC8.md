# DS Compare R22.3 RC8 STEP restart

Based on bb52ee68ceb71355831b8c22cbe17a032c154257 (RC7 roundtrip branch).

Compiled RC7 roundtrip diagnostics (run 40273244654) show successful aligned STEP write/read but metadata matching fails on M3 inserts: volume/center integration changes after STEP roundtrip. RC8 uses unique occurrence IDs only to restore original names/paths, with count, uniqueness and coverage validation. IDs never prove SAME. The fresh comparison still runs without prior geometry certificates or another alignment. Reimport deliberately bypasses the persistent import cache. Separate topology wrappers retain coincident repeated occurrences.

Local OCP 7.8 tests: 8 roundtrip tests and 9 alignment tests pass. Windows OCP 7.9 compiled six-scenario matrix is required; this checkpoint is not a stable release claim. Original-frame behavior is unchanged. Native ZW3D 2019 not available for verification.

Workflow uploads Windows executable, complete patched sources and per-case diagnostics. Remaining risk: native geometry failures may still appear after metadata restoration; no timeout relaxation or acceptance of incomplete proofs.
