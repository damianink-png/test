# Diagnostyka TXT 0.6.20

Raport użytkownika z wersji 0.6.19 (commit 76a3a3f) nadal zawiera 114 pozycji UNCERTAIN. Wyrównanie B → A (-129,999719; -280,000000; -410,000179) mm jest potwierdzone końcowym porównaniem. 106 pozycji to 53 stare i 53 nowe wystąpienia rodziny 04156745 / C04156745, których test B-Rep nie został rozstrzygnięty. Pozostałe 8 pozycji dotyczy czterech par z nieudanym Common/Cut.

Dotychczasowa diagnostyka wykazała 75 wystąpień tej definicji w A i 109 w B. Nie jest to rodzina o jednakowej liczebności w obu rewizjach. Jej objętości wynoszą odpowiednio 12003,313365 i 12003,459601 mm³. Bliskość tych wartości nie dowodzi zgodności kształtu. Importowane obwiednie różnią się znacznie, lecz są konserwatywne i nie rozstrzygają, czy zmienił się detal, czy sposób reprezentacji jego geometrii.

Nowy DIAGNOSTYKA_MODELI.txt (report_schema=2) zachowuje dotychczasowe dane i dodaje:
- wersję silnika oraz SHA-256 każdego źródła;
- indeksy części i transformacje 3x4 każdego wystąpienia;
- liczbę ścian, krawędzi, wierzchołków, brył i powłok;
- typ, orientację, pole, środek i zakres UV każdej powierzchni;
- parametry powierzchni analitycznych;
- stopnie, liczby biegunów i węzłów, wymierność i okresowość spline;
- tolerancje ścian, krawędzi i wierzchołków;
- mapowanie krawędzi do ścian, szwy, degeneracje, SameParameter i SameRange;
- kontrolę topologii bez pełnej walidacji geometrycznej, z jawną informacją o zakresie;
- błędy inspekcji zamiast przerwania całego raportu.

Geometria jest opisywana raz na definicję; wszystkie jej wystąpienia mają osobne położenia. Raport nie wykonuje Common/Cut, napraw, triangulacji ani kosztownych dokładnych ekstremów spline. Nie zapisuje B-Rep, siatki ani współrzędnych biegunów spline. Częściowy raport jest aktualizowany atomowo co 10 definicji i po każdym modelu; complete oznacza ukończenie raportu, nie poprawność geometrii. has_inspection_errors sygnalizuje błędy odczytu danych CAD.

Po instalacji 0.6.20: Diagnostyka → te same modele A/B → Zapisz diagnostykę → Otwórz folder raportu. Do dalszej analizy wystarczy przesłać DIAGNOSTYKA_MODELI.txt. Nie jest potrzebny źródłowy STEP. Tekst nie zastępuje geometrii do odtworzenia każdej operacji OCCT, ale pozwoli wskazać konkretne różnice reprezentacji i ograniczenia algorytmu.
