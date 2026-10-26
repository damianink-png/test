# RC10 review and RC10.1 checkpoint

Base: main 1b7e0511a3bfe64996bf74c784b20b2713976f25, exact DSCompare_RC10_GitHub_CI.zip.
Evidence: GitHub run 40355667751. One of six real compiled CAD scenarios passed.

| Model/case | EXE seconds | Outcome | Last pair |
|---|---:|---|---|
| V2 revision | 337.89 | PASS: SAME 1682, ADDED 28, MOVED 5, REMOVED 20 | — |
| V2 shift | 1410.98 | Common timeout 35 s | 84 / 84 |
| V2 revision + shift | 1466.48 | Common timeout 35 s | 84 / 84 |
| Trident revision | 474.05 | Common timeout 35 s | 679 / 679 |
| Trident shift | 1076.08 | Common timeout 35 s | 178 / 178 |
| Trident revision + shift | 1030.62 | Common timeout 35 s | 178 / 178 |

These are EXE durations, not whole CI job durations. Faster jobs across runners do not establish an algorithmic speedup.
All five failures terminate cleanly with code 1; these logs do not establish native access violations or a corrupt STEP.
The STEP written immediately before comparison in shifted tests is the harness-generated shifted INPUT, not evidence that the application exported an aligned STEP.

## Verified code defects and changes

- Aligned stage-one lookup used strict integrated centroid and descriptor filters even though the subsequent surface verifier uses a wider candidate search. Use the verifier's candidate radius only after accepted alignment; every new candidate still requires the original tolerance CAD proof.
- Residual old/new parts entered Common directly. Add one isolated, non-Boolean identity check for uniquely corresponding candidates before Common. Only an actual full surface + oriented trim proof can yield SAME. Ambiguous duplicates remain on existing path. Timeouts abort, never certify identity.
- Reuse the already implemented scoped native proof worker after alignment, without carrying old comparison results or enlarging geometric tolerance.
- Preserve failed BREP inputs by default; record Common worker phase and a child stack dump at 20 seconds, before the existing 35-second deadline. Log pair indices, names, volumes, centroid distance and bounds.

## Validation and limits

Five targeted local tests pass: descriptor drift, real geometric change rejection, ambiguity, timeout propagation and aligned candidate lookup. Installer verified against clean RC10 archive.
Windows regression, build, six small EXE cases, then six large real CAD cases are gated in rc101-proof-recovery.yml.
The new candidate rescue is not yet proven to resolve the actual complex Voron pairs. Full geometric proof can remain inconclusive and genuine modified solids can still exceed Common deadline; these must remain incomplete, not falsely marked SAME.
Local extraction of representative Trident BREP fixtures is in progress and must not be reported as a passed comparison.
