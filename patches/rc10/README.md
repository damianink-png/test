# RC10: powtarzające się detale i przesunięcie modeli

Poprawka dotyczy obu archiwów RC10 z `main` (bazowy commit
`0a70ff5d7b8819da0b5dd2bc612a3802e834431f`).

- Common pomija powtarzającą się geometrię w dowolnej rewizji. Liczona jest
  cała lista, również wystąpienia wcześniej dopasowane, niezależnie od nazwy
  i położenia. Wspólna definicja lub zgodne deskryptory fizyczne wykluczają
  automatyczne łączenie; deskryptory nie stanowią dowodu równości geometrii.
- Niepotwierdzone heurystyczne pary powtarzających się detali są rozdzielane
  na REMOVED + ADDED. Potwierdzone SAME/MOVED oraz błędy B-Rep zachowują
  swoje znaczenie. Przy błędzie testu nie deklarujemy usunięcia/dodania.
- Próbowanie przesunięć używa próbek uporządkowanych przestrzennie zamiast
  kolejności STEP, obsługuje złożenie jednobryłowe i nie zatwierdza wyniku,
  jeśli limit przerwał weryfikację nadal konkurencyjnych przesunięć.

## Użycie

Rozpakuj jedno archiwum RC10 i wykonaj z katalogu repozytorium:

```text
python patches/rc10/apply_patch.py KATALOG_Z_DSAC29
```

Następnie użyj standardowego `BUDUJ_WINDOWS.ps1`. Skrypt sprawdza SHA-256
wszystkich bazowych plików przed zapisem; ponowne zastosowanie jest dozwolone.
Oba workflow RC10 stosują poprawkę przed kompilacją.

## Weryfikacja

Nowe testy odtwarzają mieszaną klasyfikację 4 + 4 w grupie ośmiu kopii,
osobne i współdzielone definicje B-Rep, różne nazwy, pełne populacje,
przesunięcie globalne, ruch lokalny, zmianę kolejności STEP i limit hipotez.
Test eksportu materiału używa teraz trzech różnych geometrii, ponieważ
automatyczny Common dla powtarzających się geometrii jest celowo wyłączony.

Walidacja odbywa się na bryłach Open CASCADE. Pliki STEP zgłaszanego przez
użytkownika przypadku nie są dostępne; nie potwierdzono jego konkretnego
wyniku ani nowego EXE dla Windows.
