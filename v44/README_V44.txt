DS Compare 4.4 — Windows x64, EXE + DLL ZW3D 2019
Autor: Szymczyk Damian

URUCHOMIENIE
Rozpakuj cały ZIP. Uruchom DSCompareV3.exe. Folder _internal musi pozostać obok EXE.
Nie wymaga instalacji Pythona ani uprawnień administratora.
Nazwa EXE pozostaje taka sama, aby istniejące połączenia z DLL działały.

ZW3D 2019
Zamknij ZW3D przed wymianą załadowanej DLL. Zachowaj poprzednią wersję.
DSAssemblyCompare2019.dll i DSCompareV3.exe mogą być obok siebie.
Jeżeli DLL jest w osobnym katalogu, plik DSComparePath.txt obok DLL powinien
zawierać pełną ścieżkę do DSCompareV3.exe.
~DSCOMPARE_A — eksport aktywnego modelu A
~DSCOMPARE_B — eksport aktywnego modelu B i otwarcie programu
~DSCOMPARE lub ~DSAC — otwarcie programu

ZMIANY W 4.4 — WSPÓLNY WIDOK A/B
Start w przestrzeni Model A / B. Pola A i B przyjmują przeciągnięte pliki STEP.
Przycisk Porównaj korzysta z parametrów z zakładki Opcje analizy.
Po lewej lista Zmiany oraz zakładka Wszystkie części, każda z wyszukiwaniem.
Kliknięcie zmiany pokazuje parę i otwiera szczegóły po prawej. Izolacja jest osobna.
Tryby A / B / A+B zachowują kamerę; niezmienione części można przygasić.
Opcje innych modeli i szczegółowości ukryto pod Inny podgląd.
Liczniki pokazują pokrycie analizy i kompletność siatki.

RĘCZNE WSKAZANIE PARY
Dla niepewnych, nowych i usuniętych części otwórz szczegóły i Wskaż parę A/B.
Wybierz część A oraz B. Korekta uruchamia ponowną analizę w nowym folderze.
Wymagane są oryginalne pliki. SHA-256 blokuje zastosowanie indeksów do zmienionych
źródeł. Dotychczasowe ręczne pary są zachowywane, poza konfliktującymi z nową.
Pozostałe części z rozdzielonych par pozostają niepewne i nie znikają z raportu.
Tożsamość pary jest decyzją użytkownika; zgodność geometrii jest badana oddzielnie.
Opcja działa dla analiz wykonanych w 4.4. Starsze wyniki można oglądać,
ale przed korektą trzeba wykonać nowe porównanie. Cofnięcie wszystkich korekt:
uruchom zwykłe porównanie pierwotnych A/B. Poprzednie foldery pozostają dostępne.

ZMIANY W 4.3
- Globalny dobór par przesuniętych i zmienionych brył w grupach kandydatów.
- Alternatywne przypisanie jest sprawdzane przez ponowne rozwiązanie grupy
  bez wybranej pary. Mała różnica wyniku oznacza niepewną tożsamość części.
- Zgodność geometrii nie jest utożsamiana z pewnością, które wystąpienie
  odpowiada któremu. Niepewne duplikaty są jawnie oznaczane.
- Grupy powyżej 60 elementów po którejkolwiek stronie korzystają z uproszczonego
  doboru z oznaczeniem niepewności, aby ograniczyć koszt optymalizacji.
- Ciemny grafitowy interfejs, spójniejsze kolory liczników i krótkie statusy.
- Wyszukiwarka części w drzewku, przełącznik krawędzi, początkowy widok
  izometryczny i jasne gradientowe tło sceny CAD.
- 87 testów automatycznych, w tym 20 scenariuszy trafności i 8 dodatkowych
  wariantów parametrów. Wyniki i ograniczenia opisano w RAPORT_V43.md.

ZMIANY W 4.2
- Domyślnie porównanie i bezpośredni podgląd bez eksportu STEP i pełnych różnic.
  Scena powstaje z już wczytanych brył, bez ponownego importowania kolorowego STEP.
- Wynik tabelaryczny udostępniany przed zakończeniem przygotowywania sceny.
- Drzewko kategorii i wystąpień części, zaznaczanie, izolacja, pokaż wszystko,
  poprzednia/następna zmiana. Nie jest to oryginalna hierarchia montażowa CAD.
- Bez zmian: szary, nowe: zielony, usunięte: czerwony, niepewne: żółty.
  Poprzednie bryły par zmienionych są półprzezroczyste i można je ukryć.
- Liczniki pokrycia i diagnostyka brakujących siatek; każda pozycja ma stały ID.
- Szczegóły różnicy wybranej pary obliczane dopiero na żądanie z pamięci B-Rep.
- Podgląd wszystkich wystąpień części z tabeli masy po dwukliku.
- Filtry kategorii w ustawieniach dotyczą prezentacji. Analiza nadal sprawdza
  wszystkie bryły, aby wyłączenie kategorii nie tworzyło fałszywych nowych/usuniętych.
- Otwarcie zapisanego wyniku bez ponownej analizy; podgląd nie usuwa dziennika.
- Dodatkowa heurystyka wspólnej objętości dla prostych, pobliskich brył
  (do 24 ścian, do 40 sprawdzeń), np. skróconego profilu o zmienionej nazwie.
  Niejednoznaczne pary pozostają kategorią „Do sprawdzenia”.
