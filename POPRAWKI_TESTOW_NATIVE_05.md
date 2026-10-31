# RC9 / Native 05 — Desktop 0.4.2

## Powtarzalny błąd V2 revision_shift

Run41120964432 / job124288946877 zatrzymuje się na Common A[162]/B[162], M3 Threaded Insert (2):6. Obie bryły są poprawne, po129 ścian; objętości39.288838276/39.266820599mm³. Środki różnią się o około1.45mm, a zapisane ustawienia CAD zawierają również obrót. Filtr objętości/momentów odrzucał tę parę zanim wykonano dowód geometrii.

Pełne sprawdzenie oryginalnych powierzchni i wszystkich krawędzi po zastosowaniu właściwego obrotu/przesunięcia z lokalizacji CAD potwierdza zgodność przy0.01mm. Pozycja powinna być MOVED. Nie wolno wyciągać tego wniosku z nazwy, gabarytów czy samego położenia.

W już zweryfikowanym dużym układzie złożenia rozszerzono wybór kandydatów na podstawie powierzchni. Jest to tylko filtr wyszukiwania. Izolowany proces proponuje właściwą transformację z metadanych CAD i wymaga pełnego dowodu oryginalnych granic; dopiero wtedy akceptuje MOVED. Nie zwiększono tolerancji. Rzeczywiste powiększenie bryły5% jest odrzucane. Niejednoznaczne przypisania wielu wystąpień nadal pozostają UNCERTAIN.

Dodano oryginalną parę z artefaktu13009797583 i test całego dopasowania w złożeniu601 wystąpień: wynik600 SAME +1 MOVED, bez zgadywanych zmian materiału.

## Sporadyczna awaria Windows

Starszy run41116925092 / V2 shift zakończył się AV3221225477 podczas zachowywania diagnostyki B-Rep. Ten sam silnik przeszedł ten scenariusz w kolejnym run41120964432, więc przyczyna nie jest udowodniona. Nie deklarujemy jej zamknięcia na podstawie samego ponowienia.

Zastąpiono mostki Python/C++ strumieni plikowych w transporcie B-Rep i wyliczaniu lokalnych skrótów natywnym API OCCT przyjmującym nazwę pliku. Nie zmienia to geometrii ani warunków zgodności. Dodano test40 zapisów/odczytów rzeczywistej bryły w ścieżce Unicode, równolegle z odczytem metryk pamięci przez wątek diagnostyczny; na końcu pełny dowód granic przy0.000001mm. To kontrola transportu i ograniczenie ryzykownej granicy, nie dowód ustalonej przyczyny AV. Ocena stabilności wymaga ponownych testów Windows i dużych modeli.

## Wydanie

Kompletny DSCompare_RC9_KOMPLET_ZRODLA.zip obejmuje nowy silnik, Svelte5/Tauri2 w wersji0.4.2 i okno autora z oryginalnym animowanym logo. Główny workflow ponownie buduje silnik, testuje CAD i tworzy instalator z dokładnie tego samego źródła. Historyczny workflow instalatora0.4.1 pozostaje dostępny do ręcznego odtworzenia, z przypiętym wcześniejszym silnikiem; nie buduje bieżącego wydania.

OpenArm pozostaje jawnym raportem częściowym przy oryginalnej wadliwej osłonie i budżecie0.01mm. Nie przedstawiamy go jako pełnej analizy materiału.
