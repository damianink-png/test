# DS Compare 0.6.9 — delay after revision classification

The screenshot ends with classification of 1692 records in 0.4 seconds and
no additional classification B-Rep tests. The next operation is
`merge_material_revisions`. Its full-model occurrence grouping could perform
many native rigid tests before the first material-stage progress message.
The UI therefore retained the earlier "Ruch części" phase. The supplied
screenshot does not identify the exact user-model timings or outcome.

This full-model grouping already exists in the 0.6.3 source; it was not added
by the 0.6.8 unique-anchor change. Common initialization could also repeat
completed negative congruence results: it checked only cached positives.
Native errors/timeouts must remain unknown, not false cached verdicts.

The new policy explores only geometry components touching the original
removed/added Common operands. It includes every matching occurrence in the
WHOLE revision, including SAME/MOVED survivors and excluded operands that may
be restored by the equal-count/name rule. No native comparisons between
unrelated unchanged families are required. A component is expanded only by
actual native identity, exact definition or completed geometric proof;
numeric equality and names remain lookup hints. Normal full-population API
calls retain full behavior. Focused APIs reject operands outside their
computed scope. Repeated-population diagnostic counters now explicitly mark
their scope as families touching Common operands.

A tristate registry lookup reuses completed true AND false results at exactly
the same tolerance. A native timeout/exception is not cached. Progress switches
to material preparation before population checks and reports native work.
`CZASY_ANALIZY.json` separately records occurrence classification and material
revision matching. Material diagnostics include preparation time and scope.

Reproduction with independent baked box solids (24 unchanged parts and one
unique changed operand per revision): old policy construction executes 46
real isolated native rigid proofs and takes 52.922 s; focused construction
executes zero native proofs and takes 0.001812 s. These numbers cover only
policy construction, not full comparison/import/Common/Cut/export. See
population-preparation-benchmark-069.json. Reproduce with the corresponding
source PYTHONPATH and portable/tests/population_preparation_benchmark.py
argument `old` (full scan) or `new` (focused scan).

New tests exercise unrelated SAME-family exclusion, full-revision 8-vs-7
counts with only one free operand per side, focused/full policy agreement,
negative-proof caching with separate tolerances, retryable native unknowns,
and the material progress transition before grouping. Existing Common,
repeated naming/count, ambiguity and registration tests remain in CI.
This is a reproduced bottleneck and fix, not confirmation of the exact
cause or full runtime on the user's unavailable STEP pair.
