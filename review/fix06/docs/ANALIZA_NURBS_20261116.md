# Raport diagnostyczny 0.6.20 — 16.11.2026

Źródło: DSCompare_1794809876682893200.zip. Raport schematu 2 jest kompletny i nie zawiera błędów inspekcji. SHA-256 obu modeli zgadza się z poprzednią analizą, więc odnosimy się do tej samej pary plików.

## Co wynika z danych

Model A: 380 brył, 110 definicji; model B: 554 bryły, 118 definicji. Wszystkie 4541 powierzchni zbadanych definicji modelu B mają typ BSplineSurface. Model A zawiera głównie płaszczyzny, cylindry, stożki, torusy, a także B-spline i powierzchnie wyciągnięcia.

Rodzina 04156745 / C04156745:
- 75 wystąpień w A i 109 w B;
- w obu definicjach 390 ścian, 1081 unikalnych krawędzi i 659 wierzchołków;
- identyczne raportowane lokalne granice wierzchołków;
- A: 137 cylindrów, 126 B-spline, 99 płaszczyzn, 22 torusy, 6 stożków;
- B: 390 B-spline;
- maksymalna tolerancja w obu: 0,009967966917 mm;
- po 24 krawędzie zdegenerowane; SameParameter i SameRange ustawione;
- uproszczona kontrola topologii nie wykazała błędów.

To silny sygnał zmiany reprezentacji, nie dowód identyczności całych brył. Raport nie zawiera sieci kontrolnych ani obrysów umożliwiających odtworzenie wszystkich operacji CAD. Kontrola topologii nie obejmuje pełnej walidacji geometrycznej.

Pozostałe pary z błędami Common są rzeczywistymi kandydatami zmian materiału: 04244002 ma 75 → 74 ściany, 04244004 ma 117 → 120, a 04244035 ma inne granice wierzchołków i objętość. Nie można uznać ich za SAME tylko po zamianie reprezentacji.

## Błąd algorytmu i poprawka 0.6.21

Dotychczasowa szybka ścieżka odrzuca różne typy powierzchni i krzywych. Odtworzono to na identycznym cylindrze: wersja analityczna i dokładna kopia NURBS nie przechodzą szybkiego testu, trafiając do kosztownych różnic Boolean.

Dodano izolowaną ścieżkę dla par o jednakowej strukturze topologicznej, ale różnych typach reprezentacji. OCCT NurbsConvert tworzy kopie we wspólnej reprezentacji NURBS, bez dopasowania siatki, naprawy czy przesuwania. Następnie wykonywany jest pełny test zorientowanych powierzchni i obrysów przy połowie tolerancji użytkownika. Konwersja sama nie stanowi dowodu zgodności. Sprawdzane są poprawność i zachowanie liczebności topologii. Błąd lub brak dowodu pozostawia dotychczasową weryfikację oryginalnych brył.

Testy obejmują oba kierunki analityczny/NURBS, rzeczywistą zmianę promienia, przesunięcie lokalne, zachowanie oryginalnych brył i położeń oraz użycie nowej ścieżki w izolowanym procesie zamiast Boolean. Dotychczasowe testy podziału powierzchni, powtórzeń i wyrównania są zachowane.

Nie potwierdzono jeszcze wyniku na bryłach użytkownika. Odmienne parametryzacje NURBS nadal mogą wymagać dotychczasowego sprawdzenia. Ta poprawka nie jest deklaracją naprawienia wszystkich czterech błędów zmienionego materiału Common/Cut.
