# RC8.1: remove restart overhead

RC8 code review found two concrete regressions in fresh comparison: copying every occurrence into an independent topology destroyed shared native definitions; fresh comparison called isolated world verification without the existing scoped worker session, launching a process per pair.

Fix: preserve native definition identity (IsPartner registry plus orientation) and placement-aware reuse in aligned STEP. Coincident duplicate instances retain distinct topology labels so counts and IDs survive roundtrip. Fresh comparison now uses existing recyclable native sessions for large models. Every request still loads its own B-Rep and proves equivalence; no stale certificates, geometry tolerance changes, increased Boolean timeout or failed-proof acceptance.

Local Linux OCP7.8 validation: 209 regression tests PASS (40.89s); 20 roundtrip/alignment tests PASS. Tests cover post-import definition sharing, all 600 occurrences in benchmark, coincident duplicates, metadata bijection and worker-session cleanup on exception.

Controlled benchmark (not compiled Windows, not actual Voron):
| Workload | RC8 | RC8.1 |
|---|---:|---:|
| STEP write+reimport, 600 copies of one box | 3.833s | 0.196s |
| STEP bytes | 10445724 | 374890 |
| Native definitions after reimport | 600 | 1 |
| 12 isolated full world proofs | 11.649s | 1.000s |

These measurements demonstrate overhead removal, not a promised end-to-end Voron speedup. Windows build and six compiled CAD scenarios must establish that separately. Pre-restart registration still verifies many pairs; this conservative gate has not been weakened in this patch. Source restart is retained as requested.
