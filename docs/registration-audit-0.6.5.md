# Wyrównanie modeli STEP — audyt i wybór metody (0.6.5)

Bazą jest gotowy, przetestowany OneEXE 0.6.4, commit `1cae4bc4e273ca778116a33976cec360ba2ba72c`. Audyt dotyczy całej aktywnej ścieżki od importu, przez ocenę wspólnego układu, do końcowego porównania i decyzji GUI. Nie otrzymano STEP użytkownika ani końcowego komunikatu błędu; nie przypisujemy mu hipotetycznej przyczyny.

## Jak działała 0.6.4 i jakie są ograniczenia

| Element | Ustalenie | Zmiana |
| --- | --- | --- |
| `cli.process`, `similarity_gate.check_related` | Wstępne ścisłe sygnatury mogły ostrzec o niezwiązanych modelach zanim rozpoczęło się szukanie układu CAD. | Przy żądaniu wyrównania najpierw ograniczone wyszukiwanie; ostrzeżenie nie jest dowodem braku związku. |
| `compare` etap 1 i `deferred_alignment.propose_from_stage1` | Zgodność w miejscu była sprawdzana przed przesunięciem; test okresowego układu zabezpieczał przesunięcie o jeden rozstaw. To potrzebne zabezpieczenia. | Zachowane, włącznie z brakiem szukania przy pojedynczych lokalnych ruchach. |
| `deferred_alignment.propose` i `robust_translation` | Translacje bazowały na zintegrowanych środkach brył, ścisłych sygnaturach i ograniczonych próbkach powtórzeń. | Punkty odniesienia z oryginalnych wierzchołków CAD, łagodna selekcja kandydatów, rozłożona przestrzennie próbka. |
| `rigid_registration` | Obrót był osobnym algorytmem po translacjach. Klucze zaokrąglonego logarytmu objętości/pola mogły całkowicie zgubić korespondencje po reeksporcie. | Ten sam koordynator, ten sam budżet i stan; graf zgodności odległości i Kabsch, potem dopracowanie odporne na odstające pary. Dla pojedynczej bryły i współliniowych centrów również propozycje z natywnych ram CAD, każda sprawdzana B-Rep. |
| `_step_reexport_fallback`, `translation_refinement` | Kolejne odrębne próby i specjalne doprecyzowanie AABB były zależne od wcześniej wygenerowanych hipotez. | Nie są wywoływane przez aktywną ścieżkę. Zostały jako zgodność ze starszymi pomocnikami/testami. |
| `registration_search` | Kontynuacja przechowywała translacje, lecz nie cały wspólny stan transformacji sztywnych. | Pamięć punktów CAD, ukończonych obrotów i translacji, dowodów oraz nieukończonych prób. |
| `registration_gate.frame_support` | Bezpieczna kontrola 1:1 i B-Rep, ale indeks położenia wciąż korzystał ze środka masy. | Indeks oryginalnych punktów CAD po transformacji. Nadal tylko B-Rep daje pozytywny wynik. |
| `native_guard`, `native_session` | Pojedyncza operacja mogła zużyć 90 s; małe złożenia wykonywały część kontroli w procesie nadrzędnym. | Kontrole rejestracji z budżetem w procesie izolowanym niezależnie od liczby brył; deadline 60/120 s i maksymalnie 12 s na nową próbę natywną. |
| `compare` po wyrównaniu | Sprawdzenie mapy dowodów i wyszukiwanie niesprawdzonych par mogły ponownie zgubić prawidłowy wynik przez niedokładny środek masy. | Oryginalne punkty CAD w obu miejscach; niezależna kontrola niesprawdzonych brył zachowana. |
| GUI i `worker_v37` | Okno przekazuje decyzję do koordynatora; build jest zapisywany w `ENGINE_BUILD.json`. | Zachowane; opis diagnostyczny identyfikuje nowy algorytm. |
| `alignment.align_assembly` | Stary zestaw pomocników nadal istnieje dla zgodności; Tauri nie powinno go uruchamiać. | Testy zabraniają jego wywołania przez produkcyjną ścieżkę. Nie opisujemy pozostawionego kodu jako usuniętego. |

## Porównanie rozwiązań zewnętrznych

Źródła pierwotne, przeczytane podczas pracy:

