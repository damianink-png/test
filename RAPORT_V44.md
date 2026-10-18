# DS Compare 4.4 — wspólna przestrzeń porównania A/B

## Zmiany

- Program otwiera przestrzeń Model A / B. Dwa pola z przeciąganiem plików STEP
  i przycisk Porównaj są bezpośrednio nad podglądem.
- Po lewej domyślna lista Zmiany oraz osobna zakładka Wszystkie części.
  Obie mają wyszukiwanie; lista respektuje kategorie i kolory analizy.
- Kliknięcie pozycji zaznacza parę A/B, przybliża jej obszar i otwiera panel
  szczegółów po prawej. Pozostałe części pozostają widoczne; izolacja jest osobna.
- A / B / A+B przełącza widoczność bez resetowania kamery. Dla części bez zmian
  używana jest jedna wspólna siatka w obu trybach. Wyrównanie, jeśli włączone,
  oznacza porównywanie B już w wyrównanym układzie.
- Przygasić bez zmian można niezależnie od ukrywania kategorii.
- Panel szczegółów podaje kategorię, opis i podstawę dopasowania. Można go zamknąć.
- Stały pasek pokazuje rzeczywiste pokrycie indeksów A/B oraz kompletność siatki
  i liczbę jej błędów. Widoczność wynikająca z filtrów jest odrębną informacją.
- Zaawansowany wybór źródła podglądu schowano pod Inny podgląd. Raporty, eksport
  i masa są w osobnych zakładkach.

## Ręczne pary

Przycisk Wskaż parę A/B umożliwia wybranie części spośród niepewnych, zmienionych,
nowych i usuniętych oraz wcześniej wskazanych ręcznie. Korekta uruchamia nowe
porównanie w osobnym folderze, zachowując poprzedni wynik.

Decyzja użytkownika dotyczy tożsamości części. Program osobno sprawdza B-Rep
w oryginalnym lub wyrównanym ustawieniu. Błąd geometrii pozostaje niepewnością.
Niewykorzystane części ze zmienionych przypisań są jawnie zachowane jako niepewne.
Raport przechowuje ręczne pary, a SHA-256 blokuje użycie indeksów dla zmienionych
plików źródłowych. Potrzebne są oryginalne A/B i analiza wykonana w 4.4.
Ponowne zwykłe porównanie A/B pozwala wrócić do automatycznego dopasowania.

## Weryfikacja

- 104 testy automatyczne: PASS, w tym wcześniejsze testy trafności i przypisań.
- Nowe testy: widoczność A/B/A+B, przygaszanie, brak zmiany kamery podczas
  przełączania, kompletność po ręcznej korekcie, błędy geometrii, konflikt par,
  blokada zmienionego pliku, panel zmian i liczniki.
- Sprawdzono pełną analizę z ręczną parą i poprawne utworzenie sceny.
- Sprawdzono także dwa rzeczywiste procesy aplikacji: analiza i ponowna analiza
  z plikiem ręcznej korekty. Wynik: WORKER_MANUAL_OK.
- Kontrola układu rzeczywistego okna Qt przy 1600×950. Nie wykonano wiarygodnej
  wizualnej walidacji renderowania OpenGL/VTK w tym środowisku bez ekranu.
- Algorytm automatycznych przypisań z 4.3 zachowany. Dużego OpenArm nie testowano
  ponownie w tej iteracji; poprzedniego wyniku nie przedstawiamy jako testu 4.4.

## Ograniczenia

To wdrożenie funkcjonalnego układu z koncepcji, nie jej odwzorowanie piksel w piksel.
Nie dodano automatycznej interpretacji grubości blach i średnic otworów.
Drzewko nadal grupuje wystąpienia według kategorii; nie jest pełnym drzewem montażowym.
Ręczna korekta ponownie wczytuje źródła i analizuje geometrię; nie jest natychmiastowa.
Dokładna różnica wybranej pary jest obliczana na żądanie. Wynik zależy od poprawności
STEP i od trafności wskazania pary przez użytkownika.

Dostarczono źródła, workflow i instrukcję. Nie opublikowano nic na GitHubie,
nie wykonano kompilacji Windows ani testu DLL wewnątrz ZW3D. Workflow zawiera
budowanie EXE/DLL oraz testy zbudowanego EXE, w tym ręcznej korekty par.

## Wgranie na GitHub

1. Wgraj DSCompare_V4_4_ZRODLA.zip bez rozpakowania do katalogu głównego repozytorium.
2. Dodaj build-dscompare-v44.yml pod .github/workflows/build-dscompare-v44.yml.
3. Uruchom workflow DS Compare V4.4 w Actions.
4. Po poprawnym zakończeniu pobierz artefakt z ZIP-em Windows EXE + DLL.

Szczegóły: INSTRUKCJA_GITHUB.txt oraz v44/README_V44.txt.
