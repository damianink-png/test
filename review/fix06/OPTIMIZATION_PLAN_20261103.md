# DS Compare RC9 — plan 20 optymalizacji i bramki testowe

Stan: 2026-11-03. Gałąź: `codex/rc9-palette-20261102`.
**Zasada:** „w kodzie” nie oznacza „PASS na rzeczywistych złożeniach”.
Weryfikować dokładną wersję SHA dla EXE, regresji i modeli; nie raportować
sukcesu nieuruchomionych, przerwanych lub nieukończonych testów.

## Etap I — dopasowanie i wydajność
| Nr | Zadanie | Stan 2026-11-03 |
| --- | --- | --- |
| 1 | Jeden katalog dokładnych definicji i wystąpień | Częściowo — istnieją lokalne rejestry; wymagana integracja |
| 2 | Wielopoziomowe sygnatury i dowód geometryczny | Częściowo — sygnatury to filtr, nie dowód |
| 3 | Indeks przestrzenny dla kandydatów rewizji | Wdrożony w R17 w `revision_overlap.py`; oczekuje CI |
| 4 | Wspólny cache pozytywnych dowodów dla etapów | Częściowo — obecne lokalne cache; wciąż rozproszone |
| 5 | Definicje i liczności przed wystąpieniami | Częściowo — ochrona powtarzających się detali; zintegrować |
| 6 | Tanie odrzucanie kandydatów przed Common/Cut | Częściowo — bbox/objętość/nazwy; zmierzyć trafność |

## Etap II — B-Rep i odzyskiwanie
| Nr | Zadanie | Stan 2026-11-03 |
| --- | --- | --- |
| 7 | Preflight topologii dla trudnych par, cache diagnoz | Częściowo |
| 8 | Bezpieczna ShapeFix na kopii z konserwacją materiału | Do wdrożenia i rygorystycznego testu |
| 9 | Jedno źródło Common/Cut z walidacją regionów | Częściowo — ścieżki fallback już istnieją |
| 10 | Dynamiczne per-pair timeout i fair retry | Częściowo — budżety globalne/post-pass; brak pełnej polityki |
| 11 | Pula izolowanych operacji natywnych i recovery | Częściowo — izolowane B-Rep i timeout |
| 12 | Rozdzielenie tolerancji re-eksportu od progu zmian | Częściowo — wymaga matrycy testowej |
| 13 | Kody TIMEOUT/INVALID_BREP/BOOLEAN_FAILED/BUDGET | Do pełnego wdrożenia |

## Etap III — wyrównanie
| Nr | Zadanie | Stan 2026-11-03 |
| --- | --- | --- |
| 14 | Szybki dowód braku przesunięcia | Częściowo — istnieją filtry i fast path |
| 15 | Wspólne, bezpieczne pozytywne dowody B-Rep | Częściowo — FrameProofCache, rozwinąć |

## Etap IV — eksport, raporty, wydajność
| Nr | Zadanie | Stan 2026-11-03 |
| --- | --- | --- |
| 16 | Zweryfikowane tryby kompaktowy i płaski STEP | Częściowo — oba tryby istnieją, kompatybilność ZW3D do sprawdzenia |
| 17 | Oszczędne style kolorów/przezroczystości | Diagnostyka istnieje; zoptymalizowany wariant do testów |
| 18 | Instancjonowanie siatek WebGL / HTML | Częściowo — SharedMesh; sprawdzić serializację |
| 19 | Jeden zweryfikowany wynik dla STEP/HTML/CSV/masy | Częściowo — ujednolicić zachowanie |
| 20 | Baseline czasu, RSS, Common/Cut, STEP, HTML, regresje | Częściowo — rozszerzać i zachować porównania SHA |

## Bramka akceptacji kolejnych zmian
1. Unit: testy indeksu przedziałowego porównane brute force, uwzględniające
   granice tolerancji, skrajne położenia i 2500 brył. Brak zgubionych kandydatów.
2. Geometry: te same rekordy klasyfikacji co przed zmianą dla zestawów
   Voron V2, Trident, OpenArm i Simple Swerve; bez zgadywania UNKNOWN.
3. Native: kontrola sześciu trudnych par B-Rep; zachować pełne logi i
   dowody objętości Common + Added + Removed.
4. Alignment: próby przesunięć nie mogą uznawać dopasowania z 2 baz za
   dowód przesunięcia całego złożenia.
5. Output: import STEP, kolory, nazwy i układ w ZW3D 2019; porównać tryb
   płaski i kompaktowy, nie zmieniać domyślnego formatu bez potwierdzenia.
6. Benchmark: podać zmianę czasu importu, dopasowania, B-Rep, STEP, HTML;
   szczyt RAM; liczbę wywołań Boolean; wynikowy rozmiar STEP.
7. Delivery: pełny Windows portable + single EXE, uruchomienie programu,
   testy na realnych STEP, podgląd HTML 3D, linki do konkretnych GitHub Actions.
8. Jeśli brak dowodów lub test nie skończył się: status „DO WERYFIKACJI”,
   nie „PASS”. Nie ukrywać nierozstrzygniętych par.

## Iteracja 2026-11-03 — optymalizacja nr 3
W `revision_overlap.py` zastąpiono powtarzane skanowanie wszystkich
wcześniejszych przedziałów X konserwatywnym indeksem maksymalnych końców
X. Dodano filtr rozłącznych zakresów Y/Z przed testami objętości.
Nie zmieniono progów IoU, Common/Cut ani reguł doboru par.
Testy w `test_revision_overlap_policy.py` sprawdzają zgodność z brute
force, granice tolerancji i duże rzadkie złożenie.
**Wynik realnego CI: do sprawdzenia na ostatnim SHA.**
