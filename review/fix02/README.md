# RC9 — poprawka testów przesunięcia 02

Te czytelne pliki odpowiadają plikom z kompletnego ZIP-u `DSCompare_RC9_KOMPLET_ZRODLA.zip`. Są przeznaczone do przeglądu zmian. Workflow buduje i testuje kompletny ZIP, sprawdzając jego SOURCE_MANIFEST.json.

SHA-256 plików w archiwum:

```json
{
  "dsac29/parametric_identity.py": "93082cc49056889f5065ae9e5baca9d9bdfc7da6ca4b4a7c0f575b9290a7c666",
  "dsac29/step_reexport_tolerance.py": "2b5ee1b77c2b928e8e4d8aa3e1190093568c552c3cc476aa72f2305700855688",
  "ci/run_manual_regressions.py": "44e6913c826c9b42f499af49b605d2abd56254109954c9070394e7cf5bb657c0",
  "tests/test_fractional_shift_topology.py": "ecd8d279e955e2f893165fe88a087b3d56db81849e98cc50d273376673f2523b"
}
```

Poprawki obejmują analityczne ograniczenie całych płatów mikrocylindrycznych i ich rzeczywistych krawędzi oraz usunięcie filtra różnicy objętości, który odrzucał zgodną powierzchniowo parę Trident. Filtr pola powierzchni zachowano, aby nie zaburzać wykrywania przesunięcia w mocno zmienionych rewizjach.
