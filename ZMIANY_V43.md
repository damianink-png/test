# DS Compare V4.3 — rozwój V4.2

Zaimplementowano: bezstratny indeks przestrzenny kandydatów zmodyfikowanych części;
ręczne potwierdzanie niepewnych par UNCERTAIN i wiązanie par REMOVED + ADDED;
cofanie decyzji; atomowy zapis weryfikacji i CSV bez naruszania danych B-Rep.

Wybierz Wyniki -> wiersz niepewnej pary -> Potwierdź parę lub Połącz A+B.
Oryginalny wynik PODSUMOWANIE.json / ZMIANY.csv pozostaje bez zmian.
ZMIANY_WERYFIKACJA.csv oraz WERYFIKACJA_RECZNA.json zawierają adnotacje.
Kolory i statusy w scenie 3D nadal pochodzą wyłącznie z analizy automatycznej.
Przypisanie użytkownika oznacza tożsamość konstrukcyjną według operatora,
a NIE potwierdzoną równość geometrii B-Rep.

Przyspieszenie wynika z mniejszej liczby sprawdzanych kandydatów
w sytuacjach rozproszonych. Nie deklarujemy skrócenia obliczeń bez
kontrolowanego benchmarku na identycznych plikach i stanowisku.
Nie wykonano testów DLL ani wyświetlania kolorów w rzeczywistym ZW3D 2019.
