# Common preparation optimization (0.6.37)

Changes are limited to repeated-family candidate preparation:

* Skip residual spatial eligibility when every pair of a named family already
  shares the same nonempty population token. `allows` already admits all of
  these pairs; exact bounds cannot change that decision.
* Cache conservative bounds by occurrence for the lifetime of the existing
  immutable comparison policy. This avoids repeated OCP placement lookups
  for every pair and repeated eligibility pass.
* For generated names, reject disjoint conservative bounds and incompatible
  volumes before calculating precise extrema. Conservative overlap is never
  accepted as a geometry certificate. Precise overlap and native Common/Cut
  verification remain required for surviving candidates.

A local synthetic benchmark compared HEAD (0.6.36) with these changes using
actual OCP boxes, checking both eligible IDs and all allowed pairs for equality.
120/110 occurrences: 0.283415 s -> 0.069474 s in eligible(), with the same
result; broad-cache accesses fell from 13,320 to 230. 120/120: 0.243467 s ->
0.000241 s because no residual bbox work was needed. These are individual
microbenchmark timings, not a predicted whole-model speedup.

The reports' approximately 43-second precise-bounds stage includes work still
needed for later candidate comparison. This optimization does not imply that
all of those 43 seconds disappear. It also does not repair the native B-Rep
timeouts for family 04156745 or invalid Common topology in earlier reports.
