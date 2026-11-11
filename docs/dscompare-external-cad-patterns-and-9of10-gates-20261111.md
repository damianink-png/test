# DS Compare — audyt rozwiązań CAD i bramki dojrzałości (2026-11-11)

Zakres: wyłącznie porównanie STEP/B-Rep, bez zmiany UI i bez obniżania tolerancji klasyfikacji.

## Wzorce z innych programów

- **Ansys Workbench — Compare Parts on Update:** tryb asocjacyjny zachowuje powiązania przy przeorganizowaniu brył, gdy porównywanie według indeksu może zawodzić. W DS Compare XCAF source-scoped definitions służą **do priorytetyzacji i ponownego wykorzystania identycznej definicji**; wynik nadal wymaga dokładnego dowodu B-Rep i sprawdzenia położenia. Źródło: https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/pdf/CAD_Integration.pdf
- **Open CASCADE XDE/STEPCAF:** STEP może zachować definicje, instancje, lokalizacje, kolory i nazwy. W DS Compare opłaca się liczyć **definicje**, nie wszystkie wystąpienia, i pisać jeden produkt na identyczną geometrię/kolor. Źródło: https://github.com/Open-Cascade-SAS/OCCT/blob/master/dox/user_guides/step/step.md
- **Analysis Situs:** tolerancje lokalne B-Rep mogą różnić się między krawędziami i powierzchniami; siatka wizualna nie jest dowodem identyczności. Stąd `Unknown` pozostaje nierozstrzygnięte, a przekwalifikowanie na SAME/CHANGED/MOVED wymaga natywnego potwierdzenia. Źródło: https://www.analysissitus.org/features/features_check-toler.html
- **CADfix 3D Diff / Glovius:** wyróżniaj dodany i usunięty materiał, ale dopiero po poprawnym dopasowaniu referencji. W DS Compare utrzymujemy walidowane Common/Cut bez dorabiania w UI dodatkowych opcji. Źródła: https://www.cadinterop.fr/en/your-needs/cad-data-reuse-for-cae/3d-diff-tool-to-compare-cad-and-mesh-versions-and-identify-changes-in-cadfix.html i https://www.glovius.com/support/online-help/compare-3d-cad-files/

## Wdrożenie w tej iteracji

1. `occurrence_identity.prepare_occurrence_identities`: gdy liczba wystąpień przekracza 3500, limit dotyczy teraz niezależnych kosztownych definicji (XCAF key = plik + etykieta docelowa + indeks bryły), a nie wszystkich jej wystąpień. Brak klucza nadal kosztuje jeden slot na bryłę; przekroczenie limitu nie oznacza zgadywania, tylko stary bezpieczny fallback natywny.
2. Regresje: znaczna liczba wystąpień dwóch definicji XCAF, znaczna liczba brył bez klucza i te same numery etykiet z różnych plików. Każdy pozytywny digest nadal powstaje z pełnego B-Rep.
3. CI: rzeczywiste zgięte/blaszane STEP i Trident uruchamiają się po zmianach w dowolnym używanym module `review/fix06/dsac29/**`, patchach silnika oraz `portable/assemble_engine.py`, a nie tylko po zmianach kilku wybranych modułów. Wyniki tych oddzielnych workflow muszą być odczytywane dla tego samego SHA co OneEXE.

## Wymagania do oceny 9/10 — nie są jeszcze zaliczone

| Obszar | Kryterium zatwierdzenia |
| --- | --- |
| OneEXE/Windows | CI bez błędów, porównanie SHA-256 testowanego silnika z dołączonym do EXE, uruchomienie w natywnej sesji Windows i test na docelowym komputerze |
| Regresje | Wszystkie testy CAD, w tym negatywne no-false-SAME/CHANGED/MOVED oraz brak powtórzenia kosztownego Native bez nowej hipotezy, zielone na końcowym SHA |
| Powtórzenia | Realne i syntetyczne grupy 150, 3500+ wystąpień, rozdzielone definicje XCAF, zmiana pojedynczej kopii i brak domyślnego fałszywego Common |
| CHANGED | Poprawne orakle dla rzeczywistych detali giętych, wielu zmian i różnych liczności, bez nieuzasadnionego CHANGED |
| Wyrównanie | Realne translacje, lokalnie przeniesione elementy, rotacja, rewizja geometrii; zerowe fałszywe globalne przesunięcia |
| Czas i STEP | Porównanie cold/warm na identycznych rzeczywistych plikach, liczba Common/Cut, użycie RAM i rozmiar STEP z odczytem w ZW3D 2019; bez regresji jakości/kolorów |

**Uwaga:** powodzenie kompilacji OneEXE nie zastępuje pełnych testów dwóch autentycznych rewizji STEP wykonanych na tym samym commicie. Nie podnosimy ocen do 9/10 automatycznie.
