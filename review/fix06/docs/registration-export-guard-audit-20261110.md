# Audyt wyrównania DS Compare, 2026-11-10

Źródła: dwie paczki wyników od użytkownika (380/554 oraz 380/560 brył),
aktualny silnik CAD na gałęzi fix/dscompare-0613-material-z-20261109,
Open3D RANSAC/ICP i CloudCompare Align/ICP.

## Fakt z logów
- Test przesunięty: 380 A / 554 B, B→A ~(-130,-280,-410) mm,
  40/48 pełnych próbek B-Rep; program zaakceptował transformację po potwierdzeniu.
- Test w oryginalnych współrzędnych: 380 A / 560 B, brak wyrównania,
  232 SAME, 18 CHANGED, 7 MOVED, 0 UNCERTAIN.
- Liczba brył i masa B różnią się między eksportami, więc to nie jest
  czysta transformacja TEGO SAMEGO wejściowego B-Rep. Wniosek o winie samego
  wyrównania nie wynika z tych danych.

## Audyt zabezpieczeń
- Stage1 sprawdza oryginalny układ, a gdy dotychczasowe dopasowanie
  jest bardzo wysokie (>=90%), nadal sprawdza możliwość przesunięcia
  o okres jednej rodziny powtórzeń.
- RANSAC-like CAD-landmark consensus i trimmed ICP służą tylko do
  propozycji położenia. Faktyczne potwierdzenia pochodzą z B-Rep.
- 60/120 s i 12/24 s to odrębne limity wyszukiwania/pojedynczych
  wywołań. Nie zastępować ich jednym limitem na całą analizę.
- Raport rozdziela części zweryfikowane od UNCERTAIN. Użycie dowodów
  z wcześniejszych transformacji jest zabronione.
- Nie uruchamia się już _step_reexport_fallback; wciąż istnieje w
  deferred_alignment.py jako historyczna ścieżka. Nie wywoływać jej
  automatycznie po błędzie innego eksportu, bo to dubluje poszukiwania.

## Wprowadzone poprawki
1. Przy przygotowaniu hipotezy zachować źródłowe ID definicji XCAF,
   tracone dotąd przez dataclasses.replace.
2. Zachować pełny skrót znormalizowanego B-Rep i lokalną bazę wyłącznie
   jeśli po przemieszczeniu TopoDS pozostaje IsPartner.
3. Wśród kandydatów wystąpień o podobnym położeniu dać pierwszeństwo
   parze o potwierdzonym *pełnym* skrócie lokalnego B-Rep. Sama
   kolejność NIE nadaje statusu SAME: B-Rep w świecie wciąż obowiązuje.
4. Zachować wszystkie dotychczasowe zabezpieczenia weryfikacji
   transformacji i ostatni pełny etap porównania.

## Nieweryfikowalne bez oryginalnych STEP
Odtworzenie z samych raportów zmienionych twarzy, topologii i sześciu
brakujących SOLID. Logi dowodzą różnicy eksportu, nie jej przyczyny.
