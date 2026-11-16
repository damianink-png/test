# 0.6.22 — physical NURBS orientation

The newly supplied 0.6.21 diagnostics still show 114 unverified occurrences.
The unchanged-part family has mixed FORWARD/REVERSED faces in the old model,
while the exporter uses FORWARD for every new face. Both the candidate filter
and the boundary proof previously treated these flags as directly comparable.
They are not: reversing one surface parameter reverses its parametric normal.

The opt-in NURBS comparison now admits candidate faces regardless of their
TopoDS orientation flag. Acceptance requires a complete rational Bezier patch
bound under one of the eight global UV swap/reversal mappings. The mapping's
orientation parity must compensate the TopoDS orientation difference. Every
surface patch and every oriented trimming wire must still pass. Flag-only
reversal, changed interior geometry and changed trims remain rejected.
Original shapes, placement and user tolerance are unchanged.

This does not make arbitrary NURBS parameterizations interchangeable: different
patch partitions, degrees or supporting domains may still need the original
solid-set fallback. Common/Cut recovery for genuinely revised parts is unchanged.
No result on the user's actual solids is claimed from diagnostic summaries.
