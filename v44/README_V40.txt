DS Compare 4.0 — Windows x64, EXE + DLL ZW3D 2019
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

ZMIANY 4.0
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
transformacje powodują komunikat, zamiast automatycznego zgadywania.

WERYFIKACJA
Testy automatyczne geometrii, kolorów, podglądu i GUI; kompilacja MSVC DLL;
test zbudowanego EXE w trybach porównania, siatki 3D i uruchomienia okna.
Nie wykonano testu wewnątrz rzeczywistego ZW3D 2019. Obsługa kolorów w jego
importerze wymaga sprawdzenia na stanowisku. Nowy eksporter zapisuje kolory
powierzchni; opcja importowania kolorów w ZW3D musi być włączona.
