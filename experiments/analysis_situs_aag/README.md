# Analysis Situs-inspired AAG experimental benchmark

This branch is isolated from production \`DS Compare\`. It does NOT import
Analysis Situs C++ or replace the native CAD comparator.

It implements the AAG concept (face nodes, shared-edge links, analytic
surface types) with the OpenCascade/OCP already present in DS Compare.

## Safety
- AAG is a **soft priority**. It NEVER certifies SAME, rejects a candidate,
  changes a tolerance, or changes the Common/Cut geometry.
- Exactly the SAME candidate set goes through two-direction real OCCT Cut
  in both arms.
- Separate regression: equal volumes and world geometry with different
  face counts (6 vs 10). Identical AAG would give a false negative.
- All source geometries remain unchanged.

## Benchmarks
- Ordinary assembly: different envelopes, similar to cases where current
  volume/bbox priority is already strong. AAG is activated only on ties.
- Ambiguous co-located plate/cylinder/torus/bent-profile: same outer box,
  many plausible neighbors; AAG should reduce native candidate trials.
- Actual STEP writer -> STEP reader sanity for the four analytic families.

Use \`pip install cadquery==2.6.1\` then
\`python experiments/analysis_situs_aag/prototype.py results.json\`.

The CI stores a JSON artifact. Look at **native calls, actual seconds,
incorrect pairings, candidate set preservation, and preprocessing overhead**.
Benchmark time is for isolated candidate-stage Cuts only, not the full
portable OneEXE, and does not establish speed on user's unavailable ZW3D
STEP inputs.

## Integration criterion
Do not merge before real ZW3D AP203/AP214 files with changed face partitions,
complex bent parts and high-repeat assemblies demonstrate:
- 0 lost actual SAME/CHANGED pair candidates or false positives;
- strict B-Rep and material partition still required;
- lower total elapsed time (including feature extraction and cache misses)
  in representative end-to-end assembly comparisons.
