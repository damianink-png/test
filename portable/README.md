# DS Compare Portable 0.5.2

Dwa pakiety Windows x64 nie wymagają instalatora ani uprawnień administratora:

- **Portable ZIP**: rozpakuj cały folder i uruchom `DSCompare.exe`. Folder `app` pozostaje obok programu.
- **Jeden EXE w ZIP**: rozpakuj i uruchom `DSCompare.exe`; można przenosić sam ten plik. Pierwszy start przygotowuje pliki w `%LOCALAPPDATA%\DSCompare\portable`. Kolejne sprawdzają i ponownie wykorzystują kopię. Nie jest to instalacja w systemie.

Oba zawierają natywny interfejs Svelte/Tauri, kompletny zamrożony silnik Python/OCCT oraz oficjalny Microsoft WebView2 Fixed Runtime. Nie trzeba instalować Pythona ani osobnego WebView2. Ze względu na dołączoną przeglądarkę pakiet jest większy od poprzedniego instalatora.

Ekran startowy to lekkie okno Win32, działające przed uruchomieniem interfejsu. Animowane kostki A/B pokazują etapy przygotowania, postęp rozpakowywania i kontroli plików. Start interfejsu ma osobne potwierdzenie gotowości; animacja nie zastępuje faktycznego sprawdzania. Ograniczenie animacji w ustawieniach Windows jest respektowane.

Pliki są sprawdzane według manifestu SHA-256. Równoległe starty współdzielą blokadę przygotowania. Przerwane rozpakowanie nie jest publikowane jako gotowe; uszkodzona kopia jest zastępowana nową generacją bez nadpisywania używanego programu. Jednoplikowy EXE zawiera skompresowane dane jako końcową sekcję pliku, a nie pobiera ich z Internetu.

Wyniki i ustawienia są zapisywane w normalnych folderach użytkownika, tak jak wcześniej. Przeglądarka wersji przenośnej ma osobny profil w `%LOCALAPPDATA%\DSCompare\portable-webview`. Kod silnika CAD i jego pliki binarne pochodzą z pomyślnie zweryfikowanego run **41291652234**, commit **22b9e73746e8721e146b10d3e3656df67e77956c**. Przygotowanie źródeł sprawdza ich identyczność; zmiany 0.5.2 dotyczą pakowania i potwierdzenia gotowości interfejsu.

Pakiet WebView2 i jego skrót są przypięte w `webview-source.json`, pobrane z oficjalnej strony Microsoft. Prawa odczytu wymagane przez AppContainer w Windows 10 są ustawiane tylko dla dołączonego folderu WebView2 zgodnie z dokumentacją Microsoft. Nie są zmieniane ustawienia przeglądarki systemowej ani rejestr instalacji.
