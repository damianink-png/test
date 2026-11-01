# DSCompare RC9 · Desktop 0.5.1

Aplikacja desktopowa Svelte 5 / Tauri 2 do porównywania rewizji STEP z odizolowanym silnikiem Python/OCCT.

Aktualne kompletne źródła: [DSCompare_DESKTOP_05_1_ZRODLA.zip](DSCompare_DESKTOP_05_1_ZRODLA.zip), identyczne z paczką `DSCompare_RC9_KOMPLET_ZRODLA.zip` używaną przez CI. ZIP zawiera sprawdzany manifest SHA-256. To źródła, nie skompilowany instalator.

Instalator Windows pobierz z artefaktu **DSCompare-Svelte5-Tauri2-Windows-installer** w udanym [przebiegu workflow](https://github.com/damianink-png/test/actions/workflows/rc9-corrected-real-cad.yml) dla aktualnego commita z PR. Numer wersji jest widoczny w „O programie”. Artefakt `RC9-large-current-Windows-x64` zawiera starszy interfejs Qt z aktualnym silnikiem.

Nowy przegląd wyników łączy listę części, model 3D i szczegóły. Obejmuje diagnostykę części, oddzielenie wyrównania całego złożenia od ruchu elementów, widok A/B ze wspólną kamerą, oryginalne położenie B, przekroje, postęp etapów i raporty z wyraźnym zakresem pełności.

Optymalizacja ponownie wykorzystuje ukończone dowody tylko dla dokładnie identycznych zapisów B-Rep i zgodnego położenia. Kontrola STEP korzysta z mapowania pliku, a scena HTML jest zapisywana fragmentami. W kontrolnym zestawie powtarzanych złączek: **21,27 s → 2,16 s**, te same 624 dopasowania. Wynik całych dużych złożeń wymaga nowego przebiegu Windows.

Szczegóły, pomiary i sposób uruchomienia kontroli: [REVIEW_WORKSPACE_06.md](REVIEW_WORKSPACE_06.md). Czytelne zmienione pliki: [review/fix06](review/fix06).

Poprzedni zweryfikowany Native05.1: 335 testów Windows, sześć scenariuszy V2/Trident, instalator i jawnie częściowy OpenArm — sukces w [run 41245568510](https://github.com/damianink-png/test/actions/runs/41245568510). OpenArm pozostaje testem raportu częściowego; nie oznacza potwierdzenia wszystkich różnic materiału. Tolerancja CAD pozostaje 0,01 mm.

Poprawka Windows 0.5.1: stabilny dziennik procesu sesji oraz osobne potwierdzenie zakończenia wszystkich zapisów zadania. Zapobiega kolizji usuwania plików tymczasowych (WinError 32), która przerwała V2 revision_shift w run 41278032537. [Opis i kontrole](POPRAWKA_SESJI_NATIVE_06_1.md), [czytelne pliki poprawki](review/fix061).
