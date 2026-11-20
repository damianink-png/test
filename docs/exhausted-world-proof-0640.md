# 0.6.40 — stop replaying exhausted solid subtraction

Diagnostic DSCompare_1795162993603471500.zip uses 359c641 / 0.6.39.
Total time: 994.764 s. Status counts remain 178 SAME, 18 CHANGED,
3 MOVED, 126 REMOVED, 300 ADDED, 110 UNCERTAIN. The new local recovery
consumed 75.369 s at validated_solid_symmetric_difference and timed out.
The following identical-relative-placement occurrence consumed another
25.387 s in the same operation. Neither added a positive proof.

Recovery now recognizes a timeout explicitly attributed to the final
validated solid subtraction. For a repeated native definition pair it does
not replay the local 75-second pipeline, and the ordinary world matcher
retains UNKNOWN for copies at the same relative placement without a second
native probe. Different relative placements remain eligible for independent
checks. A generic timeout earlier in boundary work retains the alternative
local-coordinate recovery path. No timeout is converted to a mismatch or SAME.

This avoids the two observed repeated operations (about 100.8 seconds in
this particular log). It does not fix the underlying failure to prove the
55 stationary pairs. No whole-analysis timing or successful matching is
claimed without rerunning the user's model. Tests cover native-proof reuse,
true/false/timeout responses, different relative positions, and real analytic
vs NURBS geometry. Full CI includes the existing Common and motion tests.
