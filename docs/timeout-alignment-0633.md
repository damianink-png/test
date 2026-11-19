# 0.6.33: analysis of diagnostic package 1795072921226104400

Both runs identify engine commit b7b83fa (0.6.32).

Run 1795072636200025100 estimated B-to-A translation (-130,-280,-410) mm.
The extended nested sample confirmed 38/48 pairs, below the 90% strict gate
and just below the existing 80% recovery gate. Two pairs timed out on family
04156745/C04156745; a competing nearby hypothesis exhausted the CAD deadline.
0.6.33 allows one bounded expansion from 48 to at most 64 observations for
borderline >=75% support with >=80% preliminary support. It keeps the SAME
cache, negative observations, tolerance, deadline and admission gates. The
remaining per-part comparison still validates every uncertified part.
This gives another opportunity, not a guarantee of alignment on these files.

Run 1795072921226104400 had 304/379 stationary matches. An unhandled
NativeGeometryFailure in the rigid search then terminated the whole job.
0.6.33 records it as pair-local uncertainty and skips repeated rigid searches
of the same definition pair. It preserves independently verified SAME/MOVED
results. It never caches timeout as a negative geometry result or equality.

Tests model the fatal timeout with independent SAME/MOVED parts and repeated
failed definitions, and the 20/24 -> 38/48 -> 54/64 nested proof sequence.
Actual STEP geometry is absent from the diagnostic archive; the slow original
boundary proof on 04156745 has not been reproduced or solved by this patch.
