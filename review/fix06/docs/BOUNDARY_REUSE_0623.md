# 0.6.23 — remove redundant boundary descriptors and retain proof diagnostics

The latest archive is incomplete: it ends in world-position matching, with no
final result, summary or completed material comparison. It cannot establish
the final number of uncertain parts. One native attempt exhausted its budget
in describe_shapes, before its actual boundary check.

Changes:
- The isolated boundary worker receives imported volume/area as advisory
  candidate-filter hints. It no longer recomputes full inertia, axes and bbox.
- Valid finite hints avoid mass/area reintegration too. Missing/invalid hints
  use native mass/area integration; repaired shapes always recompute them.
- Exact NURBS conversions reuse source hints while complete geometry proof
  remains mandatory. Forged equal hints cannot prove different geometry.
- Equal NURBS type histograms no longer skip UV-orientation verification.
- Bounded proof-stage history is saved atomically and copied into the parent
  journal on success, timeout and native failure. Rejection reasons identify
  topology-count, conversion, source-validity and surface/trim failures.

This changes neither user tolerance nor Common/Cut acceptance rules. It is not
a claim that the incomplete user comparison finished or that all previous
uncertain pairs have been resolved. Tests include cached-hint behavior, invalid
hints, forged hints on different solids, same-type NURBS with different UV
orientation, and diagnostic survival after a simulated native timeout.
