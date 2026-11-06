# DS Compare Portable 0.6.10

Dwa pakiety Windows x64 nie wymagają instalatora ani uprawnień administratora:

- **Portable ZIP**: rozpakuj cały folder i uruchom `DSCompare.exe`. Folder `app` pozostaje obok programu.
- **Jeden EXE w ZIP**: rozpakuj i uruchom `DSCompare.exe`; można przenosić sam ten plik. Pierwszy start przygotowuje pliki w `%LOCALAPPDATA%\DSCompare\portable`. Kolejne sprawdzają i ponownie wykorzystują kopię. Nie jest to instalacja w systemie.

Oba zawierają natywny interfejs Svelte/Tauri, kompletny zamrożony silnik Python/OCCT oraz oficjalny Microsoft WebView2 Fixed Runtime. Nie trzeba instalować Pythona ani osobnego WebView2. Ze względu na dołączoną przeglądarkę pakiet jest większy od poprzedniego instalatora.

Ekran startowy to lekkie okno Win32, działające przed uruchomieniem interfejsu. Animowane kostki A/B pokazują etapy przygotowania, postęp rozpakowywania i kontroli plików. Start interfejsu ma osobne potwierdzenie gotowości; animacja nie zastępuje faktycznego sprawdzania. Ograniczenie animacji w ustawieniach Windows jest respektowane.

Pliki są sprawdzane według manifestu SHA-256. Równoległe starty współdzielą blokadę przygotowania. Przerwane rozpakowanie nie jest publikowane jako gotowe; uszkodzona kopia jest zastępowana nową generacją bez nadpisywania używanego programu. Jednoplikowy EXE zawiera skompresowane dane jako końcową sekcję pliku, a nie pobiera ich z Internetu.

Wyniki i ustawienia są zapisywane w normalnych folderach użytkownika, tak jak wcześniej. Przeglądarka wersji przenośnej ma osobny profil w `%LOCALAPPDATA%\DSCompare\portable-webview`. Źródła bazowe silnika pochodzą z run **41291652234**, commit **22b9e73746e8721e146b10d3e3656df67e77956c**. Po sprawdzeniu SHA-256 nakładane są aktualne poprawki z `review/fix06`; silnik jest następnie ponownie testowany i kompilowany razem z bieżącą aplikacją. Suma SHA-256 dołączonego silnika jest sprawdzana przed pakowaniem. Zmiany 0.6.0 obejmują uproszczenie obsługi: dopasowanie okna do obszaru ekranu, natywne przeciąganie plików STEP, osobny widok wyników i 3D, czytelny wynik masy, nowe porównanie oraz osobne listy BOM A/B w HTML. CSV jest opcjonalny.

Pakiet WebView2 i jego skrót są przypięte w `webview-source.json`, pobrane z oficjalnej strony Microsoft. Prawa odczytu wymagane przez AppContainer w Windows 10 są ustawiane tylko dla dołączonego folderu WebView2 zgodnie z dokumentacją Microsoft. Nie są zmieniane ustawienia przeglądarki systemowej ani rejestr instalacji.


Wersja 0.6.2 dopuszcza automatyczny Common dla powtarzających się detali, jeżeli ich pełne liczby wystąpień w A i B są takie same i nazwy wskazują tę samą rodzinę po pominięciu oddzielonej rewizji. Uwzględniane są m.in. `12345_REV_A` / `12345_REV_B`, `12345_A` / `12345_B` oraz `12345_01` / `12345_02`. Nie są dopasowywane dowolne krótkie fragmenty ani różne numery rysunków (`PART_100` / `PART_200`). Liczone są całe modele, również części już dopasowane. Same nazwy i liczby nie dowodzą zmiany materiału: każda dopuszczona para przechodzi natywne Common/Cut. Nazwy ani podobne wymiary nie dowodzą powtórzenia: grupowanie wymaga natywnej, dokładnej lub zweryfikowanej geometrii B-Rep. Niedopuszczone lub niepotwierdzone pary pozostają jako osobne stare usunięte i nowe dodane; rzeczywiste błędy geometrii pozostają do sprawdzenia. Poprawiono pamięć tożsamości obiektów oraz deterministyczne szukanie przesunięć. Obecny interfejs Tauri, podgląd WebGL, raporty masy, paleta i dołączony WebView2 są zachowane.


## Wydania 0.6.5 i 0.6.6

Bazą jest wydana 0.6.4, commit `1cae4bc4e273ca778116a33976cec360ba2ba72c`. Przebudowano aktywną ścieżkę wyrównania: globalny konsensus oryginalnych punktów CAD, graf zgodnych odległości, obrót i translacja bez skalowania, następnie dopracowanie z odrzucaniem odstających par. W szczególnych przypadkach pojedynczej bryły lub współliniowych komponentów natywne ramy bezwładności służą wyłącznie generowaniu propozycji. Powtarzające się definicje CAD są odczytywane raz. Nazwy i przybliżone deskryptory nie dowodzą zgodności.

