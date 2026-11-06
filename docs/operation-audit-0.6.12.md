# DS Compare 0.6.12 — active pipeline operation review

Base: 0.6.11 e9d9c12ed25797587cfec0218c627dd10acb089a.
Scope is the active desktop/worker pipeline, not a certification of every
legacy prototype or OCCT implementation. No original user STEP pair is
available; synthetic results do not establish their exact performance or
solve the unknown native failure on those files.

| Stage inspected | Result |
| --- | --- |
| Input fingerprints / serial and parallel import | Existing full-file digest is passed into both cache paths. Import sharing/cache and validation retained; no duplicate hashing change needed. |
| Translation / rotation / retries | Stop constructing new body hypotheses once their verification budget is exhausted. Preserve pending retries, exact-transform proofs and the independent surface budget. Reuse center arrays once per coordinator invocation. |
| Surface correspondence proposal | Descriptor cache now includes feature_kind, not just equal area/volume. Different surface kinds no longer share an incompatible candidate list. No candidate is promoted to a geometric proof. |
| Revision classification / full occurrence counts / Common | Keep the 0.6.9 operand-focused FULL-revision counts and completed positive/negative reuse. Unknown results stay unknown. Existing validated Common/Cut partitions are shared with output; checks are not deleted. |
| BOM | Completed rigid proofs are consulted before expensive serialization, including fast mode. Actual identity/congruence is required; numbers/names do not establish equality. Existing complete and partial A-to-B group transfer retained. |
| STEP / HTML / CSV output | Retain selected structural/full STEP validation and source-bound material evidence. Existing single HTML generation and optional output flags already avoid duplicate output. |
| Preview | Reuse computed properties of the identical Common shape for the second revision's metadata. Keep separate A/B names/roles/paths. Existing shared mesh cache and streamed scene writing retained. |
| Desktop orchestration / progress | Replace whole-log reread on every poll with backward reading sufficient for 100 valid JSON events. Preserve malformed/partial-line handling and Unicode. Worker isolation, decision tokens, cancellation and result publication remain. |

Python regressions verify no serialization after a completed BOM proof,
Common geometry property reuse with both names preserved, no unused hypothesis
generation after budget expiry, and type-correct surface correspondences.
Rust tests compare the tail reader to the prior full-reader result across
10,000 Unicode/CRLF events, malformed lines, incomplete final JSON and empty
files, and assert the large case reads under one tenth of the input bytes.
The tail may read the full file if it has fewer than 100 valid events; that
is required to preserve the existing history semantics.

Full selected CAD tests, packaged diagnostics, real independent STEP smoke,
frontend/browser/Rust tests and cold/warm OneEXE startup run in Windows CI.
Final exact outcomes and artifact identity are recorded in the PR. Native
verification at a new transform and a user-requested retry of an interrupted
operation remain necessary operations, not redundant repeats.
