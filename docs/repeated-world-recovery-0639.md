# Fixed-position repeated-family recovery — 0.6.39

Recent reports contain 53–55 stationary candidates of 04156745 where the
original isolated world test timed out after 25 seconds. Two such timeouts
left every equivalent relative placement unknown. Individual rigid search
is intentionally disabled for repeated occurrences in revision mode.

After a timeout, a repeated native definition pair now gets one additional
isolated original-geometry proof with a 75-second bound. Both operands are
translated by exactly the same vector toward the origin. No relative pose
is fitted, no geometry is repaired into an equality certificate, and numeric
moments/names alone cannot produce SAME. The existing complete boundary and
validated solid-set proof runs in the worker.

Only a completed positive proof enters the existing world-anchor cache.
Every other occurrence must share the native definitions and pass the
relative-placement check. Locally moved occurrences remain unmatched.
Negative/incomplete recovery never becomes SAME. There is at most one
additional attempt per definition pair per final comparison. Existing
world-failure limits still apply, including their second ordinary probe.
Thus a failed recovery can add up to 75 seconds; this is not a guaranteed
speedup. A successful proof can avoid many subsequent unverified candidates
and material comparisons.

Validation: 42 world/repeated-policy tests passed, plus a new real analytic
box vs NURBS test (6 focused recovery tests passed). The latter accepts the
same physical placement and rejects a 0.2 mm local movement at 0.01 mm
tolerance. Tests also cover 120 occurrences, positive/negative/timeouts,
input immutability, one recovery per family, and unique-part exclusion.
The full suite and Windows OneEXE workflow run separately.

User STEP geometry is not included in diagnostics. Whether this completes
the difficult 04156745 proof within the budget must be verified on that model.
