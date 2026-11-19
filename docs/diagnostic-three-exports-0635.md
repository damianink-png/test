# Three-export diagnostic comparison — 0.6.35

Input: Bez przesuniecia oryginalne step.zip, three reports from 9a633f6 (0.6.34).
The archive contains diagnostics, not the source STEP geometry. The original
export is a comparison baseline, not ground truth for every detail.

| Run | Parts A/B | Outcome | Total time |
| --- | --- | --- | --- |
| Original STEP, stationary | 380/560 | 18 CHANGED, 179 SAME, 7 MOVED | 327.8 s |
| Both exported through ZW3D, translated | 379/554 | 12 CHANGED, 231 SAME, 7 MOVED, 4 UNCERTAIN | 555.7 s |
| Mixed exporters, translated | 380/554 | Alignment unresolved, then cancelled | Incomplete |

The mixed run proposed approximately (-130, -280, -410) mm. Its expanded
sample had 50 positive native proofs out of 64, but the old 80% rule required
52 even when some native operations were unfinished. Cancellation is not a
native crash. The two completed reports also differ in imported part counts;
identity of the exported geometry cannot be established from logs alone.

## Changes

* Strip a terminal `_PRT` object suffix before parsing the separated revision.
  `04244035_PRT`, `04244035_AF0_PRT`, and `04244035_AF1` can now reach the same
  repeated-family candidate gate.
* Infer the numeric `C` prefix convention only after three distinct drawing
  families demonstrate it through already verified stationary pairs. Block
  aliases when both prefixed and bare names occur in the same revision.
  Original names and rename reporting are preserved. This is candidate
  selection only: Common/Cut still proves the actual material change.
* Report unfinished checks in the selected alignment sample, including
  skipped repetitions of failed native checks. They are not negative proofs.
* Conditional frame recovery requires at least 75% positive proofs across
  the whole sample, 80% among completed checks, 40 completed checks, at most
  20% unfinished checks, independent diverse spatially spread geometry, and
  improvement over the original pose. Rival-hypothesis checks remain.
  Unknown parts are never certified as SAME. Final per-part comparison remains.

## Validation and limits

79 targeted regression tests passed locally on the assembled shipped engine.
Added actual native Common tests for repeated `_PRT` names and learned numeric
prefixes; checked absent/insufficient evidence, aliases, ambiguous collisions,
50/64 recovery, repeated/collinear anchors, local motion and timeout accounting.
The complete CI regression suite and Windows OneEXE build run separately.

Two ZW3D material pairs (04244003 and 04244004) failed with invalid/null Boolean
results even after recentering. These changes do not declare invalid topology
valid or convert unknown material into a match. Those failures remain an open
issue requiring a reproducible geometric case. No end-to-end speedup or 100%
STEP exporter compatibility is claimed from diagnostic-only inputs.
