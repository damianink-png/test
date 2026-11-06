# DS Compare 0.6.11 — incomplete native hypotheses and stale competitor vetoes

The user reports continued failure for an identical translated model, and
for a translated changed revision. Screenshots show two different outcomes:
no additional confirmed translation; and an unverified competitive B-Rep
hypothesis. An unknown rival is not evidence of a second correct frame.
Actual STEP inputs/native logs have not been supplied. These messages alone
do not identify the underlying native failure or prove this state bug caused
both real outcomes.

## Confirmed coordinator defects

0.6.10 called `finish(pose)` in its NativeGeometryFailure handler. The pose
was therefore both incomplete AND permanently on the completed-pose skip
list. The extended search could skip the correct vector, return None and
show the generic no-additional-translation message. A failed preliminary
sample with a few explicitly unknown native pairs could be finalized too.
An old incomplete competitor could retain its veto even after the kernel
would be able to finish its verification.

## Changes

Incomplete attempts remain pending. The explicit extended pass retries them
first, once per pass, with 24s per pair instead of 12s within the existing
60s extended body-search budget. Completed unsupported evaluations still
stay completed. Only an actual completed retry removes an incomplete veto;
a repeated unknown stays unresolved. Genuine competing confirmed frames
and all geometry thresholds remain conservative.

Completed positive pairs can resume only with the exact original inputs,
tolerance, rotation and translation. Saved proof-pose metadata is checked
again before any transfer. Unknowns and false values never become positive
certificates. A pending exact transform is retried even if a nearby transform
is already completed within the ordinary deduplication tolerance; that nearby
result does not certify the pending exact pose. A changed-transform regression verifies that retained positives
are not seeded into the altered frame.

`WYROWNANIE_DIAGNOSTYKA.json` is saved in the job directory before a decision
and remains after cancellation. It records pending vectors/rotations,
candidate and verified counts, attempts, native errors, resolved interruptions
and completed world-space samples. The failed-search confirmation preserves
these diagnostics. Error text identifies the rival and last error; no-new-
hypothesis text retains earlier sample counts instead of erasing them.
This file contains no source B-Rep payload, but may contain coordinates and
local exception paths. No user data is committed to the repository.

## Validation

Public coordinator tests simulate an initial transient native interruption,
then invoke real CAD proof on continuation. Other tests cover an incomplete
sample without a thrown exception; closed negatives not replayed; repeated
unknowns remaining unresolved; exact-pose positive proof retention; changed
pose protection; an actual wrong rival closed by native proof; a persistent
unknown rival still blocking; and diagnostics retained after cancellation.

The packaged synthetic diagnostic adds a deliberately injected interruption
on separately defined equal solids with different face partitions, then uses
the ordinary native engine to complete the search with 8/8 certificates.
The transient error is injected only inside this explicit synthetic check,
not in production comparisons. Diagnostic total is now 12. The existing
real-STEP translation, rotation, changed revision, repeated Common, six-of-
eight and independent local-motion checks remain in Windows CI.

This fixes a reproduced state-machine failure. It does not establish the
underlying cause or success on the user's unavailable STEP files. Original
+ translated STEP, or native trace/build diagnostics from that job, are still
needed to determine why the actual native proof did not finish.
