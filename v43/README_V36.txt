DS COMPARE V3.6 — NOWY INTERFEJS + MOTYW JASNY/CIEMNY + PODGLĄD KOLORÓW

1) Rozpakuj CAŁE archiwum kompilacji Windows. Folder _internal musi być obok DSCompareV3.exe.
2) Uruchom DSCompareV3.exe i wybierz dwa pliki STEP lub STP.
3) Na pasku u góry wybierz motyw jasny albo ciemny; wybór zostaje zapisany w %APPDATA%\DSCompare\settings.json.
4) W zakładce Porównanie pozostaw zaznaczone „Kolorowy STEP” oraz „Podgląd 3D w przeglądarce”.
5) Po analizie w Wynikach kliknij „Podgląd 3D”. Otworzy się PODGLAD_KOLOROW_3D.html.
   To niezależny, obracany podgląd B-Rep po triangulacji (WebGL offline). Nie jest edytowalnym STEP.
6) POROWNANIE_KOLORY.step jest prawdziwym modelem B-Rep STEP z kolorami XCAF.
   Kolory w CADbro zależą od importu stylów i włączenia widoku cieniowania. Jeśli są niewidoczne,
   sprawdź DIAGNOSTYKA_KOLOROW.json; prześlij też fragment oryginalnego STEP i wynikowego STEP.
7) Masa części: jedna bryła / pojedynczy STEP, zestawienie CSV i HTML.
8) ZW3D 2019: eksperymentalna DLL; zachowaj kopię poprzedniej wersji.

UWAGA: Nie ma możliwości potwierdzenia wyświetlania kolorów CADbro wyłącznie na podstawie
poprawnego transferu do STEP, bez uruchomienia CADbro na komputerze docelowym.

Wersja i autor: DS Compare / O programie / Szymczyk Damian.
