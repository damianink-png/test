# RC9 — Trident revision: Common sensitivity and BOP cross-check (2026-10-29)

## Reproducible inputs

Source: GitHub Actions run [40779014276](https://github.com/damianink-png/test/actions/runs/40779014276), artifact **RC9-large-trident-revision** (ID `12857144315`), directory `evidence/comparison/FAILED_BREP/common/`.

- A.brep: 148116 bytes, SHA-256 `e4f7b5c7718d6e8a9066e0e8d11beeddc7f5442c6f51356d04132b957667a2e6`
- B.brep: 150444 bytes, SHA-256 `688c2bb7447200fc28648ee7bc2a137d8b390661ecf6843fb7058cef092055ec`
- Runtime: `cadquery-ocp==7.9.3.1.1`, isolated local subprocess per configuration.
- Both inputs pass `BRepCheck_Analyzer.IsValid()`, each has one solid and 112 faces.
- Input signed volumes: A `6209.135907780914 mm³`, B `6244.723869371624 mm³`.

## Results — never a valid geometry verdict

| Common fuzzy (mm) | Signed result volume (mm³) | BRepCheck result | Observed solids |
|---:|---:|:---:|---:|
| 0.000001 | -15.544600449960383 | invalid | 3, all negative |
| 0.0001 | -122.58159431091562 | invalid | 5, all negative |
| 0.001 | -122.58159431091562 | invalid | 5, all negative |
| 0.005 | -122.58159431091562 | invalid | 5, all negative |

Independent direct `BOPAlgo_BOP` COMMON at fuzzy `0.0001 mm`: default, `SetCheckInverted(False)`, OBB disabled, both disabled, and parallel processing all returned **invalid topology** and signed volume `-122.58159431091562 mm³`. This shows that swapping the API wrapper or simply increasing the fuzzy parameter does **not** resolve the problem.

These are diagnostic-only probes, **not** changes to the production comparison tolerance of **0.01 mm**. Negative volume must never be converted to positive using `abs()`, and an invalid Common cannot prove SAME, MOVED or material delta.

## Current verification

[Run 40789984229](https://github.com/damianink-png/test/actions/runs/40789984229) has a successful Windows build and successful V2 revision scenario; the other five CAD jobs were still running when this note was prepared. No new application algorithm change is justified by these probes.

## Next engineering steps

Inspect OCCT's section/interference graph and coincident face classification for the exact pair; evaluate any proposed reconstruction with independent closed-shell validity, positive oriented solids, and two-way geometric/material conservation checks under the unchanged 0.01 mm limit. Keep the native worker fail-closed and retain STEP/HTML/BOM assertions. Avoid promoting diagnostic workarounds to production without proof.
