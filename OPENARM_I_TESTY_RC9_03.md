# RC9 / OpenArm 03

## Wynik analizy danych użytkownika

Sprawdzono oba pliki OpenArm v1.0/v1.1: po 553 bryły. Są identyczne z publicznymi plikami projektu OpenArm (szczegóły i licencja w tests/fixtures/openarm_source_tolerance).

Odtworzony błąd dotyczy A[133] J3-J4_Cover v2:1#1 i B[131] J3-J4_Cover_2.step#1. Oryginalna bryła A ma nieprawidłową orientację ściany 18. Zapisane tolerancje topologii wynoszą do 0.170017583 mm dla wierzchołków i 0.077489470 mm dla krawędzi, przy budżecie naprawy 0.01 mm. To wartości tolerancji wewnętrznych, nie pomiar błędu położenia. Próby naprawy nie potwierdziły poprawnej bryły w tym budżecie: ShapeFix przywraca większe tolerancje. Nie zwiększono limitu ani nie uznano błędu za brak zmian.

Domyślna analiza pozostaje ścisła. GUI oferuje jawny wybór: „Utwórz raport częściowy” albo domyślne „Przerwij”. Dopiero po wyborze użytkownika zapisuje dostępne wyniki: 522 SAME oraz 62 UNCERTAIN (31 pozycji A i 31 B). Nie tworzy zgadywanych par ani fałszywych różnic materiału. Raport, PODSUMOWANIE.json i GUI sygnalizują niepełną analizę; powstaje ANALIZA_NIEKOMPLETNA.txt. Importowane modele są dostępne w STEP, BOM i podglądzie 3D.

Rzeczywisty przebieg częściowy: 191.4 s, 584 wystąpienia, 539832 trójkąty, 0 pominiętych siatek. Audyt kompletności danych i przeglądarka WebGL przeszły; konsola bez błędów JavaScript. To raport częściowy, nie potwierdzenie pełnej analizy różnic materiałowych.

## Nowe błędy GitHub

Uruchomienie 41084199652: Windows build i 318 testów PASS; wszystkie trzy scenariusze Trident oraz rewizje V2 bez przesunięcia PASS. Dwa scenariusze V2 z przesunięciem ujawniły dodatkowy wariant mikrocylindra z punktowymi szwami. Poprawka sprawdza wszystkie punkty i cały zakres powierzchni, zachowując oryginalny budżet tolerancji. Nie odrzuca rzeczywistych krzywych jako punktów. Pełna wadliwa para z artefaktu została odtworzona i przechodzi izolowaną operację natywną; dodano utrwaloną regresję i testy negatywne.

Nowy workflow obejmuje sześć niezmienionych ścisłych scenariuszy V2/Trident oraz osobny scenariusz OpenArm z jawną zgodą na raport częściowy. Ten ostatni test wymaga statusu niepełnego i zachowania wszystkich 553+553 indeksów; nie może zaliczyć takiego wyniku jako pełnego porównania.

## Walidacja tej wersji

Lokalnie: 326 zebranych testów, 325 PASS i 1 pominięty test Windows Job Object na Linux; dodatkowo 7 kontroli oryginalnej granicy geometrycznej, audyt GUI, rzeczywistego raportu OpenArm i WebGL PASS. Trzy testy raportu częściowego powtórzono po ostatniej zmianie komunikatu: PASS. Nowy pełny przebieg Windows/GitHub wymaga niezależnego zakończenia; wyników starszego EXE nie należy przypisywać tej wersji.

Instalować kompletny pakiet źródeł lub EXE z tego samego commita. Historyczne nakładki UI nie instalują tej wersji. Numer kompilacji „RC9 / OpenArm 03” jest widoczny w oknie informacji.
