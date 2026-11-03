# Trident exact pair — iteration 6 evidence (2026-11-03)

Source run: https://github.com/damianink-png/test/actions/runs/41553622949 (commit ff919e4be5751f5f690cf5b79f3c2eefbfb38d67). This is a **FAILED, INCOMPLETE** full geometry run, not a PASS.

Inputs: A 192710725 bytes SHA256 e26006c887004d1dcacac36e08ca083268336d80668ea2d868a16e2b20aee370; B 185183500 bytes SHA256 416eda4e9212b894ed6f78ad3a6af55757115ebfcc4c18db933743d97dd48ccf. Both verified in strict audit.

Counts in partial PODSUMOWANIE.json: A=1551, B=1595, SAME=651, MOVED=198, CHANGED=2, ADDED=598, REMOVED=574, UNCERTAIN=272; total records=2295. Exactly 1551 A-side and 1595 B-side occurrence references are accounted for, but 272 are unverified. These are provisional classifications, not certified final results. 129 failed material pairs were reported (the strict audit excerpt lists 30). material_analysis_complete=false, analysis_complete=false. Strict audit errors: analysis_marked_incomplete, failed_material_pairs, partial_material_overlap, uncertain_records, unverified_record.

Elapsed 2783.116 seconds. Import A ReadFile=16.083s, XCAF Transfer=1641.750s; import B ReadFile=13.129s, Transfer=241.408s, despite persistent_cache=HIT for both. Major cost is XCAF transfer, not disk read. STEP export succeeded (main_step_ready=true, step_export_error=null), but it is a partial export and cannot certify the comparison.

Examples of failed pairs: A[31] B_Drive_Frame_Lower:1 vs B[44] b_stepper_lower:1 and A[80] A_Drive_Frame_Lower:1 vs B[50] a_stepper_lower:1: UnprovenRepair / invalid B-Rep after repair; A[232] A_Belt:1 vs B[639] A_Belt:1 and A[233] B_Belt:1 vs B[640] B_Belt:1: 35s isolated Common timeout; A[242]/B[363] M3 threaded insert / heat set: impossible negative signed Common volume -13.4305704 mm3. Other records were not attempted after operation/time budget.

Artifacts: diagnostics ID 13196121350; FAILED-BREP ID 13196680609; partial STEP/HTML ID 13196206098.

Next safe work: isolate and test those exact failed B-Rep pairs independently with BRepCheck and tolerances unchanged; identify whether negative signed Common is orientation/topology rather than valid overlap; optimize import via reuse of already-transferred B-Rep/XCAF representation (cache currently does not avoid transfer); cache geometric failure by canonical definition pair+transform+tolerance; ensure time-budget omissions are not silently promoted to ADDED/REMOVED. Add regression tests for failed-pair propagation and duplicate occurrence accounting. Do not increase tolerances or silently treat UNCERTAIN as confirmed.

No geometry algorithm patch is claimed in this iteration; no duplicate full run was launched.