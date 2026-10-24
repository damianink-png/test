# DS Compare R21 — testy skompilowanego programu na dużych złożeniach

Data: 24.10.2026. Windows Server 2022 x64, Python 3.11 użyty do zbudowania PyInstaller EXE, OCP 7.9.3.1.1.

Kompilacja i uruchomienie interfejsu: PASS. Regresje: **156 passed in 27.92s**.

Porównania uruchamiano przez `DSCompare.exe --worker compare`, czyli skompilowany moduł używany przez GUI. Python przygotowywał dane i sprawdzał wyniki; nie zastępował EXE podczas porównania. SHA256 EXE: `08068ec3a5da4d6cc2f500e2e348d368d526a82ca0bc72aeb0e932823251cec8`.

Uruchomienie i pełne logi: https://github.com/damianink-png/test/actions/runs/40105273358

## Zakończone próby

| Próba | Bryły A / B | Wynik programu | Czas EXE z importem i eksportem |
|---|---:|---|---:|
| Voron 2.4r2 — ten sam plik | 1715 / 1715 | 1715 bez zmian, brak wyrównania | 308,98 s |
| Trident R2 — ten sam plik | 1595 / 1595 | 1595 bez zmian, brak wyrównania | 468,59 s |
| Voron 2.4r2 — autentyczne rewizje | 1707 / 1715 | 1682 bez zmian, 29 nowych, 21 usuniętych, 4 przestawione | 509,27 s |
| Trident R2 — autentyczne rewizje | 1595 / 1595 | 1594 bez zmian, 1 nowy, 1 usunięty | 647,28 s |

Są to dwa rzeczywiste projekty złożeń, łącznie cztery pliki wersji źródłowych, każdy powyżej 600 brył. Nie tworzono sztucznego dużego złożenia przez powielanie małego modelu.

W testach tego samego pliku działa szybka ścieżka rozpoznania identycznych danych; nie są one pomiarem pełnego dopasowania dwóch niezależnych eksportów STEP. W obu rzeczywistych parach rewizji program również pozostał w oryginalnych współrzędnych, bez pytania o wyrównanie.

Dla autentycznych rewizji nie istnieje tutaj niezależna, ręcznie zweryfikowana lista oczekiwanych klas. Podane liczby są wynikiem programu, a PASS oznacza ukończenie analizy, kompletność przypisań i zapis wyjść, nie dowód poprawności każdej klasyfikacji.

## Spójność wyjść

Dla czterech zakończonych analiz:
- każda bryła A i B występuje dokładnie raz w przypisaniach wynikowych;
- kolorowy STEP został zapisany bez zgłoszonego błędu;
- weryfikacja STEP była szybka, strukturalna — bez ponownego importu całego wyjścia;
- HTML zawiera wszystkie zadeklarowane obiekty siatki, liczba pominiętych wynosi 0;
- pliki zawierają kod drzewa złożenia; w tym zestawie testów nie wykonywano interakcyjnych kliknięć w przeglądarce;
- pełny BOM był wyłączony. Czasy nie obejmują jego grupowania.

## Wydajność

| Para rewizji | Import A+B | Dopasowanie i klasyfikacja | STEP i raporty |
|---|---:|---:|---:|
| Voron | 275,88 s | 51,36 s | 177,30 s |
| Trident | 467,06 s | 17,28 s | 160,00 s |

Podglądy zawierają około 2,1–2,3 mln trójkątów. Zadany cel 300 tys. nie jest twardym limitem, ponieważ program zachowuje wszystkie bryły. Brak pominiętych elementów nie oznacza, że tak duży HTML będzie płynny na każdym komputerze. Priorytety dalszej optymalizacji: import, współdzielenie siatek powtarzalnych części, ograniczenie szczegółowości bez usuwania wystąpień.

## Odrzucony model

Voron Switchwire: przygotowujący test import zgłosił bryłę o zerowej/ujemnej objętości: `(Unsaved)/Gantry:1/X Axis Assembly:1/CW2_Assembly:1/CW2_Printed:1/Main_Body:1/Main_Body:1`. Próby zatrzymały się **przed uruchomieniem porównania EXE**. Nie zaliczono ich jako udanych testów dużego złożenia. Sam komunikat nie rozstrzyga, czy problem leży w źródłowym STEP, czy w obsłudze jego geometrii przez importer; wymaga osobnej diagnostyki.

