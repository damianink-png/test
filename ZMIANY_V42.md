# DS Compare 4.2 — paczka źródłowa do GitHub

Cel: wczytać model A i B, zobaczyć zmiany i szybko obejrzeć wybrane części.
Paczka nie zawiera skompilowanego programu Windows. Workflow buduje EXE,
DLL i kompletny przenośny ZIP. W tej sesji nic nie opublikowano na GitHubie.

## Usprawnienia

- Podgląd generowany bezpośrednio z wczytanych brył, bez pośredniego eksportu
  i ponownego importu STEP. Eksport kolorowego STEP i pełnej różnicy jest opcjonalny.
- Tabela wyników dostępna przed ukończeniem generowania sceny przy domyślnych opcjach.
- Drzewko kategorii i wystąpień części; izolacja wybranej pary, pokaż wszystko,
  poprzednia/następna zmiana, widoczność poprzedniej wersji.
- Szare części bez zmian, zielone nowe, czerwone usunięte, żółte niepewne.
  Kolory można zmienić w ustawieniach. Zachowano wyrównane ikony menu 26 px.
- Stabilne identyfikatory łączą raport ze sceną. Liczniki i diagnostyka informują
  o brakujących siatkach; błąd podglądu nie jest potajemnie uznawany za kompletność.
- Szczegółowa różnica dodanej/usuniętej objętości wybranej pary obliczana na żądanie.
- Dwuklik w tabeli masy pokazuje wszystkie wystąpienia danej grupy geometrycznej.
- Filtry kategorii są zapisywane w ustawieniach. Pełna analiza pozostaje aktywna,
  aby wyłączenie prezentacji obrotów lub geometrii nie tworzyło fałszywych nowych części.
- Podgląd nie czyści dziennika analizy. Zapisany wynik można ponownie otworzyć.
- Dodatkowe dopasowanie prostych brył przez wspólną objętość. Ograniczenie do 24
  ścian i 40 testów chroni przed kosztownym pełnym porównywaniem wszystkich par.
  Niejednoznaczne dopasowania pozostają do sprawdzenia.
- Eksport STEP nadal weryfikuje kolory powierzchni po ponownym odczycie;
  usunięto drugą, zbędną kopię tej samej walidacji.

## Weryfikacja lokalna

- 54 testy automatyczne zakończone powodzeniem (Linux, OCP 7.8.1.1, VTK 9.3.1).
- Test procesu aplikacji: porównanie, kolorowy STEP, pełna różnica i scena bezpośrednia.
- Przykład: scena 5/5 pozycji, 7 brył A/B, zero błędów siatki.
- Kolorowy STEP po ponownym odczycie: 31 powierzchni z kolorem, zero bez koloru.
- Osobny proces szczegółów wybranej pary poprawnie utworzył scenę różnic.
- Testy Qt sprawdzają logikę filtrów i zachowanie dziennika. Wizualne renderowanie
  OpenGL w środowisku bez ekranu nie zostało wiarygodnie zweryfikowane.

## Duże złożenie OpenArm

Przetestowano pliki OpenArm v1.0 / v1.1: po 553 bryły.
Pokrycie indeksów analizy: 553/553 A i 553/553 B, bez pominiętych wystąpień.
Wynik: 522 bez zmian, 11 niepewnych par, 20 nowych i 20 usuniętych.
To wynik algorytmu, nie ręcznie zweryfikowana prawda konstrukcyjna.
Scena: 573/573 pozycji, 584 bryły A/B, zero błędów siatki.
Liczba brył sceny jest większa od liczby pozycji, ponieważ niepewne pary
zawierają osobno obie wersje. Części bez zmian pokazano raz.
Brak porównania czasów na identycznym stanowisku; nie deklarujemy przyspieszenia procentowego.

## Granice tej wersji

Drzewko przedstawia kategorie i wystąpienia, nie pełną hierarchię montażową CAD.
Dopasowanie zmienionych części jest heurystyką: wspólna objętość nie dowodzi
ich tożsamości konstrukcyjnej. Masa zakłada jedną podaną gęstość.
Przycisk eksportu z wyników przygotowuje ponowną analizę z eksportem i wymaga
oryginalnych A/B oraz kliknięcia Start. Nie jest to eksport z pamięci wyników.

Nie wykonano kompilacji Windows ani testu wewnątrz ZW3D 2019 w tej sesji.
Workflow zawiera testy zbudowanego EXE, kolorów, sceny, szczegółów pary,
uruchomienia Qt oraz ładowania DLL. DLL pozostaje eksperymentalnym mostkiem;
test jej ładowania nie potwierdza poprawności integracji z ZW3D.
Nie gwarantujemy zachowania kolorów przez importer ZW3D bez testu na stanowisku.

## Jak zbudować

1. Wgraj `DSCompare_V4_2_ZRODLA.zip` do katalogu głównego repozytorium bez rozpakowania.
2. Dodaj osobny plik workflow pod `.github/workflows/build-dscompare-v42.yml`.
3. Uruchom workflow DS Compare V4.2 w zakładce Actions.
4. Po poprawnym zakończeniu pobierz artefakt z ZIP-em Windows EXE + DLL.
5. Rozpakuj cały ZIP; zachowaj EXE, DLL i folder `_internal` razem.

Pełna instrukcja znajduje się w `INSTRUKCJA_GITHUB.txt` i `v42/README_V42.txt`.
