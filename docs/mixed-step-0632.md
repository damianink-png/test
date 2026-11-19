# Mixed STEP comparison: 0.6.32

## Reproduced numerical failure
An exact OCCT cylinder of radius 5 mm and height 11 mm has volume
863.937979737 mm³. After exact BRepBuilderAPI_NurbsConvert, the default
VolumeProperties overload reports 871.381143982 mm³. Adaptive integration
reports approximately 863.937979100 mm³ (native intersection results may
have their own small integration/trim differences). This is not a geometric
change or a reason to enlarge position tolerance.

The prior material pipeline rejected all eight changed repeated cylinders
as UNCERTAIN because Common/Cut volumes did not balance the inaccurate input
mass. Mass properties, inertia, centroid and area now use the Eps overload
with relative integration error 1e-12 throughout import, comparison, diagnostics
and material checks. Persistent import cache schema is invalidated.

## Routing defects
Small assemblies previously bypassed the isolated exporter-independent
boundary checks; strict centroid lookup could miss the pair before proof.
Mixed analytic/NURBS pairs now reach the complete boundary proof before an
ordinary coincident-surface Common can time out. Definition-local surface
histograms select the path only; they never establish equality. Proven repeat
reuse still verifies relative placement, so local movement is not hidden.

## External comparison (public documentation, not proprietary internals)
- SOLIDWORKS Import Diagnostics describes replacement of suitable B-spline
  surfaces by equivalent analytic ones and repair of geometry/topology:
  https://help.solidworks.com/2023/english/Solidworks/sldworks/c_Import_Diagnostics_Overview.htm
- Autodesk Inventor describes import checking and healing with an Allowable
  Change tolerance, not unconditional acceptance of translated geometry:
  https://help.autodesk.com/cloudhelp/2026/ENU/Inventor-Help/files/GUID-1F054A20-AB49-4063-819B-7CF4DC83FFF1.htm
- OCCT documents adaptive integration via Eps; values over .001 select
  non-adaptive integration. The installed OCP overload documentation was
  checked alongside the numerical reproduction.
  https://www.occt3d.com/dev/doc/refman/html/class_b_rep_g_prop.html

No STEP re-export or mesh-only equality was introduced. Common/Cut still
requires valid topology and balanced positive material volumes. Tests use
synthetic analytic/NURBS models; unavailable customer STEP files remain
unverified. Adaptive integration may cost more per unique curved definition;
whole-analysis speedup on customer models has not been measured.
