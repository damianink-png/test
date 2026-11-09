# DS Compare 0.6.13 — przegląd ścieżek uruchamiania i zabezpieczeń

Zakres: aktualny silnik desktopowy (Tauri/Svelte + OCP), nakładki `portable/assemble_engine.py`,
porównanie STEP, wyrównanie, natywny ekran startowy. Część plików z wcześniejszych
wersji RC9 pozostaje w bazowym archiwum źródłowym ze względu na testy zgodności.

## Bezpiecznie usunięte
- Widoczna zakładka **Diagnostyka** i przypisana akcja diagnostyczna w Svelte.
  Zachowano dziennik postępu i diagnostykę silnika dla sytuacji błędów.
- Nieużywane importy ikon Svelte i nieosiągalną trzecią gałąź wyboru plików
  w `run('compare'|'mass')`.
- Starą, jednorazową animację startową zastąpił wektorowy skan porównania brył
  A/B z obsługą systemowego ograniczenia animacji.

## Poprawione stare zabezpieczenie
- `compare.py`: twardy limit 240 s obejmował **cały** etap izolowanych prób
  sztywnego dopasowania B-Rep. Aktualny limit wynosi
  `max(240 s, 0.5 s × max(liczba_brył_A, liczba_brył_B))`.
  Natywne sprawdzenia par nadal mają własne limity, operacje są izolowane,
  nieudane dowody nadal nie mogą być publikowane jako SAME.

## Sprawdzone obliczenia, których NIE należy usuwać bez dowodu równoważności
- Pierwsze dopasowanie w położeniu, etap ruchu sztywnego i kwalifikowanie zmian
  geometrii rozwiązują różne problemy. To nie jest trzy razy ten sam test.
- `Common/Cut` oblicza zmiany materiału; pomocnicze powtórzenie operacji po
  błędzie jest celowym odzyskiwaniem dowodu, nie zwykłą redundancją.
- Współdzielone pamięci rodzin B-Rep, `FrameProofCache`, `GeometryRegistry`
  i testy powtórzeń STEP przyspieszają przebieg; różne wyniki natywne muszą
  pozostać odrębne od heurystyk nazw i wymiarów.
- Stary interfejs Qt i wewnętrzne funkcje testowe pozostają do czasu
  bezpiecznego usunięcia z pakowania po sprawdzeniu zależności; nie należy
  wycinać ich mechanicznie z archiwum źródeł.

## Weryfikacja
- Test menu Svelte potwierdza brak Diagnostyki i zachowanie dwóch głównych kart.
- Test budżetu: 1600 brył → 800 s; 80 brył → 240 s.
- Kompilacja Tauri, Rust i PyInstaller oraz test otwarcia natywnego splash
  pozostają obowiązkowe przed wydaniem OneEXE.
- Obowiązkowy test u użytkownika: rzeczywiste ponowne eksporty ZW3D 2019
  AP203/AP214 z 150 identycznymi wystąpieniami i realnymi zmianami.
