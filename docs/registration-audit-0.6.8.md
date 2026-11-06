# DS Compare 0.6.8 — largest unique translation anchors

Base: 0.6.7, f4c7d69e0e71c4baca59405692f5aea3a80508f9.
The user reports that even an identical revision translated in CAD still
fails. The actual STEP pair has not been supplied, so the underlying cause
and outcome on those files remain unconfirmed.

## Requested change

Registration now starts with bilateral singleton candidate cohorts, sorted
by descending original solid volume. Cohorts compare volume, surface area,
and sorted central principal inertia moments. Central moments are independent
of translation; their eigenvalues also survive rigid rotation. No part name
is required. Broad numerical tolerances admit lookup candidates only, and
ambiguous descriptor cohorts are left to the general algorithm.

Each candidate undergoes native whole-solid proof in an isolated process,
after bringing centers into the same frame. If the integrated center fails,
a separate original CAD landmark can propose another translation. No inertia,
volume, area, center or bounding box equality becomes a geometry verdict.
A successful native proof provides a seed vector, not a global frame decision.
The existing independent assembly verification then checks that vector on the
remaining parts. A local move of one unique component does not authorize
global relocation. Proven seed pairs may reuse their exact native verdict
for the same placed shapes; no untested pair is certified.

The unique-anchor route runs before general translation/rotation hypotheses.
The 90% in-place shortcut also considers unique-anchor candidate vectors so
repeated-pitch matches cannot bypass this route. Its lookup check is not a
geometry proof. General and preserved-face searches remain fallbacks.
Completed native negatives are retained for continuation; timeouts remain
unknown and may be retried under the explicit expanded budget. Candidate,
proof and timing counts, anchor indices, volume and vector are reported in
`unique_anchor_evidence` and the progress/native trace. In the final alignment
`search_algorithm=unique_largest_inertia_anchor` identifies the new route.

## Verification

New tests cover largest-first ordering despite reversed input and repeated
fasteners; central inertia translation invariance; inertia mismatch rejection;
real native alignment when general hypotheses are deliberately empty;
rejection of forged matching moments/volume with different real geometry;
rejection of a single locally moved anchor; and retryable native failures.
The frozen worker also independently writes and reimports two STEP assemblies
with twenty repeated fasteners and three unique bodies, then asserts that the
largest anchor drives the result, the vector is correct, and all 23 bodies
are SAME. Existing rotation, ambiguity, copied-solid topology, changed-face,
Common and approval tests remain in CI. CI outcomes are recorded in the PR.

Common occurrence-count/name-family rules and the current portable Tauri /
WebView2 delivery are unchanged. This release implements the requested route;
its synthetic successes are not proof of success on the unavailable models.
