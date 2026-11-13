# Analiza raportów 0.6.17 i zmiany 0.6.18

Źródło: DSCompare_1794556564606096400.zip, raporty dwóch analiz przesłane przez użytkownika. Porównywana wersja: commit 6ec90ad3e45cb9b17e9244f4458b00ad60ac2e1f.

## Ustalenia z raportów

| Etap | Oryginalne położenie | Przesunięcie i eksport ZW3D |
| --- | ---: | ---: |
| Bryły A / B | 380 / 560 | 380 / 554 |
| Całość | 237,681 s | 661,862 s |
| Import równoległy | 12,081 s | 25,543 s |
| Wyszukiwanie wyrównania | niepotrzebne | 226,182 s |
| Porównanie materiału | 112,642 s | 310,145 s |
| SAME | 232 | 178 |
| UNCERTAIN | 0 | 114 |

Wyrównanie w drugim raporcie zostało znalezione, zatwierdzone i zastosowane. Wektor B → A: (-129,999719; -280,000000; -410,000179) mm. Potwierdzono 41 z 48 próbek oraz 178 części w końcowym porównaniu. Nie jest to raport o niewykrytym przesunięciu.

Główne pozostałe problemy: nieprawidłowa topologia wyników Common/Cut oraz przekroczenia czasu weryfikacji B-Rep. Zmiana eksportera zmieniła reprezentację: 554 zamiast 560 brył w B i 2712 powierzchni poza bryłami w B. Z samych raportów nie można rozstrzygnąć, czy utracono materiał, czy tylko inaczej zapisano strukturę. Program porównuje bryły SOLID.

## Wprowadzone zmiany

1. W selekcji powtarzających się części najpierw sprawdzana jest tania, konserwatywna obwiednia OCCT bez triangulacji. Rozłączne obwiednie nie uruchamiają kosztownego szukania dokładnych ekstremów powierzchni. Kandydaci z możliwym przecięciem nadal przechodzą dotychczasowe dokładne sprawdzenia.
2. Osobny cache obwiedni wstępnych, uwzględniający rzeczywistą geometrię, obrót, orientację i przesunięcie. Statystyki raportują obliczenia, trafienia i czas.
3. Po wyczerpaniu czasu pierwszego Common niezależna próba Common/Cut ma limit 30 s zamiast kolejnych 60–240 s. Pierwsza próba i odzyskiwanie po szybkim błędzie topologii zachowują dotychczasowe limity. Nieudane odzyskiwanie pozostawia wynik niepotwierdzony. Może to pozostawić UNCERTAIN dla bardzo kosztownej pary, którą dłuższa próba zdołałaby rozstrzygnąć.
4. Testy: konserwatywna obwiednia obróconej bryły, przeniesienie cache przy translacji, brak dokładnych ekstremów dla rozłącznych rodzin i limit niezależnej próby po timeout.

## Granice weryfikacji

Archiwum zawiera raporty i podglądy, ale nie źródłowe pliki STEP. Testy regresji weryfikują mechanizmy; nie zastępują ponownego porównania źródłowych modeli użytkownika. Nie ma podstaw, aby uznać wszystkie błędy ZW3D za naprawione ani podać zmierzony czas nowej wersji dla tych modeli. Automatyczne rozszerzanie wyszukiwania z 0.6.17 pozostaje aktywne.
