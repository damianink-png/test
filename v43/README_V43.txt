DS Compare V4.3 — dopasowywanie i bezpieczna ręczna weryfikacja

Nowości:
- Przyspieszono wyszukiwanie kandydatów zmodyfikowanych elementów bez gubienia części.
  Indeks po współrzędnych i wyszukiwanie binarne zastępują pełny przegląd reszty złożenia.
- W Wyniki: Potwierdź parę (dla UNCERTAIN z A+B), Połącz A + B (dla pojedynczych
  REMOVED/ADDED) i Cofnij decyzję.
- Oryginalne PODSUMOWANIE.json i ZMIANY.csv nigdy nie są modyfikowane decyzją użytkownika.
- Weryfikacja zapisana w WERYFIKACJA_RECZNA.json, eksport CSV do
  ZMIANY_WERYFIKACJA.csv. Potwierdzenie użytkownika NIE oznacza równości B-Rep.
- Decyzje powiązane z SHA256 wyników; po podmianie analizy odmowa zastosowania starych decyzji.
- Jeden element nie może być potwierdzony z dwiema różnymi częściami.
- Wybrane pary A/B nadal pozostają w pierwotnych wierszach i zachowują kolory
  automatycznego statusu sceny, aby nie udawać nowego porównania geometrii.

ZW3D: DLL x64 pozostaje eksperymentalna; zgodność z realnym ZW3D 2019
oraz kolorowanie w jego importerze wymagają sprawdzenia na stanowisku.
Aby uruchomić: rozpakuj wszystko, uruchom DSCompareV3.exe, zachowaj _internal.
