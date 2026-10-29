# DS Compare RC9 — 2026-10-29: Trident shifted torus false negative

Source: actual failed Windows [run 40789984229](https://github.com/damianink-png/test/actions/runs/40789984229), artifact `RC9-large-trident-shift` (`12862872177`). The original run had 4 old and 4 new unmatched parts, then Common A[245]/B[245] timed out at 90 seconds.

The `world_negative_02` pair has two valid solids (34638.704811 and 34638.785324 mm³). Face 337 is an oriented torus with:
- face centroid difference **0.000097 mm**,
- surface area difference **0.000770 mm²**,
- conservative face AABB difference **1.42 mm** after STEP re-export.

The old candidate filter rejected any non-B-Spline face whose AABB differed by more than 0.01 mm, even when its centroid agreed within 0.01 mm. This was **not** a valid necessary condition for the underlying trimmed analytic surface: a conservative bound can differ substantially due parameterization and trimming representation.

The independent `parametric_identity.prove` still checks analytic surfaces and **all oriented trimming wires/edges**; the AABB is merely a lookup hint. After removing only the redundant AABB rejection, all four captured Trident shifted pairs (`world_negative_02`, `03`, `05`, `06`) returned **True** locally using the full proof in 0.66–0.74 seconds each. The old prefilter returned False before reaching this proof.

Patch: `ci/patch_rc9_conservative_face_bounds.py`. This does not modify user tolerance **0.01 mm**, the physical geometry, SAME/MOVED rules, material Boolean validation, or export assertions. No face can be accepted by AABB or centroid alone.

**Separate unresolved large pair:** the same Trident shift artifact also contains a roughly 5.4 MB/5.6 MB B-Rep pair (`world_negative_01` and `04`) with one reversed B-Spline face orientation (A: 173 forward/157 reversed; B: 172 forward/158 reversed). It is not covered by the torus fix and must not be declared SAME without an independent oriented material proof. Thus four successful small-pair replays do **not** imply that Trident shift as a whole will pass.

The end-to-end Windows EXE run is still required: [workflow](https://github.com/damianink-png/test/actions/workflows/rc9-large-cad.yml). A positive local pair proof is not a six-case PASS. Trident revision's negative-volume Common remains a separate unresolved defect.
