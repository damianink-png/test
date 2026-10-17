DS Compare V3.2 FAST / zmiany B-Rep
Designed & developed by Szymczyk Damian

1. Windows 64-bit: rozpakuj całą paczkę z GitHub Actions. Uruchom DSCompareV3.exe.
2. Dla aktualnie wyeksportowanych modeli STEP/STP wskaż Model A i Model B.
3. Porównaj B-Rep i przejdź do Wyniki. Sprawdź ROZNICE_BREP.step.
4. W ROZNICE_BREP.step: fioletowy oznacza dodany materiał, pomarańczowy usunięty.
   Przesunięte elementy są pokazane jako stare i nowe położenie tylko w tym dodatkowym pliku.
5. Pełny POROWNANIE_KOLORY.step nadal przedstawia aktualny model + usunięte części.
6. Przy dużych złożeniach odznacz "Kolorowy STEP (pełny model)" by przyspieszyć zapis.
7. Analiza wykonywana jest w odrębnym procesie Windows. Można ją zatrzymać przez Anuluj.
8. Cache B-Rep stosuje tylko tożsame instancje TShape oraz sprawdzone pary geometrii.
   Dla 300 instancji test dopasowania 1 parą Boolean zajął ok. 0.05s na środowisku testowym.
   To nie jest całkowity czas analizy importu ani eksportu STEP.
9. Dla ponad 60 par CHANGED szczegółowy STEP z różnicami nie powstanie,
   a program zapisze stosowną uwagę; porównaj wtedy mniejsze podzłożenie.
10. Integracja ZW3D 2019 DLL jest nadal eksperymentalna. Nie zmieniaj oryginałów Z3.

Komendy ZW3D: ~DSCOMPARE_A, ~DSCOMPARE_B, ~DSCOMPARE. Kopię DLL wykonaj przed podmianą.
