# Diagnostic 1795155624145804700 / 0.6.38

Input engine: 8f4b664 (0.6.37). Total 1099.58 s; material matching
680.81 s. 18 CHANGED, 178 SAME, 3 MOVED, 126 REMOVED, 300 ADDED,
110 UNCERTAIN. Uncertainty covers 55 old and 55 new occurrences of
04156745 / C04156745. Registration succeeded; world verification still
times out on the representative repeated definition.

Two Common candidates (227/209 and 228/210) returned invalid non-null
Common shapes. The fresh partition and local-coordinate partition also
failed. This route recorded generic BOOLEAN_FAILED rather than a terminal
native geometry failure, so the post-pass retried Common and partition.
Those redundant post-pass operations consumed 192.617 s in this report.

The fix labels exhausted deterministic partition recovery consistently and
skips that post-pass retry. Unknown remains unknown. Successful local
recovery still works, temporary transport failures remain retryable, and
budget-omitted candidates retain their retry. Five targeted tests passed,
including deterministic-vs-transient behavior and successful local recovery.
The full regression suite and Windows packaging run separately.

This removes a specific unnecessary retry path. It does not establish
geometric equality of the 55 pairs, repair their topology, or guarantee a
193-second saving on another model or machine. No source STEP is included
in the diagnostic archive.
