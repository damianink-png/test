# RC9 / Native 05.1 — Desktop 0.4.3

Poprzednia poprawka potwierdzała dopasowanie przesuniętej wkładki M3, lecz pełna analiza nadal kończyła się błędem. Późniejsza klasyfikacja liczby wystąpień stosowała filtr objętości po pozytywnym pełnym dowodzie B-Rep i rozdzielała MOVED na REMOVED/ADDED. Teraz już potwierdzone definicje geometrii uczestniczą w liczeniu populacji niezależnie od tego filtra. Reguła jednakowej liczby wystąpień pozostaje zachowana.

Gdy populacja się zmienia, pozostają osobne wystąpienia stare i nowe. Etap materiału nie kieruje udowodnionych geometrycznie równych definicji do Common i nie zgaduje ich tożsamości. Wszystkie niepotwierdzone zmiany nadal wymagają natywnego Common/Cut.

Regresja obejmuje teraz pełny łańcuch compare → classify_revisions → merge_material_revisions na oryginalnej parze z artefaktu i złożeniu 601 wystąpień. Dodano kontrole dodatkowego wystąpienia i obowiązkowej operacji Common dla nieudowodnionej zmiany. Nie zwiększono tolerancji.

Nie deklarujemy lokalnego zaliczenia tej poprawki: środowisko wykonawcze stało się niedostępne. Kod i spójność źródeł sprawdzono przy przygotowaniu pakietu; pełne testy Windows, CAD i instalatora muszą zakończyć się osobno na GitHubie.

Poprzedni run41182141340: 333 testy Windows, budowanie instalatora, V2 shift, wszystkie scenariusze Trident, V2 bez przesunięcia i jawny raport częściowy OpenArm PASS; V2 revision_shift FAIL na M3. Ta aktualizacja naprawia utratę dowodu w dalszych etapach. Przyczyna wcześniejszej sporadycznej awarii Windows nie jest uznana za udowodnioną.

Autorytatywne bieżące źródła: DSCompare_RC9_KOMPLET_ZRODLA.zip. Czytelny przyrost zmian względem Native05: DSCompare_NATIVE_05_1.patch i review/fix051/. Starszy DSCompare_RC9_KOMPLET.patch opisuje bazę Native05; do instalacji używaj pełnego aktualnego pakietu.
