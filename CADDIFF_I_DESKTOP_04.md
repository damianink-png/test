# Wyniki kontroli CADdiff i migracja Desktop 04

## Stan błędów GitHub

Run 41099940185, commit 026fa3f: 326 testów Windows i pakowanie PASS. Trident: przesunięcie, rewizje i rewizje z przesunięciem PASS. V2: rewizje bez przesunięcia PASS. Osobny OpenArm z jawną zgodą na raport częściowy PASS — nie jest to pełna analiza materiału. Dwa V2 z przesunięciem nadal FAIL, dlatego nie uznajemy ich za zamknięte.

Nowy blokujący przypadek: złącze Molex 0471510001, 270 ścian. A jest formalnie poprawne, B nie. Obie oryginalne powierzchnie i wszystkie krawędzie spełniają pełny dowód zgodności przy 0.01 mm. Koordynator wcześniej dopuszczał taki dowód jedynie dla pary dwóch niepoprawnych brył i pomijał go dla pary mieszanej. Teraz przed naprawą próbuje tego samego pełnego dowodu także dla pary mieszanej. Nadal nie akceptuje samej zgodności objętości, gabarytów ani tolerancji zapisanej w pliku. Gdy dowodu nie ma, zachowuje kontrolowaną naprawę kopii z tym samym budżetem i zatrzymanie przy niepowodzeniu.

Dodano utrwaloną oryginalną parę z artefaktu 13001380925 i test negatywny rzeczywistego przemieszczenia o 0.03 mm. Istniejące testy budżetu naprawy nadal wymagają odrzucenia nieudowodnionego wyniku; uwzględniają teraz poprzedzającą naprawę próbę pełnego dowodu.

## CADdiff

Sprawdzono oryginalne źródła z załącznika, bez zmiany algorytmu. FreeCAD 1.0, natywny moduł Part. Na obu oryginalnych plikach OpenArm pipeline kończy raport (kod 1 = wykryto różnice), ale ma 0 kandydatów geometrii, 100 dodanych i 77 usuniętych kluczy BOM. Nie sprawdza problematycznej osłony, ponieważ nazwy nie zostały sparowane. Nie jest to potwierdzenie poprawnej analizy różnic materiału.

Test negatywny: zewnętrzny klocek 20×20×10 mm z okrągłym otworem R2 oraz klocek z kwadratowym otworem o tej samej powierzchni. Objętość, gabaryty i położenie zgodne; CADdiff classify_change zwraca identical. Natywna różnica symetryczna wynosi 22.7566840328 mm³. Nie skopiowano tej reguły ani silnika do DSCompare.

## Kwantflow i pozostałe rozwiązania

Przejrzano konfigurację Svelte 5/Tauri 2, cad-loader, cad-viewer i organizację usług Kwantflow (GPL-3.0-only). Nową warstwę napisano niezależnie; kod GPL nie był kopiowany. Zastosowano organizację zadań w oddzielnym procesie, widoki robocze, spójną paletę i ustawienia z dokładnymi wartościami. Occt-import-js dostarcza podgląd siatek, nie dowód porównania brył; nie zastępuje dotychczasowego silnika.

FreeCAD służy do niezależnej weryfikacji CADdiff. DSCompare korzysta z natywnego OCCT przez OCP. Innych programów porównujących nie deklarujemy jako przetestowanych.

## Desktop 04

Źródła w desktop/. Frontend Svelte 5 i natywna granica procesu Tauri 2. Windows installer jest osobnym zadaniem CI i musi być oceniony osobno od udanego builda WWW i testów biblioteki Rust. Nie zastępujemy istniejącego EXE niezweryfikowaną kompilacją.

Dostępne: wybór rewizji, zamiana A/B, porównanie, anulowanie drzewa procesów, decyzje dotyczące wyrównania i niepełnej analizy, raporty HTML i 3D, CSV/STEP/BOM, lista z filtrowaniem i szczegółami, zapis ustawień, masa wielu plików, diagnostyka. Pełny dowód geometrii pozostaje w procesie silnika. Przeglądarka WWW jawnie wyłącza funkcje wymagające aplikacji desktopowej.