- Usunięto powtórny pełny odczyt walidacyjny kolorowego eksportu STEP;
  jedna pełna weryfikacja kolorów powierzchni jest zachowana.

SPOSÓB PRACY
Wybierz A i B, kliknij porównanie, obejrzyj wynik oraz scenę 3D.
Dwuklik wyniku przybliża część. Drzewko umożliwia wybranie i odizolowanie pary.
Przycisk szczegółów pokazuje dodaną i usuniętą objętość wybranej pary.
Pełny kolorowy STEP i ROZNICE_BREP.step są opcjonalne. Można je zaznaczyć
przed analizą. Przycisk eksportu z wyników przygotowuje ponowne porównanie
z włączonym eksportem; wymaga ponownego kliknięcia Start i dostępu do A/B.
W tym trybie eksport może wydłużać oczekiwanie na wyniki.
Przechowuj cały folder wyniku: SCENA_WYNIK.npz, raporty oraz katalog Geometria
są potrzebne do odtwarzania podglądu i szczegółów bez plików źródłowych.
W tabeli masy wyłącz edycję ilości przed dwuklikiem służącym do podglądu.

ZACHOWANE ZMIANY 4.1
- Etykiety NAUO nie udają nazw konstrukcyjnych; używana jest nazwa definicji STEP.
- Różnice nazw eksportowych nie oznaczają automatycznie RENAMED.
- Geometryczny BOM łączy potwierdzone identyczne bryły także przy innych nazwach.
  Nie rozróżnia materiału, numeru zamówienia ani technologii. Wszystkie wystąpienia
  i ich ścieżki są zapisane w BOM_GRUPY_A.json oraz BOM_GRUPY_B.json.
- Dokładne kopie zapisu B-Rep korzystają z pamięci wyników BOM.
- Ujemne przemieszczenia i różnice objętości pozostają liczbami w Excelu.
- Wyrównanie korzysta także z unikalnej geometrii; brak pewnego wyniku nie przerywa
  porównania. Ostrzeżenie pojawia się w oknie, HTML, JSON i OSTRZEZENIA.txt.
- Ostatni poprawny wynik jest zachowywany po nieudanej analizie.

ZACHOWANE POPRAWKI 4.0
- Równe ikony wektorowe 26 px, stała wysokość przycisków menu; obsługa skalowania Qt.
- Osobne kategorie i kolory: geometria, nowe, usunięte, położenie/obrót, niepewne.
- Dwuklik pozycji wyniku otwiera i przybliża odpowiadającą bryłę w podglądzie.
- Wyszukiwanie, filtr kategorii, szczegóły przemieszczenia i kąta dopasowania.
- Każde porównanie zapisuje się w osobnym folderze z datą i czasem.
- STEP: definicje części, wystąpienia i wszystkie powierzchnie mają jawny kolor.
  Eksport sprawdza każdą powierzchnię po ponownym odczycie; niepełny plik nie jest publikowany.
- Kolorowy STEP AP214 jest domyślny. AP242 można wybrać w oknie.
- Różnice materiału są dostępne jako ROZNICE_BREP.step i w podglądzie 3D.
- Poprawiono podgląd zagnieżdżonych złożeń: odwołania i transformacje rodziców.
- Dopasowanie symetrycznych brył używa dodatkowych baz geometrycznych i testu B-Rep.
- Niepewne pary i błędy obliczeń nie są oznaczane jako potwierdzona zgodność.
- BOM grupuje części po potwierdzeniu geometrii, nie tylko przybliżonej sygnaturze.
- Opcjonalne wyrównanie całego B do A; transformacja zapisana w PODSUMOWANIE.json.
- Anulowanie procesu nie jest prezentowane jako awaria; źródła nie są modyfikowane.

INTERPRETACJA
Geometria: bryły różnią się, ale tożsamość pary na podstawie nazwy/położenia
wymaga kontroli. „Do sprawdzenia” oznacza niejednoznaczność lub błąd testu.
Obrót jest kątem znalezionego dopasowania. Symetryczna bryła może mieć kilka
równoważnych orientacji. Program nie odczytuje historii operacji CAD.
Tolerancja to próg numeryczny B-Rep, nie gwarantowana maksymalna odchyłka powierzchni.
Masa zakłada jedną gęstość dla wszystkich części. BOM dotyczy brył STEP.
Wyrównanie wymaga jednoznacznych wspólnych części; niezgodne/niejednoznaczne
transformacje powodują ostrzeżenie i porównanie w oryginalnych położeniach.

WERYFIKACJA
Workflow wykonuje testy geometrii, kolorów, podglądu i GUI; kompilację MSVC DLL;
test zbudowanego EXE w trybach porównania, siatki 3D i uruchomienia okna.
Nie wykonano testu wewnątrz rzeczywistego ZW3D 2019. Obsługa kolorów w jego
importerze wymaga sprawdzenia na stanowisku. Nowy eksporter zapisuje kolory
powierzchni; opcja importowania kolorów w ZW3D musi być włączona.