Położenie nadal musi przejść B-Rep przy niezmienionej tolerancji. Dla dużych złożeń sprawdzana jest ograniczona próbka, a pozostałe części kontroluje końcowe porównanie. Oba etapy wyszukują po oryginalnych punktach CAD, a nie niedokładnych środkach masy. „Szukaj dokładniej” kontynuuje ten sam stan obrotów i przesunięć bez powtarzania ukończonych hipotez. Timeout, sprzeczne dowody i podobnie dobre konkurencyjne położenia nie są pozytywnym wynikiem.

Reguły Common z jednakową liczbą powtórzeń i zgodną rodziną nazwy pozostają zachowane. W folderze zadania `ENGINE_BUILD.json` identyfikuje rzeczywisty silnik i commit. Diagnostyka zawiera 11 prób, w tym końcową kontrolę 80/80 brył z niedokładnymi środkami oraz obrót i przesunięcie po reeksporcie. Audyt, źródła wyboru metody i odtwarzalne porównanie z 0.6.4 znajdują się w `docs/registration-audit-0.6.5.md` w repozytorium.

W 0.6.6 `czesc1_afm0`, `czesc1_afm2` oraz `czesc1_xyz2` mają wspólną bazę `czesc1`. Oddzielony dopisek z literami i krótkim numerem rewizji nie wymaga identycznego kodu literowego. W nazwach wieloczłonowych zachowane są wcześniejsze pola identyfikujące detal, np. `12345_LEWY_afm0` i `12345_PRAWY_afm2` pozostają różne. Różne bazy, liczby wystąpień i numery rysunków nadal nie dopuszczają rodziny do Common. Nazwy jedynie dopuszczają próbę; materiał musi przejść natywne Common/Cut.


## Wydanie 0.6.7

Bazą jest 0.6.6. Przygotowanie hipotezy obrotu nie przelicza ponownie własności masowych wszystkich brył. Dla prawidłowych brył o innym podziale ścian po eksporcie dodano natywny dowód przez dwie puste różnice brył. Punkty CAD i środki masy służą jako niezależne wskazówki wyszukiwania; każda zgodność nadal wymaga dowodu geometrii.

Gdy całe detale zostały zmienione, program może zaproponować położenie na podstawie zachowanych oryginalnych powierzchni z dokładną kontrolą ich obrysów. Taka propozycja wymaga zatwierdzenia, również po „Szukaj dokładniej”. Okno pokazuje przesunięcie, obrót i liczbę potwierdzonych powierzchni. Dowód położenia nie oznacza zgodności całych detali: po zatwierdzeniu następuje niezależne porównanie materiału. Zachowano reguły Common z 0.6.6.

Dodano testy rzeczywistych zapisów STEP: zmieniona i przesunięta rewizja (8 zmienionych detali), identyczne przesunięte bryły z podziałem ścian (8 bez zmian) oraz dotychczasowy obrót i przesunięcie (18 bez zmian). Szczegóły i ograniczenia opisano w `docs/registration-audit-0.6.7.md`. Bez oryginalnych plików użytkownika nie potwierdzono przyczyny zgłoszonego błędu.


## Wydanie 0.6.8

Wykrywanie translacji rozpoczyna się od największych detali o unikatowym zestawie objętości, pola powierzchni i głównych centralnych momentów bezwładności po obu stronach. Nazwa nie jest warunkiem dopasowania. Te własności jedynie wybierają kandydatów: wektor jest dopuszczany dopiero po rzeczywistym dowodzie geometrii całego detalu B-Rep. Następnie program sprawdza pozostałe złożenie w tym położeniu. Pojedynczy lokalnie przesunięty detal nie potwierdza globalnego ruchu.

Detale z niejednoznacznymi deskryptorami pozostają dla ogólnego wyszukiwania. Nieukończony dowód geometrii nie staje się zgodnością. W postępie i diagnostyce widać kolejność unikatowych detali, wyniki dowodów oraz wyznaczony wektor. Common pozostaje według zasad 0.6.6. Szczegóły: `docs/registration-audit-0.6.8.md`.


## Wydanie 0.6.9

Po klasyfikacji rewizji przygotowanie Common nie przelicza już niezwiązanych rodzin części bez zmian. Dla części uczestniczących w Common nadal liczone są wszystkie zgodne geometrycznie wystąpienia w całych rewizjach, także już dopasowane. Powtórne sprawdzenie tej samej pary korzysta również z ukończonych ujemnych wyników zgodności przy tej samej tolerancji; awaria lub timeout nie stają się wynikiem negatywnym ani dowodem zgodności. Postęp od razu przechodzi do „Weryfikacji materiału” i pokazuje przygotowanie/liczenie wystąpień. Osobne czasy klasyfikacji i dopasowania materiału zapisuje `CZASY_ANALIZY.json`. Reguły Common oraz wykrywanie przesunięcia z 0.6.8 pozostają.


## Wydanie 0.6.10 — kompilacja OneEXE

Gałąź `build/dscompare-0.6.10-20261106` została utworzona ze źródeł `0.6.9` (commit `a29010a1fb76332a72f7b1e2bbd1dd68632f50d7`). Wersja 0.6.10 zachowuje ich moduły i algorytmy CAD; zmieniono identyfikatory wersji aplikacji Tauri, launchera, manifestu oraz artefaktów GitHub Actions. Jest to nowe wydanie techniczne tego kodu, bez twierdzenia o dodatkowych naprawach wyrównywania.
