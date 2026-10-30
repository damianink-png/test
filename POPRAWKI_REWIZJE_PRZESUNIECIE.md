# Poprawki po zgłoszeniu błędu rewizji i przesunięcia

Ta kompletna paczka zastępuje wcześniejszą wersję z PR #1. Zawiera wszystkie wcześniejsze poprawki raportów, kolorów i 3D.

## Co zmieniono

- Odrzucenie pomocniczego Common podczas `bind_common` nie powoduje już nieobsłużonego błędu. Program odrzuca ten wynik i oblicza niezależnie Common oraz oba Cut w izolowanym procesie. Każdy kształt oraz bilans materiału muszą przejść walidację. Niepowodzenie ponownego dowodu nadal zatrzymuje analizę z jawnym błędem.
- Naprawiono wyszukiwanie zgodnych brył w dużych złożeniach po eksporcie STEP. Przechwycona para 37 powierzchni miała różnicę całkowanych środków 0,199449 mm, chociaż wszystkie oryginalne powierzchnie i obrysy spełniały dowód w tolerancji 0,01 mm. Promień wyszukiwania kandydatów jest oddzielony od tolerancji dowodu. Naprawa działa także bez przesunięcia i nie kieruje już takiej pary do Common.
- W małych złożeniach usunięto niemożliwy warunek: przy dwóch częściach wymagano czterech pozytywnych dowodów, mimo zgodności wszystkich dostępnych par.
- Przesunięta część ze zmienioną nazwą STEP zachowuje status MOVED po potwierdzeniu geometrii i liczby wystąpień. Zmieniona etykieta nie ustanawia ani nie wyklucza tożsamości geometrii.
- Wynik aplikacji i raport pokazują globalne przesunięcie oraz wektor zastosowanego wyrównania B → A. Dzięki temu SAME po wyrównaniu nie ukrywa informacji o pierwotnym przesunięciu całego złożenia. Odróżnione są też niepotwierdzone przesunięcie i świadomy wybór oryginalnych współrzędnych.
- Pola tolerancji, limitu brył, przezroczystości i gęstości mają oddzielne przyciski „−” i „+”, czytelną wartość i możliwość wpisywania z klawiatury. Przyciski respektują granice i wyłączenie pola. Natywne strzałki Qt powodujące nieprawidłowy wygląd na Windows są ukryte.
- Znane błędy geometrii pokazują krótki komunikat; pełny traceback pozostaje w `DIAGNOSTYKA_BLEDU.txt` w katalogu danego zadania.

## Sprawdzenie zgłoszonego przesunięcia

Wektor przesunięcia B względem A: **X +507,4569; Y −249,1752; Z +524 mm**.
Oczekiwane wyrównanie B → A: **X −507,4569; Y +249,1752; Z −524 mm**.

Testy tworzą rzeczywiste pliki STEP, wczytują je ponownie i uruchamiają produkcyjne `cli.process`. Dla 2, 6 i 20 części program potwierdza właściwy wektor, klasyfikuje niezmienione części po wyrównaniu i pokazuje informację w HTML. Oddzielny test potwierdza, że przesunięcie jednej części pozostaje MOVED i nie wyrównuje całego złożenia. Testowana jest również wcześniejsza translacja 1000/−300/50 mm.

Przechwycona para z GitHub: przebieg `41035666577`, artefakt `12969261874`, pliki `FAILED_BREP/common`. Nowy test obejmuje ją w złożeniu 601 elementów, z wcześniej potwierdzoną ramą i bez niej. Negatywna kontrola z dodatkowym przesunięciem 0,02 mm nie może uzyskać zgodności. Pochodzenie i SHA-256 znajdują się w `tests/fixtures/centroid_reexport/PROVENANCE.json`.

## Granice potwierdzenia

Weryfikacja lokalna obejmuje testy regresji, rzeczywisty interfejs Qt/QProcess oraz Chromium/WebGL. Test Windows Job Object jest pomijany na Linux i wykonywany w Windows CI. Wyniki XML i logi są w osobnej paczce dowodów.

Nie mam źródłowych plików STEP ze zdjęcia, więc test zgłoszonego wektora używa wygenerowanych złożeń, a test trudnej topologii — rzeczywistego artefaktu GitHub. Nie jest to deklaracja ukończenia analizy konkretnej pary użytkownika.

Lokalna próba pełnego publicznego V2 bez przesunięcia przeszła klasyfikację rewizji, ale proces został zakończony przez limit 8 GB pamięci tego środowiska podczas eksportu STEP. Nie oznaczono jej jako PASS. Pełną weryfikację EXE na większych runnerach Windows zapewnia nowy workflow: V2/Trident, rewizje bez przesunięcia oraz przesunięcie z podanym wektorem, także po zmianie rewizji. Dotychczasowy Windows build przeszedł, lecz jego duże testy wykazały opisany wyżej problem wyszukiwania.

## Uruchomienie

Rozpakuj nowy ZIP i używaj zawartego w nim całego katalogu `dscompare_rc9_manual`. Nie nakładaj starego ZIP-u poprawek.

Windows/PowerShell w tym katalogu:

```powershell
./BUDUJ_WINDOWS.ps1 -InstallOnly
python -m pip install pytest
python ci/run_manual_regressions.py
python ci/test_rc9_original_boundary.py
./BUDUJ_WINDOWS.ps1 -NoInstall
```

Wynik: `dist/DSCompare/DSCompare.exe`. Testy i pliki wykonywalne z GitHub są przypisane do konkretnego commita — starszy EXE nie zawiera tych poprawek.
