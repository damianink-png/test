# Desktop 0.5.1 / Review 06.1 — WinError 32

W run 41278032537 przeszedł build Windows, 346 regresji, instalator Tauri, pięć scenariuszy V2/Trident i jawnie częściowy OpenArm. V2 `revision_shift` zatrzymał się na usuwaniu `_ETAPY_DIAGNOSTYKA.jsonl` w katalogu `dscompare_world_*`: Windows zgłosił, że plik jest używany przez inny proces.

## Przyczyna

Proces sesji jest używany do kolejnych zadań B-Rep. Każde wywołanie funkcji worker ponownie uruchamiało diagnostykę i kierowało globalny dziennik oraz żywy wątek heartbeat do tymczasowego katalogu pojedynczego zadania. Po opublikowaniu odpowiedzi proces nadrzędny usuwał katalog. Wątek diagnostyczny mógł w tej chwili mieć otwarty jego plik — w Windows kończyło to całą analizę błędem sprzątania. Nie był to zgłoszony błąd wyniku Common ani nowa awaria geometrii.

## Zmiana

Diagnostyka inicjuje się raz dla procesu sesji i pozostaje w jego stabilnym katalogu. Wywołanie worker z sesji nie zmienia ścieżki loggera. Pojedyncze zadanie zachowuje swoje pliki wejścia, odpowiedź i znacznik etapu, ale nie posiada żywego loggera ani faulthandlera.

Proces nadrzędny oczekuje na osobne, atomowo publikowane potwierdzenie zakończenia z numerem zadania. Samo pojawienie się odpowiedzi nie wystarcza. Potwierdzenie powstaje dopiero po powrocie funkcji worker i zakończeniu wszystkich jej zapisów. Usuwanie katalogu następuje po tej granicy. Nie zastosowano ignorowania błędów sprzątania ani zmiany wyniku porównania na poprawny.

Timeout, błędny numer potwierdzenia, niepoprawny protokół lub zakończenie procesu pozostają błędami. Przy błędzie proces jest zatrzymywany przed sprzątaniem, a jego dziennik trafia do `NATIVE_SESSION_DIAGNOSTYKA.jsonl` w zachowywanym materiale diagnostycznym. Tolerancje i algorytmy CAD są takie jak w 0.5.0.

## Kontrole

`tests/test_native_session_lifecycle.py` sprawdza rzeczywiste 24 żądania w jednym procesie, brak dzienników w usuwanych katalogach, pojedynczą inicjalizację diagnostyki oraz zakończenie procesu i usunięcie katalogu sesji. Oddzielny proces testowy celowo publikuje odpowiedź przed ostatnim zapisem; nadrzędny musi poczekać na ten zapis. Kontrole odrzucają niezgodny numer, bool zamiast numeru, pusty obiekt i listę oraz zachowują dziennik po timeout. Nowe kontrole są częścią bramki regresji Windows.

Lokalny sukces tych kontroli nie zastępuje ponownego testu zamrożonego EXE na Windows i dużym V2. Wszystkie dotychczasowe scenariusze i audyty pozostały wymagane; OpenArm nadal jest testem raportu częściowego.

Walidacja lokalna po poprawce: 352 testy regresyjne zaliczone, jeden test Windows pominięty na Linuksie; 7 kontroli oryginalnej geometrii zaliczonych. Frontend: 0 błędów/ostrzeżeń Svelte, build i 4 testy zaliczone. Rust: 3 testy zaliczone z zamrożonym plikiem zależności (`--locked`). Nowy przebieg Windows jest wymagany dla pełnego potwierdzenia poprawki.
