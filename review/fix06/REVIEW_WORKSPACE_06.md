# Desktop 0.5.0 / Review 06

Nowy przegląd wyników łączy listę części, podgląd i szczegóły. Wybór działa w obu kierunkach i zachowuje oryginalne identyfikatory po filtrowaniu i stronicowaniu.

- Diagnostyka pokazuje przyczynę niepotwierdzonego wyniku. Osobno zaznacza rzeczywiste operandy operacji zakończonej błędem. Nie przypisuje uszkodzonej topologii wszystkim niepewnym częściom.
- Wyrównanie całego złożenia B→A jest oddzielone od ruchu części A→B. Podgląd potrafi odwrócić zatwierdzoną transformację, uwzględniając obrót, przesunięcie i centrowanie siatki.
- Widok A/B korzysta ze wspólnej kamery. Pokazuje rzeczywistą geometrię obu rewizji, w tym materiał wspólny i usunięty po stronie A zmienionego detalu. Nakładka nie dubluje niezmienionego materiału A.
- Przekroje X/Y/Z są wizualnym obcięciem siatki, bez zamykania powierzchni cięcia. Nie zmieniają STEP ani wyników pomiarów.
- Zdarzenia postępu zawierają czas, etap i jawne liczniki. Brak komunikatu nie jest diagnozą zawieszenia; interfejs pokazuje czas ostatniej wiadomości i stan procesu. Nie ma wymyślonego procentu całej analizy.
- Raport offline ma podsumowanie pełności, diagnostykę, parametry, identyfikację źródeł SHA-256 oraz bezpośrednie odnośniki do części w 3D. Drukowanie do PDF zachowuje aktualny zakres filtrów.
- Własna paleta jest przenoszona na odpowiednie kolory rewizji i fragmentów materiału. Statusy mają również opisy tekstowe.
- Interfejs zachowuje motyw jasny/ciemny, okno autora z oryginalnym logo i animacją oraz układ kompaktowy. Osadzony podgląd chowa dodatkowe drzewo, dostępne nadal w samodzielnym HTML.

## Sprawdzenie

Regresje geometrii uruchamia `python ci/run_manual_regressions.py`; nowe kontrole są w `tests/test_review_workspace.py`. Audyt sceny wymaga teraz również pełnego zestawu elementów A w trybie obu rewizji — nie poluzowuje wymagań kompletności.

`npm run check`, `npm test`, `npm run build` w `desktop`; `cargo test --manifest-path desktop/src-tauri/Cargo.toml --lib`.

Test przeglądarki wymaga Pythona z OCP/numpy i Playwright/Chromium, uruchomionego `npm run dev -- --port 8766`:

```
python desktop/tests/make_review_fixture.py
python desktop/tests/browser_review.py
```

To test prawdziwego WebGL i interfejsu Svelte z jawną atrapą IPC Tauri. Osobno `desktop/src-tauri/examples/engine_smoke.rs` sprawdza rzeczywisty proces Rust→Python/OCCT i kompletne wyniki. `DSCOMPARE_ENGINE_COMMAND` jest tablicą JSON polecenia silnika; przykład przyjmuje ścieżki A.step, B.step i folder wyników.

Pełny nowy instalator Windows powstaje w głównym workflow `rc9-corrected-real-cad.yml`, z tego samego kompletnego ZIP źródeł. Lokalne testy nie zastępują jego budowania i testów dużych złożeń. Test OpenArm nadal sprawdza jawnie częściowy raport; nie oznacza potwierdzenia wszystkich różnic materiału.

Tolerancja CAD i zasady dowodzenia zgodności nie zostały zwiększone. Dotychczasowe dowody Native05.1 pozostają obowiązujące. Przyczyna wcześniejszego sporadycznego naruszenia pamięci natywnej nie została potwierdzona.

## Optymalizacja

Zakończony run 41245568510: V2 `revision_shift` 1705,65 s analizy, w tym import A+B 296,62 s, sprawdzanie/dopasowanie geometrii 1184,65 s i zapis wyników 205,60 s. W dzienniku 1566 odizolowanych dowodów re-eksportu zajęło łącznie 1136,08 s. Trident bez globalnego przesunięcia: 719,13 s, w tym importy 506,58 s, dopasowanie 30,52 s i zapis 181,66 s. To różne dominujące koszty; nie należy utożsamiać kolejki CI z czasem samego silnika.

Dodano ponowne wykorzystanie ukończonego dowodu położenia tylko dla dwóch par identycznych lokalnych zapisów B-Rep, zatwierdzonych przez rejestr geometrii, oraz zgodnej względnej transformacji. Tolerancja i kontrola całych powierzchni/krzywych pozostają te same. Niepowodzenia nie tworzą wpisu dodatniego i pozostają ponawialne.

Pomiar kontrolny: 24 niezależnie skopiowane pary rzeczywistych złączek Molex oraz 600 części referencyjnych, 624 dopasowania w obu wariantach. Przed optymalizacją 21,27 s, po 2,16 s; 23 ponowne użycia pozytywnego dowodu. Jest to wynik tego zestawu, a nie deklarowane przyspieszenie całego V2.

Weryfikacja struktury i diagnostyka STEP używają mapowania pliku tylko do odczytu. Nie powstaje pełna prywatna kopia dużego STEP. Kontrola syntetycznego pliku 128 MiB dała te same wszystkie liczniki: szczyt alokacji Pythona około 128 MiB przed zmianą i 13 KiB po zmianie, przy podobnym czasie 2,75 / 2,72 s. To pomiar sterty Pythona, nie całej pamięci procesu ani obietnica określonej oszczędności RSS. Scena HTML jest zapisywana fragmentami, bez kilku jednoczesnych kopii całego JSON/HTML.

Harness rewizji bez przesunięcia nie dekoduje ponownie obu dużych źródeł przed właściwym zimnym testem EXE. Zamiast tego wymaga pełnej zgodności SHA-256 z przypiętymi źródłami i dokładnej oczekiwanej liczby wystąpień: V2 1707/1715, Trident 1595/1595. Liczby zostały niezależnie potwierdzone przed tą zmianą. Audyty każdej pozycji, BOM, STEP i podglądu pozostają wymagane. Zewnętrzne pliki o innym skrócie nie przejdą tej kontroli.

Workflow nadal uruchamia wszystkie scenariusze. Limit macierzy podniesiono z 3 do 7 niezależnych runnerów; faktyczną równoległość ogranicza również konto GitHub. Nowszy przebieg tego samego workflow/PR zastępuje nieukończony starszy przebieg.

Historyczny test `test_v46_r1_export.py::test_native_repeat_reuses_geometry_without_losing_occurrences` zakłada jedną wspólną definicję STEP dla 36 wystąpień. Ten test jest poza istniejącą bramką regresji i nie odpowiada obecnemu celowemu eksportowi oddzielnych produktów, potrzebnemu dla nazw części w CAD. Sprawdzono bezpośrednio niezmieniony kod Native05.1: również tworzy 36 definicji/36 wystąpień. Optymalizacja zachowuje tę politykę eksportu; nie usuwa produktów, aby uzyskać mniejszy STEP.
