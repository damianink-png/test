# DS Compare Portable 0.6.4

Dwa pakiety Windows x64 nie wymagają instalatora ani uprawnień administratora:

- **Portable ZIP**: rozpakuj cały folder i uruchom `DSCompare.exe`. Folder `app` pozostaje obok programu.
- **Jeden EXE w ZIP**: rozpakuj i uruchom `DSCompare.exe`; można przenosić sam ten plik. Pierwszy start przygotowuje pliki w `%LOCALAPPDATA%\DSCompare\portable`. Kolejne sprawdzają i ponownie wykorzystują kopię. Nie jest to instalacja w systemie.

Oba zawierają natywny interfejs Svelte/Tauri, kompletny zamrożony silnik Python/OCCT oraz oficjalny Microsoft WebView2 Fixed Runtime. Nie trzeba instalować Pythona ani osobnego WebView2. Ze względu na dołączoną przeglądarkę pakiet jest większy od poprzedniego instalatora.

Ekran startowy to lekkie okno Win32, działające przed uruchomieniem interfejsu. Animowane kostki A/B pokazują etapy przygotowania, postęp rozpakowywania i kontroli plików. Start interfejsu ma osobne potwierdzenie gotowości; animacja nie zastępuje faktycznego sprawdzania. Ograniczenie animacji w ustawieniach Windows jest respektowane.

Pliki są sprawdzane według manifestu SHA-256. Równoległe starty współdzielą blokadę przygotowania. Przerwane rozpakowanie nie jest publikowane jako gotowe; uszkodzona kopia jest zastępowana nową generacją bez nadpisywania używanego programu. Jednoplikowy EXE zawiera skompresowane dane jako końcową sekcję pliku, a nie pobiera ich z Internetu.

Wyniki i ustawienia są zapisywane w normalnych folderach użytkownika, tak jak wcześniej. Przeglądarka wersji przenośnej ma osobny profil w `%LOCALAPPDATA%\DSCompare\portable-webview`. Źródła bazowe silnika pochodzą z run **41291652234**, commit **22b9e73746e8721e146b10d3e3656df67e77956c**. Po sprawdzeniu SHA-256 nakładane są aktualne poprawki z `review/fix06`; silnik jest następnie ponownie testowany i kompilowany razem z bieżącą aplikacją. Suma SHA-256 dołączonego silnika jest sprawdzana przed pakowaniem. Zmiany 0.6.0 obejmują uproszczenie obsługi: dopasowanie okna do obszaru ekranu, natywne przeciąganie plików STEP, osobny widok wyników i 3D, czytelny wynik masy, nowe porównanie oraz osobne listy BOM A/B w HTML. CSV jest opcjonalny.

Pakiet WebView2 i jego skrót są przypięte w `webview-source.json`, pobrane z oficjalnej strony Microsoft. Prawa odczytu wymagane przez AppContainer w Windows 10 są ustawiane tylko dla dołączonego folderu WebView2 zgodnie z dokumentacją Microsoft. Nie są zmieniane ustawienia przeglądarki systemowej ani rejestr instalacji.


Wersja 0.6.2 dopuszcza automatyczny Common dla powtarzających się detali, jeżeli ich pełne liczby wystąpień w A i B są takie same i nazwy wskazują tę samą rodzinę po pominięciu oddzielonej rewizji. Uwzględniane są m.in. `12345_REV_A` / `12345_REV_B`, `12345_A` / `12345_B` oraz `12345_01` / `12345_02`. Nie są dopasowywane dowolne krótkie fragmenty ani różne numery rysunków (`PART_100` / `PART_200`). Liczone są całe modele, również części już dopasowane. Same nazwy i liczby nie dowodzą zmiany materiału: każda dopuszczona para przechodzi natywne Common/Cut. Nazwy ani podobne wymiary nie dowodzą powtórzenia: grupowanie wymaga natywnej, dokładnej lub zweryfikowanej geometrii B-Rep. Niedopuszczone lub niepotwierdzone pary pozostają jako osobne stare usunięte i nowe dodane; rzeczywiste błędy geometrii pozostają do sprawdzenia. Poprawiono pamięć tożsamości obiektów oraz deterministyczne szukanie przesunięć. Obecny interfejs Tauri, podgląd WebGL, raporty masy, paleta i dołączony WebView2 są zachowane.


## Wydanie 0.6.4

Jest to techniczna kompilacja najnowszych źródeł 0.6.2 z gałęzi `fix/latest-common-shift-20261105` (commit `bc71d7b8`), z ujednoliconą wersją 0.6.4 w aplikacji desktopowej, launcherze, manifeście i artefaktach. Algorytm CAD pozostaje taki sam jak w bazie źródłowej, bez niezweryfikowanych zmian dopasowania.

Wersja 0.6.4 doprecyzowuje hipotezy przesunięcia z granic oryginalnej geometrii CAD, gdy zintegrowane środki brył STEP są niedokładne. Granice i nazwy służą tylko wyszukiwaniu: każda uznana para wymaga dowodu B-Rep. Dla złożeń od 80 brył wstępna kontrola obejmuje ograniczoną próbkę, a pozostałe części sprawdza końcowe porównanie. Przycisk „Szukaj dokładniej” kontynuuje bieżące wyszukiwanie bez uruchamiania starego align_assembly i bez powtarzania ukończonych hipotez. W folderze zadania ENGINE_BUILD.json identyfikuje faktyczny silnik i commit.
