# DS Compare V3.6 — Geometry & Assembly Comparison

Nowa wersja: motyw jasny/ciemny, responsywny interfejs, podgląd kolorów 3D bez CADbro, masa części.

Więcej: `README_V36.txt`.

# DS Compare — porównywanie złożeń i geometrii

Samodzielna aplikacja dla Windows x64, wykorzystująca Open CASCADE. Eksperymentalny most DLL dla ZW3D 2019.

## Instalacja

1. Rozpakuj całą paczkę, pozostawiając katalog `_internal` obok programu.
2. Zakładka „Masa części” analizuje tylko jeden STEP/STP; generuje MASY_CZESCI.csv i RAPORT_MASY.html.
3. STEP z kolorami zapisuje teraz także kolory powierzchni oraz DIAGNOSTYKA_KOLOROW.json. W CADbro włącz cieniowanie z kolorami, nie sam szkielet/krawędzie.
2. Uruchom `DSCompareV3.exe`.
3. Wskaż starszy model A i nowszy model B w formacie STEP/STP.
4. Naciśnij „PORÓWNAJ B-REP”. Wyniki znajdziesz w wybranym folderze.
5. Odczytuj masę w kg; przyjmuje się gęstość podaną w polu programu (domyślnie 7850 kg/m³).
6. Jeśli potrzebujesz dokładnych fragmentów materiału dodanego i usuniętego, zaznacz opcję „Wyznacz dokładne różnice materiału”. Jest ona domyślnie wyłączona, ponieważ może znacznie wydłużyć obliczenia.

## Zawartość wyników

- `BOM_A.csv`, `BOM_B.csv` — wykazy części, separator średnik i przecinek dziesiętny dla polskiego Excela.
- `ZMIANY.csv` — wykaz zmian z polskimi nagłówkami i nazwami statusów.
- `RAPORT.html` — czytelny raport w języku polskim.
- `POROWNANIE_KOLORY.step` — kolorowy model porównawczy, gdy zaznaczono eksport.
- `ROZNICE_BREP.step` — materiał dodany i usunięty, gdy zaznaczono szczegółowe różnice.
- `PODSUMOWANIE.json` — techniczny format wymiany danych z interfejsem.

Nazwy w rodzaju `=>[0:1:1:102]` są wewnętrznymi odwołaniami STEP. Program próbuje użyć rzeczywistej nazwy komponentu; gdy jej brak, przejmuje najbliższą sensowną nazwę ze ścieżki złożenia. Nie da się odtworzyć nazwy, której sam plik STEP nie zawiera.

## Komendy integracji z ZW3D 2019

Po zainstalowaniu eksperymentalnej biblioteki `DSAssemblyCompare2019.dll`:

- `~DSCOMPARE_A` — eksport aktywnego modelu A.
- `~DSCOMPARE_B` — eksport modelu B i uruchomienie porównania.
- `~DSCOMPARE` — otwarcie aplikacji.

Podczas testów używaj kopii modeli. Kompilacja DLL w Windows nie stanowi potwierdzenia poprawnego działania w konkretnym ZW3D 2019.

## Informacje o programie

W działającej aplikacji naciśnij przycisk „O programie” — są tam dane o wersji i autorze.
