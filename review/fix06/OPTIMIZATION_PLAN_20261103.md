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

## Iteracja 2026-11-04 — zintegrowany pakiet optymalizacji
- Nr 4/9: _TranslatedProofIndex dla dodatnich, źródłowo potwierdzonych
  dowodów Common/regionów. Hash lokalnych kształtów wyłącznie zawęża
  kandydatów; nadal obowiązuje pełne _reuse_common_volume.
  Cache nie przechowuje awarii, nie zmienia tolerancji ani progów.
  Statystyki: common_cache_entries / common_cache_candidates_checked,
  region_cache_entries / region_cache_candidates_checked.
- Nr 16: indeks dokładnych podpisów BRep ogranicza ponowne skanowanie
  listy definicji STEP o tej samej nazwie, orientacji, RGBA.
  Żadne przybliżone podobieństwo nie staje się dowodem.
- Nr 18/20: podgląd HTML 3D zapisuje dane siatki strumieniowo przez
  plik tymczasowy, bez trzymania całej listy binarnych payloadów
  w RAM. Zachowuje identyczny JSON/HTML dla sprawdzonego przypadku.
- Nr 13/20: Windows portable otrzymuje trwałe znaczniki faz,
  a oba workflow wykonują testy nowego cache, HTML oraz wszystkich
  wariantów indeksu przestrzennego.
- Lokalnie: testy semantyki STEP i HTML 8 PASS, testy nowej sceny
  2 PASS, testy indeksu dowodów 2 PASS; 9 PASS w regresjach
  revision_overlap z wyłączeniem jednego długotrwałego testu.
- Rzeczywisty Windows/duże złożenia, pomiar szczytu RAM,
  liczba B-Rep i rozmiar STEP po zmianach: DO WERYFIKACJI w CI.

## Audyt CI — 2026-11-04 06:51 CET (SHA 4c2ad5b)
- Windows portable/single EXE: workflow 41777579200 **success**.
- Zintegrowana kompilacja i testy rzeczywistych STEP: 41777579166 **success**, 7/7 zadań real-cad zielonych (Voron V2 shift/revision_shift, Trident shift/revision_shift, Simple Swerve revision, OpenArm review).
- Poprawiony ZIP RC9: 41777579262 **success**, 7/7 zadań CAD zielonych (V2 shift/revision/revision_shift, Trident shift/revision/revision_shift, OpenArm review); instalator Svelte5/Tauri2 zielony.
- Izolowane CAD/Swerve: 41777579176 **success**.
- Ważne: zielony job nie jest dowodem rozwiązania każdej z sześciu trudnych par Boolean; do potwierdzenia na poziomie raportów par. Nie ma jeszcze porównywalnych danych baseline dla czasu/RSS/liczby Common/Cut i rozmiaru wyeksportowanego STEP ani potwierdzenia importu do ZW3D 2019. Nie deklarować tych bramek jako PASS.
- Rozmiary *spakowanych artefaktów CI*, nie wynikowego STEP: Windows x64 195377587 B; V2 revision 149696937 B; Trident shift 100910382 B. Nie wolno mylić ich z rozmiarem STEP.
- W tej iteracji wykonano audyt i uaktualnienie ewidencji; **bez zmian algorytmu** i bez uruchamiania duplikatów buildów. Następny krok: z artefaktów CAD wydobyć per-pair Boolean outcomes, RSS, czas i rozmiar STEP; następnie wdrożyć brakujące pomiary (nr 20).

## Iteracja ręczna 2026-11-04 — poprawki i telemetria (do weryfikacji)
- NaN/Inf i ujemne Common nie są dowodem zgodności.
- Punktacja po ponowieniu B-Rep wynika z potwierdzonego podziału
  Common/Cut, a nie wstępnej objętości Common. Progi bez zmian.
- BUDGET_EXCEEDED ma odrębny kod od BOOLEAN_FAILED; kolejka retry
  nie klasyfikuje błędów na podstawie polskiego tekstu komunikatu.
- Liczone są wszystkie próby B-Rep, niepowodzenia i czas dla faz.
  Stary boolean_checks to tylko pierwotne Common, nie wszystkie operacje.
- Dodano regresje numeryczne i pomiarowe. Windows/real STEP i sześć
  trudnych par B-Rep: DO WERYFIKACJI na nowym SHA.
