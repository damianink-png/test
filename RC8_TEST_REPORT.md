# DS Compare R22.3 RC8 — stan testów

Kod kompilacji: c3c08ce84e4689c636c1f196e7bb83a826abf74e.
Workflow: https://github.com/damianink-png/test/actions/runs/40277943613

## Zmiana
Po potwierdzeniu globalnego wyrównania B→A aplikacja zapisuje `_WYROWNANY_STEP/B_WYROWNANY.step`, importuje go bez bufora importu, odtwarza metadane przez jednoznaczne ID wystąpień i wykonuje porównanie od nowa. Nie używa starych dowodów ani ponownego wyszukiwania przesunięcia. Dla modeli bez potwierdzonego przesunięcia nie zapisuje dodatkowego STEP.

Naprawiono błąd odtwarzania metadanych po zmianie numerycznie wyliczonej objętości/środka masy podczas STEP round-trip. ID nie jest dowodem zgodności geometrii. Zachowano pełną kontrolę powierzchni i krawędzi oraz izolację kosztownych testów dla dużych złożeń. Osobne wystąpienia identycznych brył w tym samym miejscu nie giną. Progi końcowej akceptacji geometrii i timeout Common nie zostały zwiększone.

## Potwierdzone
- Windows x64: kompilacja i smoke test UI PASS.
- Windows: 209 regresji PASS (55.29 s), 11 dodatkowych testów PASS (2.21 s).
- Linux OCP 7.8: 209 regresji PASS (42.48 s), 18 testów restartu/wyrównania PASS (3.82 s).
- Cztery rzeczywiste pary z diagnostyki Trident (3,18,53,81): nowy STEP, reimport, pełny test powierzchni/krawędzi PASS; świeże compare: SAME=4 (14.42 s). To test wybranych brył w Pythonie, NIE zastępstwo pełnych testów EXE.

## Duże złożenia — stan przy zapisaniu raportu
| Model | Scenariusz | Stan |
|---|---|---|
| Voron V2 | przesunięta kopia | w toku |
| Voron V2 | rewizja z przesunięciem | w toku |
| Voron V2 | rewizja bez przesunięcia | w toku |
| Trident | przesunięta kopia | kolejka |
| Trident | rewizja z przesunięciem | kolejka |
| Trident | rewizja bez przesunięcia | kolejka |

Nie potwierdzono jeszcze sześciu PASS. Czasy i klasyfikacja pełnych modeli nie są obecnie dostępne. Aktualny status jest w workflow, diagnostyka zostanie opublikowana także przy błędzie. ZW3D 2019 nie był uruchamiany.

## Pliki
- EXE: https://github.com/damianink-png/test/actions/runs/40277943613/artifacts/12631450292
- Pełne źródła po zastosowaniu poprawek: https://github.com/damianink-png/test/actions/runs/40277943613/artifacts/12630579493

To wersja testowa, nie deklaracja ukończenia pierwotnego kryterium stabilności.
