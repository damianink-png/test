# DS Compare 4.1 — analiza V4.0 i przygotowane poprawki

## Materiał odniesienia

Przejrzano ostatni czat, zrzut błędu wyrównania oraz rzeczywiste raporty z archiwum `Porownanie_20261016_190442_551762.zip`. Bazą kodu jest przetestowana linia V4.0 z poprawką workflow, a nie wcześniejsze wydanie 3.x.

Wynik OpenArm V1.0/V1.1 w V4.0: po 553 bryły, 522 pozycje RENAMED, 11 UNCERTAIN, 20 ADDED i 20 REMOVED. BOM miał 236 wierszy dla A i aż 553 dla B. Próba z włączonym wyrównaniem kończyła się błędem. To wskazuje na problemy z interpretacją nazw z eksportera, grupowaniem i obsługą niejednoznacznego wyrównania.

## Co zmieniono

| Problem | Poprawka w przygotowanych źródłach |
|---|---|
| Techniczne etykiety NAUO rozpoznawane jako zmiana nazwy | Importer wybiera nazwę definicji części i zapamiętuje jej pochodzenie. Różnica nazwy eksportowej nie staje się automatycznie RENAMED. Rzeczywiste jawne zmiany nazw nadal są wykrywane. |
| BOM rozbity na pojedyncze wystąpienia | Grupowanie zgodnej geometrii potwierdzone testem B‑Rep lub identycznym zapisem B‑Rep, niezależnie od etykiety eksportera. Dokładne kopie geometrii korzystają z pamięci wyników zamiast powtarzać operacje Boolean. Mapy BOM_GRUPY_A/B.json przechowują wszystkie wystąpienia, nazwy i ścieżki. |
| Błąd wyrównania przerywa całe zadanie | Używane są także unikalne bazy geometryczne. Brak jednoznacznej transformacji powoduje ostrzeżenie i porównanie oryginalnych położeń. Ostrzeżenie trafia do okna, HTML, JSON i pliku tekstowego. |
| Ryzyko zbędnej transformacji już zgodnych modeli | Potwierdzony wspólny układ pozostaje bez transformacji. Nowa transformacja wymaga co najmniej trzech baz o środkach nieleżących na jednej prostej. |
| Ujemne wartości CSV stają się tekstem | Przesunięcia i różnice objętości pozostają liczbami z polskim separatorem dziesiętnym. Ochrona przed formułami w nazwach pozostaje. |
| Raport pokazuje niepełną legendę | Legenda zawiera wszystkie siedem kategorii wraz z ich kolorami. |
| Nieudana analiza nadpisuje ostatni wynik | Odnośnik do ostatniego wyniku jest zapisywany dopiero po sukcesie. |

BOM jest **geometryczny**: dwie identyczne bryły o różnych materiałach lub numerach zamówienia mogą być razem. Nie jest to materiałowy BOM produkcyjny. Pochodzenie wystąpień pozostaje w mapach JSON. Różnice nazw pominięte jako eksportowe są widoczne w uwagach porównania.

## Wygląd

Zachowano poprawki V4.0: wspólną stylistykę ikon, rozmiar 26 px, wysokość przycisków 52 px, wyrównanie podpisów oraz wyróżnienie aktywnej strony. Sprawdzono uruchomienie i zrzuty czterech stron Qt. Nie przebudowywano od nowa już poprawionego menu.

## Kolory STEP

W Twoim dużym teście V4.0 diagnostyka wykazała **573 kolorowe etykiety, 20 224 kolorowe powierzchnie i zero powierzchni bez koloru**, a plik zawierał 21 370 rekordów stylów. Eksporter przypisuje kolory do definicji, wystąpień i powierzchni; tę poprawkę zachowano.

To potwierdza obecność kolorów po ponownym odczycie przez Open CASCADE. Nie potwierdza wyglądu w importerze ZW3D. Jeżeli ZW3D nadal wyświetla model jednolicie, potrzebny jest test na stanowisku z włączonym importem kolorów. Nie deklaruję wykonania tego testu tutaj.

## Weryfikacja

- 46 testów automatycznych: PASS. Obejmują geometrię, transformacje, niejednoznaczności, nazwy STEP, BOM, CSV, kolory powierzchni, siatkę i elementy GUI.
- Nowy test faktycznego zapisu/odczytu STEP potwierdza, że wystąpienie `NAUO528` otrzymuje nazwę swojej definicji.
- Twoje `moved_old.stp` / `moved_new.stp`: analiza z zaznaczonym wyrównaniem kończy się, raportuje 1 SAME, 1 MOVED i 1 CHANGED. Nieudane wyrównanie jest jawnie pomijane; nie znika rzeczywiste przesunięcie.
- Przetestowano wyrównanie całego syntetycznego złożenia po obrocie i przesunięciu oraz przy różnych nazwach części.
- OpenArm V1.0/V1.1: 522 SAME, 0 RENAMED, 11 UNCERTAIN, 20 ADDED, 20 REMOVED. W nazwach B nie pozostały etykiety NAUO. Wyrównanie rozpoznało już wspólny układ i nie przekształcało modelu. Przeprowadzono porównanie i raporty bez ponownego generowania dużego STEP. Test kolorów wykonano na próbkach, a wynik dużego eksportu pochodzi z Twojej V4.0.
- Końcowy BOM OpenArm: A = 82 grupy, B = 78 grup. W każdym zestawieniu suma ilości wynosi 553; mapy wystąpień zawierają po 553 unikalne indeksy, bez pominięć i podwójnego liczenia. Cały lokalny przebieg bez eksportu dużego STEP trwał około 202 s; nie jest to porównywalny pomiar szybkości z wcześniejszym testem Windows z eksportem.
- Test uruchomienia Qt: cztery strony i sześć ikon załadowane.

## Czego nie należy obiecywać

Nie należy uznawać wszystkich pozostałych par ADDED/REMOVED za błędy. Bez potwierdzonej tożsamości części zamiana ich na CHANGED byłaby zgadywaniem. UNCERTAIN oznacza konieczność weryfikacji. Masa jest obliczana z jednej zadanej gęstości, nie z rzeczywistych materiałów złożenia.

Źródła przetestowano lokalnie w Linuksie/Pythonie 3.12. Przygotowany workflow buduje na Windows x64/Pythonie 3.11, uruchamia testy oraz kontroluje gotowy EXE i załadowanie DLL. W tej sesji nie uruchomiono nowej kompilacji Windows ani nie testowano DLL wewnątrz ZW3D. Paczka nie jest gotowym EXE.

## Dostarczenie

`DSCompare_V4_1_ZRODLA.zip` — kod, testy, przykłady syntetyczne, instrukcja, analiza oraz kopia workflow.

`build-dscompare-v41.yml` — plik do `.github/workflows/`.

Instrukcja ręcznego przesłania znajduje się w `INSTRUKCJA_GITHUB.txt` wewnątrz ZIP-a. Duże modele i Twoje archiwa wyników nie są dołączone do paczki źródłowej. Poprawek V4.1 nie wysłano na GitHub.