* [Open3D: global registration](https://www.open3d.org/docs/release/tutorial/pipelines/global_registration.html): globalne dopasowanie RANSAC/cech, wczesne odrzucanie niezgodnych odległości, następnie dokładne lokalne dopasowanie. FPFH jest cechą chmury punktów, nie dowodem zgodności CAD.
* [CloudCompare: ICP](https://www.cloudcompare.org/doc/wiki/index.php/ICP): wymaga przybliżonego wyrównania na wejściu; obsługuje częściowe pokrycie i usuwanie dalekich punktów. Sam ICP z przypadkowego położenia nie rozwiązuje naszego problemu.
* [MIT SPARK: TEASER](https://web.mit.edu/sparklab/research/teaser/): odporne oszacowanie transformacji przy licznych błędnych korespondencjach; autorzy rozdzielają oszacowanie skali, obrotu i translacji. Gwarancje tej publikacji dotyczą opisanej tam metody i założeń, nie naszej implementacji.

Wybrano podejście globalne + odporne dopracowanie, zaadaptowane do komponentów CAD. To własna implementacja NumPy, a nie skopiowany Open3D/CloudCompare ani implementacja certyfikowanego TEASER++. Nie dokładamy dużego silnika chmur punktów ani nowej biblioteki natywnej do Windows OneEXE.

## Nowa aktywna ścieżka

1. Oryginalne wierzchołki każdej definicji CAD wyznaczają punkt odniesienia. Powtarzające się definicje są obliczane raz i przenoszone natywnym położeniem CAD. Bryły bez wierzchołków używają środka powierzchni CAD. Środek masy z opisu STEP nie steruje rejestracją.
2. Objętość, pole i opcjonalna część nazwy dopuszczają wyłącznie kandydatów. Dobór zachowuje rzadkie detale oraz rozrzut przestrzenny; jedna rodzina śrub nie wyczerpuje budżetu.
3. Najpierw sprawdzane są globalne translacje. Gdy nie dają potwierdzenia, ten sam koordynator szuka obrotu z translacją. Graf kandydatów wymaga zgodnych odległości i różnych końców par 1:1. Deterministyczny dobór trójek i Kabsch dopuszczają tylko obrót właściwy: bez odbicia i skalowania. Gdy trójki są zdegenerowane, natywne ramy bezwładności proponują dodatkowe obroty; nie zastępują dowodu geometrii.
4. Dopracowanie iteracyjne działa na punktach komponentów, z ograniczeniem deskryptorów i odrzucaniem odstających reszt na podstawie mediany/MAD. Wpływ wielu kopii jednej rodziny jest ograniczony wagami. To dopracowanie punktów komponentów, nie ICP po całych powierzchniach.
5. Ograniczona próbka B-Rep albo pełne dowody małego/słabo pokrytego układu dopiero pozwalają zaproponować wyrównanie. Niepewna próbka, timeout, podobnie dobre konkurencyjne układy albo wyczerpanie budżetu nie są pozytywnym wynikiem.
6. Pozostałe części wymagają normalnego końcowego porównania B-Rep. Pamięć dowodów obejmuje niezmienne wejścia, kolejność, tolerancję i konkretną transformację. Common i reguły wielokrotności nie są rozluźnione.

Nie istnieje jedna metoda gwarantująca jednoznaczny wynik dla wszystkich zmienionych i symetrycznych złożeń. Próbkowanie jest ograniczone; wierzchołki mogą zmienić się przy przebudowie topologii; deskryptory mogą nie dopuścić skrajnie różnie wyeksportowanych brył. Budżet dowodów nie ogranicza czasu importu ani każdego kroku wyznaczania cech. W razie braku wystarczających dowodów program ma pozostać przy decyzji użytkownika, a nie wymuszać położenie.

## Porównanie na identycznych modelach syntetycznych

Uruchomiono `portable/tests/registration_benchmark.py` osobno z kompletnym silnikiem 0.6.4 oraz 0.6.5. W obu przypadkach te same wejścia, zmieniona kolejność części, ta sama tolerancja 0,01 mm i prawdziwe dowody B-Rep. Szum reeksportu w tym teście to celowe zaburzenie metadanych środka, pola, objętości i bezwładności przy zachowanej oryginalnej geometrii. Nie są to STEP użytkownika ani ogólny benchmark wszystkich modeli CAD.

| Przypadek | 0.6.4 | 0.6.5 | Dowody nowego silnika |
| --- | --- | --- | --- |
| Translacja | poprawny układ | poprawny układ | 18/18 |
| Translacja i niedokładne metadane | brak potwierdzenia | poprawny układ | 18/18 |
| Obrót, translacja i niedokładne metadane | brak potwierdzenia | poprawny układ | 18/18 |
| Obrót 24 powtarzających się detali | brak potwierdzenia | poprawny układ | 24/24 |
| Tylko 8 zgodnych detali z 80, niedokładne metadane | brak potwierdzenia | poprawny układ, wymaga decyzji | 8/8 |

Wynik: 1/5 → 5/5 w tym konkretnym zestawie. Pełne pomiary i liczby są w `registration-benchmark-064.json` oraz `registration-benchmark-065.json`. Czasy na prostych prostopadłościanach nie prognozują czasu pracy na złożonych powierzchniach STEP. Osobne regresje obejmują jednoznaczne i niejednoznaczne położenia, odbicia, skalowanie, fałszywe deskryptory, limity, kontynuację, brak globalnego ruchu, pojedynczy lokalny ruch i końcowe porównanie części spoza próbki.

Pamięć ukończonych transformacji uwzględnia maksymalne fizyczne przemieszczenie punktów i rozmiar brył. Sama mała różnica macierzy obrotu nie wystarcza daleko od początku układu: kąt 2e-8 rad przy 1e8 mm daje około 2 mm. Pojedyncza bryła ma osobny budżet 32 hipotez, aby objąć 24 właściwe orientacje ramy; zwykły początkowy budżet złożenia to 12, rozszerzony 32. Proces natywny jest współdzielony jako transport między hipotezami, ale jego wyniki geometryczne nie są współdzielone bez osobnego, ważnego dowodu.
