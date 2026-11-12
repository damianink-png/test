DS Compare 0.6.16 fixes repeated work found in the 0.6.15 diagnostic package.

- Parallel and persistent import now preserve the source-scoped XCAF definition
  identity. Each import has an immutable namespace, so overwriting a STEP at the
  same path cannot merge two different revisions. Old cache schemas are rejected.
- Normalization retains native TShape handles, preventing wrapper lifetime from
  defeating the cache for repeated occurrences. Placements remain independent.
- Common candidate selection and material matching share exact world bounds.
  A native definition at the same rotation reuses bounds under translation;
  replaced geometry and different rotations require fresh bounds.
- Extended registration retains completed negative checks as well as positive
  proofs only at the exact same pose of the same bound inputs and tolerance.
  Unknown results remain retryable. Alternative spatially diverse witnesses are
  tried before previously slow pairs, with unchanged sample acceptance thresholds.
- Expired anchor searches no longer erase previous anchor diagnostics. Common
  diagnostics now distinguish eligibility work and precise-bound calculations.
  Normalization duration no longer overwrites the journal's elapsed timestamp.
- The navigation item is now “Diagnostyka”, directly above “O programie”, using
  the same navigation font. The page title and breadcrumb use the same name.

New regression coverage checks import transport, persistent-cache invalidation,
independent placements, native-handle reuse, translation/rotation/mutation of
cached bounds, exact-pose negative continuation and sample replacement without
shrinking the sample. Existing global/local movement, repeated-name Common and
STEP re-export tests remain in the Windows build gate.

This release does not replace the CAD engine wholesale or remove native process
isolation, geometry validation, one-to-one occurrence accounting or final-frame
verification. The earlier audit is a record of 0.6.15; larger architectural
recommendations such as replacing the baseline-plus-patches build remain separate.
The attached user bundle contains diagnostics but not the original STEP inputs,
so their exact native geometry and elapsed-time improvements require a new run.
