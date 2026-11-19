# Boundary verification performance, 0.6.34

This is a review of the slow boundary-verification path from the supplied
0.6.32 logs, not a complete audit of every application module or a benchmark
against proprietary CAD programs.

## Comparison with publicly documented approaches

SOLIDWORKS Import Diagnostics checks and repairs imported geometry/topology,
and can replace B-spline surfaces with equivalent analytic surfaces:
https://help.solidworks.com/2023/english/Solidworks/sldworks/c_Import_Diagnostics_Overview.htm

Spatial describes stitching, geometry simplification, and gap tightening.
It specifically relates analytic simplification to smaller data and faster
subsequent operations:
https://blog.spatial.com/healing-as-an-essential-function

OCCT documents the distinction between ordinary and more precise bounding
methods. Precise bounds are not free; the existing proof needs them but
repeated calculation on the same immutable operand does not add evidence:
https://www.occt3d.com/dev/doc/refman/html/class_b_rep_bnd_lib.html

These sources describe approaches, not public access to proprietary algorithms.
No user STEP files were executed in SOLIDWORKS or Spatial products. This change
does NOT introduce blanket shape healing or spline fitting.

## Changes

1. Before expensive bounds/integration, reject a direct face-type comparison
   that the old implementation would necessarily reject later. Normalization
   and solid-set proof remain available in the enclosing worker.
2. Reuse original face descriptors within ONE native request. Cache keys verify
   exact TopoDS identity, orientation and location; nested requests get fresh
   scopes, including the persistent worker. No positive proof is cached here.
3. Find a complete face bijection using lazy native edge verification and
   augmenting paths. Every assigned pair still needs the original complete
   surface/trim proof. Alternative assignments remain reachable; no greedy
   geometry verdict and no equality based on area/bounds.
4. Report original-boundary descriptor A/B and per-face progress so a timeout
   can identify descriptor calculation versus a specific proof candidate.

## Local validation

38 targeted tests passed, including mixed-export Common, moved occurrences,
NURBS boundary/orientation, cache scope and exhaustive matching oracles.
A synthetic 108-face NURBS assembly, three descriptor passes: uncached 0.2900 s,
request-cache 0.0946 s (~3.07x for this operation only). A dense 40-face matching
oracle used 40 proofs instead of eagerly testing 1600 candidate pairs.
Neither measurement is an end-to-end speedup claim for the unavailable user
STEP files. Full regression and Windows packaging run separately in CI.