## Pochodzenie modeli

Pliki pochodzą z publicznych repozytoriów VoronDesign. Zachowano numery commitów i sumy plików w wynikach JSON; modele nie zostały dołączone do programu.

- Voron-2, `CAD/Voron_2.4r2_Assembly_STEP.zip`: starszy `e47cc70edbdb0c36916885b54a5e1f30f52a717a` (integracja Stealthburnera), nowszy `e64c83bcb84d41c0324e104a1c911879174d08aa` (poprawki mocowania i łańcucha).
- Voron-Trident, `CAD/trident_assembly.step.zip`: starszy `9d9223311f2b0fce72484023d6a755e13a733319` (wydanie R2), nowszy `1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a` (poprawki po wydaniu).
- Voron-Switchwire, `CAD/Switchwire_Assembly_v1_STEP.zip`, ref `92cc013ca2af94e6c09950dbe05c0973ee49aa00`.

Kontrolowane przesunięcia są kopiami przygotowanymi do testu, nie autentycznymi rewizjami autorów. Wektor przesunięcia B: (+1275, −395, +210) mm. Oczekiwany wynik po prawidłowym nałożeniu: wszystkie bryły bez zmian.

## Przesunięcie całego Vorona — FAIL / timeout

EXE przekroczył limit 2400 s (40 min). Nie powstał kompletny wynik, dlatego nie można potwierdzić oczekiwanych 1715 brył bez zmian.

Program zaproponował poprawny wektor B→A `[-1275, 395, -210]` mm, metodą `comparison_translation_consensus`, z 349 potwierdzonymi głosami. Test zatwierdził tę propozycję. Ostatni komunikat: `Etap zgodności: 975/1715; B-Rep: 804; pamięć: 87; 815.7s` — czas w tym komunikacie dotyczy etapu, a nie całego uruchomienia.

To potwierdzony problem wydajności analizy po wyrównaniu. Nie jest to dowód błędnego wektora ani błędnej końcowej klasyfikacji — końcowej klasyfikacji nie uzyskano. Kod głównej ścieżki rejestracji zwraca liczbę potwierdzeń, lecz nie przekazuje wszystkich par do ponownego użycia w dopasowaniu. Warto rozszerzyć przekazywanie dowodów, tak jak już robi to alternatywna ścieżka `full_pair_map`, zachowując tolerancję i geometryczne kryteria zgodności. Taka zmiana nie została jeszcze wdrożona ani zweryfikowana w tym EXE.

## Przesunięcie całego Tridenta — FAIL / timeout

EXE przekroczył limit 2400 s (40 min). Ostatnie komunikaty: `Etap 1: 0/1595 zgodnych w miejscu; sprawdzam globalne przesunięcie.` oraz `Wynik porównania wskazuje wspólne przesunięcie. Weryfikacja położenia B-Rep…`. Nie powstało jeszcze pytanie o akceptację ani końcowy raport.

W przeciwieństwie do Vorona, ograniczenie czasu wystąpiło już podczas geometrycznej weryfikacji hipotez przesunięcia. Obecny zapis postępu nie identyfikuje konkretnej pary ani pojedynczej operacji natywnej, dlatego dokładne wskazanie kosztownej bryły wymaga dodatkowego profilowania.

## Ocena końcowa

**Nie wszystkie testy przeszły.** Cztery analizy EXE ukończono poprawnie, dwie analizy przesunięcia przerwano po limicie 40 min, a dwie próby Switchwire odpadły na przygotowującym imporcie, przed porównaniem EXE. Kompilacja oraz 156 regresji przeszły.

Ta seria ujawniła ograniczenia niewidoczne na mniejszych testach. R21 nie została w tym zadaniu zmieniona w celu ukrycia tych błędów ani oznaczona jako w pełni zweryfikowana dla dużych przesuniętych złożeń. Następna poprawka powinna objąć profilowanie i ograniczenie powtarzanych dowodów B-Rep przy rejestracji oraz przekazywanie już potwierdzonych par do dalszej analizy, bez osłabiania kryteriów zgodności. Niezależnie trzeba zdiagnozować import Switchwire.

Skompilowany testowany program (około 195 MB): https://github.com/damianink-png/test/actions/runs/40105273358/artifacts/12564094339
