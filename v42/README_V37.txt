DS Compare V3.7 — Windows x64
Autor: Szymczyk Damian (O programie)

Instalacja: rozpakuj wszystkie pliki archiwum GitHub Actions razem. Uruchom DSCompareV3.exe. Nie usuwaj folderu _internal.

Nowy interfejs Qt: ciemny oraz jasny motyw, panele Przegląd, Porównanie, Podgląd 3D, Wyniki, Masa części i Ustawienia.

Podgląd 3D: zakładka Podgląd 3D -> wybierz Wynik kolorowy, Model A, Model B lub inny STEP -> Załaduj model 3D. Pierwsza siatka dla pliku powstaje w osobnym procesie i jest buforowana. Możesz zmienić szczegółowość siatki. Obracaj modelem myszą, przybliżaj kółkiem.

Podgląd to triangulacja geometrii, a nie edytowalny CAD. Nie zastępuje oryginalnych STEP i B-Rep.

Kolory STEP: przed uruchomieniem wybierz AP214IS (profil kompatybilności starszych CAD) lub AP242DIS. Program kontroluje kolory po eksporcie poprzez ponowny import. Nie można zagwarantować sposobu wyświetlania w konkretnym ZW3D/CADbro bez modelu testowego i instalacji odbiorcy.

Wyniki: katalog z PODSUMOWANIE.json, ZMIANY.csv, BOM_A.csv, BOM_B.csv, raport HTML, POROWNANIE_KOLORY.step i DIAGNOSTYKA_KOLOROW.json.

Komenda ZW3D: most DLL pozostaje eksperymentalny, wspiera ~DSCOMPARE_A, ~DSCOMPARE_B, ~DSCOMPARE. Zachowaj kopię poprzedniej DLL. Nie wykonuj prób na niezapisanych projektach.

Wymagania: Windows 64-bit, graficzny sterownik z OpenGL obsługiwanym przez VTK; Qt i VTK są dołączone do programu. W przypadku braku akceleracji GPU wynikowe modele można nadal analizować przez STEP/CSV/HTML.
