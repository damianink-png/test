# DS Compare 0.6.7 — placement failures and independent native evidence

Baseline: 0.6.6, commit 4c52a65be11bddce2056264b372aed0bd45e4b9d.

The supplied 0.6.6 screenshots show zero whole-body proofs out of 24,
then an incomplete proof and an unsuccessful expanded search. The user also
reports that an identical revision exported at a different position fails.
No source STEP pair or diagnostic files have been supplied. The exact cause
of that real failure is **not established**. A changed revision alone does
not explain the reported identical-revision failure.

## Reproduced problems and changes

* Rotation candidates previously called full `describe` for every placed
  body before attempting the first native proof. Rigid invariants are now
  propagated algebraically during candidate preparation; accepted final
  report geometry still receives the normal exact descriptors. Preparation
  checks cancellation and the deadline. An expired preparation no longer
  manufactures unverified geometry results or marks an untested pose as done.
* The analytic whole-body check rejects physically identical valid solids
  when a STEP export partitions their faces differently. Registration and
  comparison in a verified frame can now prove equality using the existing
  native two-directional empty-difference test on valid original solids.
  This explicit opt-in never repairs an invalid original or substitutes
  equal mass/area for geometry. The native subprocess deadline still applies.
* Native vertex averages can change with face partitioning. Whole-body
  hypothesis scoring, proof candidate lookup and final registered lookup
  also consider mass centers, with one-to-one assignment and native proof
  required. A global center offset is only a candidate hint when population
  counts agree. Neither landmark source is an equality certificate.
* When whole bodies have changed, preserved original faces can establish a
  candidate frame independently. This bounded fallback checks original
  underlying surfaces, every trimming wire and edge with strict repair off.
  It requires at least eight proven faces across at least four bodies on
  each side, noncollinear anchor positions, and either independent surface
  directions or corroboration by a genuine native whole-body proof.
  Equally supported different placements remain unresolved.
* Surface evidence carries **no certified whole-body pairs**. Any nonzero
  frame based on it requires explicit user approval, including after an
  expanded search. The final whole-revision material comparison is separate.
  An identity frame does not request relocation. The UI shows the proposed
  translation, rotation and surface evidence, including rotation-only poses.
* Expanded-search diagnostics count completed translation and rotation
  hypotheses. Logs explicitly distinguish an applied frame from comparison
  in the original position. A failed search does not authorize relocation.

## Validation

New native regression fixtures cover: every body changed by a through-hole
(with translation and rotation), original-frame changed bodies, rejection of
changed trimming on a shared plane, native failures, explicit approval after
Search, and final CHANGED classifications after surface-frame approval.

Identical-revision fixtures cover eight translated solids whose native face
partition differs (both biased and unbiased vertex averages). They must
finish as SAME only after real whole-body proof. Equal synthetic mass and
area with different real material must fail that proof. Candidate preparation
also tests 380 bodies without repeated mass-property integration.

The frozen-worker smoke suite independently writes and reads STEP files for
both the changed-body surface case (CHANGED 8) and repartitioned identical
solids (SAME 8), in addition to the previous arbitrary rotation (SAME 18),
repeated Common, name-family and count mismatch cases. Browser interaction
tests verify that a surface-based rotation waits for an explicit click.

CI records actual outcomes. These synthetic fixtures establish the behavior
of these cases, not a successful reproduction of the user's unavailable files.
The Common name-family and equal occurrence-count rules from 0.6.6 remain.
