# RC7 iteration 1 — work in progress
Base RC6: d6829232754a3e0d98bb3426de2883006b8aafb0.
RC6 compiled six scenarios: original-coordinate revisions PASS, four shifted scenarios FAIL.
Distinct failures: Voron rigid native access violation at pair 1454/1454 (revision 1446/1454); Trident Common timeout at pair 3/3.
Local diagnosis of Trident extracted B-Rep pairs 3, 18, 53, 81: original scalar prefilter rejects. After bypassing scalar prefilter for diagnosis, unchanged exact validity/surface/trim proof succeeds at 0.01 mm. Bounding boxes agree within 4e-10 mm. No identity is inferred from scalar descriptors.
Changes: broader candidate-only scalar/centroid filters, original exact bounds and geometry tolerance retained; same candidate bounds in hypothesis ranking; retain native-failure B-Rep inputs in explicit CI diagnostics mode.
199 existing regression tests passed locally. 3 new tests passed. RC4/RC6 extra regression checks are included in TESTUJ.py.
Six compiled Windows scenarios are required before release. This is not a completed stable release.
