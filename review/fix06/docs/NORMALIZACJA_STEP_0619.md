# 0.6.19 — same-domain boundary proof

The original face matcher requires equal face counts. A STEP exporter can split
one analytic face into several without changing material, sending equivalent
solids to expensive directional Boolean differences. This release inserts an
independent normalization path before those differences.

The isolated native worker copies valid, single-shell solids, unifies redundant
same-domain faces/edges with OCCT, disables spline concatenation and internal
edges, checks validity, solid/shell count and conservation, then performs the
existing complete oriented surface and trimming-wire proof. It does not change
placement or infer equality from names, mass properties or repeated counts.
The proof uses half the caller's tolerance; unification uses 1e-7 mm and 1e-12
radians. At tolerances below 1e-5 mm this optional path is disabled.

Scope: planar, cylindrical, conical, spherical and toroidal source faces.
Unsupported, invalid, multi-shell, inconclusive or failed normalization falls
back to the original solid-set proof. This is not arbitrary shape healing and
not a guarantee for every ZW3D export. The original Common/Cut algorithm for
actual material changes is unchanged. Recognized unchanged parts no longer
need that fallback merely because their faces were repartitioned.

Regression coverage includes split planar faces, unchanged source B-Rep bytes,
local movement, added holes, different equal-volume shapes, tiny tolerance,
and actual AP203/AP214 STEP write/read roundtrips in translated coordinates.
Existing pipeline tests additionally cover repetitions and global alignment.
