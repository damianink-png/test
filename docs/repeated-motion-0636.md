# 0.6.36 — repeated occurrence motion policy

Input: DSCompare_1795094351337132500.zip, engine 25b1b82 / 0.6.35.
Global translation was accepted: approximately (-130, -280, -410) mm.
Common completed 18 changed pairs without incomplete material operations.
All 184 uncertain occurrences belong to 04156745 / C04156745: 75 old,
109 new. Stationary native proofs timed out in solid symmetric difference;
subsequent rigid search timed out and propagated uncertainty to the remainder
of the definition pair. The rigid stage generated 4,974 candidate edges
across all families, not exclusively this one.

Revision-only comparison now excludes identified repeated definitions and
repeated engineering-name families from individual rigid motion search.
Counts use entire revisions, including already matched stationary copies.
World-position geometry matching still runs first, and global registration
still runs before this exclusion. Unique components retain movement search.
No uncertain stationary proof is converted to SAME or silently discarded.
Common candidate verification remains unchanged.

The regression case uses 120 old and 135 new occurrences: 60 stationary,
60 removed, 75 added, without individual rigid calls. It passes for shared
native definitions, independent definitions, and baked placements. Additional
checks preserve unknown stationary proofs and the global vector when repeated
parts have small local movement. Existing unique-motion and material tests pass.

This fixes speculative movement matching and avoids its unnecessary work.
It does not fix the underlying slow native proof of the user's 04156745
geometry. No predicted exact status counts or timing for the user's model
are claimed without rerunning it. Diagnostics contain no source STEP geometry.
