DS Compare V3.3 - Windows x64
Designed & developed by Szymczyk Damian

1. Rozpakuj caly folder ZIP. Nie usuwaj _internal.
2. Uruchom DSCompareV3.exe. Nie wymaga Pythona ani uprawnien administratora.
3. Opcjonalnie: uruchom UTWORZ_SKROT_START.cmd zeby dodac skrot do menu Start.
   Po otwarciu programu mozesz go recznie przypiac do paska zadan Windows.
4. Wskaz plik STEP A i plik STEP B. Ustaw tolerancje i kliknij POROWNAJ B-REP.
5. Zakladka Ustawienia: zmien kolory kliknieciem lub kodem #RRGGBB.
   Ustawienia zapisuja sie w %APPDATA%\DSCompare\settings.json.
   Kolory obowiazuja w wynikowym STEP, ROZNICE_BREP.step i RAPORT.html.
6. Zweryfikuj wynik: ZMIANY.csv, BOM_A.csv, BOM_B.csv, RAPORT.html.

KOMENDY ZW3D 2019 - EKSPERYMENTALNE
 ~DSCOMPARE_A   eksport aktywnego dokumentu jako A
 ~DSCOMPARE_B   eksport aktywnego dokumentu jako B i start analizy
 ~DSCOMPARE     otworz program

Zapisz modele i wykonaj kopie DLL przed testami z ZW3D.
Analiza B-Rep pracuje poza procesem CAD. Funkcje mostu ZW3D nie
zostaly zweryfikowane w prawdziwym ZW3D 2019 na Windows.

ZW3D 2019: DLL wymaga rejestracji jak poprzednie wersje dodatku.
Nie mylic ikony samodzielnego programu EXE z przyciskiem na wstazce ZW3D.
Przycisk wstazki wymagalby osobnej integracji UI w ZW3D.
