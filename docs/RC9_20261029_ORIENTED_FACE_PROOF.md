# DS Compare RC9 — 2026-10-29: two distinct Voron V2 re-export failures

Source: real Windows artifact `RC9-large-v2-shift`, run [40789984229](https://github.com/damianink-png/test/actions/runs/40789984229), artifact ID `12863561317`. The same baseline still failed 5/6 scenarios in run [40801184501](https://github.com/damianink-png/test/actions/runs/40801184501). These are *not* synthetic STEP examples.

## Small pair: false negative from excessive internal proof margin

`FAILED_BREP/world_negative_02/A.brep` and `B.brep` are both valid. Their volumes are 57618.281295 and 57618.282058 mm³. One oriented straight trimming edge differs by approximately 0.002788 mm after re-export, below the required 0.01 mm tolerance but above the old internal `tolerance/8 = 0.00125 mm` predicate.

Local independent analytic surface + **all oriented edges** proof returned `True` in approximately 0.07 s using a half-budget (0.005 mm) predicate. It still rejects synthetic 0.012 and 0.020 mm shifts, and the repair-only path retains its previous strict proof. No mesh, bounding box, volume or sampled point alone establishes SAME.

Implemented in `ci/patch_rc9_oriented_trim_budget.py`: try the original strict proof first, including its original bounded micro-seam handling; only if inconclusive, try `tolerance/2` with **no micro-edge deletion**. This keeps the surface/trim accumulated budget within 0.01 mm.

## Large pair: genuine oriented-face inconsistency, not just numeric drift

`FAILED_BREP/world_negative_01/A.brep` and `B.brep` each have 718 faces. Original A is BRepCheck-invalid; B is valid. A's strict repaired copy is valid, but one B-Spline face orientation remains inconsistent:

| Face type and orientation | A | B |
| --- | ---: | ---: |
| B-Spline FORWARD | 175 | 174 |
| B-Spline REVERSED | 159 | 160 |

Candidate original A face 617 and B face 10 share the underlying B-Spline surface to within 0.005 mm, but have opposite orientation flags. At the same projected surface point, the underlying geometric normal is approximately `(0.491831, 0.504435, 0.709681)` for both; after face orientation is applied, their **physical oriented normals are opposite**. Therefore they must not be declared SAME under the required oriented-face proof. This cannot be fixed safely by ignoring orientation or comparing volume only.

The old recursive perfect-face matching could spend over 90 seconds on this impossible 718-face bijection. The new `ci/patch_rc9_face_matching.py` checks the complete face-type/orientation multiset first, then uses iterative augmenting paths. A local negative check of the actual large pair now returns `False` in about 10 seconds including face descriptors, without claiming a false SAME. A synthetic 718-face dense impossible matching returns in under 0.1 s locally. **This is a fail-closed performance fix, not a proof of equivalence for this large pair.**

## Remaining blocks

1. The large V2 oriented-face inconsistency remains unresolved. A valid orientation-changing repair would require an independent proof that it preserves the *material region* of the invalid original, not just surface locations.
2. The V2 material Common still times out after the unmatched pair reaches revision matching. Do not replace the missing Common with a guessed result.
3. Trident revision Common still returns invalid negative signed volume and unorientable output faces; shifted Trident cases remain incomplete.
4. Full six-case Windows EXE, STEP/HTML/BOM audits are mandatory before declaring success.

Current patch branch: `fix/rc9-oriented-trim-budget-20261029`. User tolerance remains **0.01 mm** and all fail-closed classifications remain enforced.
