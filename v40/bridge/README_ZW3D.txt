ZW3D 2019 - DS Compare V3.0 bridge (PROTOTYP)

1. Zapisz dokumenty i zamknij ZW3D.
2. Zrob kopie poprzedniej biblioteki DSAssemblyCompare2019.dll.
3. Nowa DLL zajmuje jej miejsce (tylko jesli poprzednia byla ladowana poprawnie).
4. Obok DLL umiesc plik DSComparePath.txt z pelna sciezka do DSCompareV3.exe.
5. W ZW3D otworz/aktywuj plik A, wpisz ~DSCOMPARE_A.
6. Otworz/aktywuj plik B, wpisz ~DSCOMPARE_B.
7. Zewnetrzny program uruchomi sie z obiema sciezkami STEP.

Komenda ~DSAC otwiera GUI, ale nie wykonuje eksportu.
Komendy nie otwieraja i nie zamykaja plikow Z3.

W przypadku bledu: %TEMP%\DSCompareV3\bridge.log
UWAGA: DLL nie zostala jeszcze sprawdzona na dzialajacym ZW3D.
