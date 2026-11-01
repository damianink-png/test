# Desktop 0.4.1 — O programie

Nowy interfejs Svelte 5/Tauri 2 ma przycisk „O programie” w lewym panelu. Okno zawiera autora Damian Szymczyk, oryginalne logo A/B, wersję z package.json, formaty i informacje o technologii.

Logo składa się z dwóch połówek, następnie przechodzi krótki skan. Animacja trwa około 2 sekund i zatrzymuje się; można ją powtórzyć. Ustawienie systemowe prefers-reduced-motion wyłącza animacje. Okno działa w obu motywach, w małej rozdzielczości, obsługuje Esc, przycisk zamykania i przywrócenie fokusu.

Sprawdzone: svelte-check bez błędów/ostrzeżeń, build produkcyjny, testy przeglądarkowe autora/logo/wersji/ponowienia animacji/zamykania/motywów/ograniczenia ruchu/1000×680, bez błędów JavaScript.

Kompletny pakiet źródeł tej wersji: DSCompare_DESKTOP_04_1_ZRODLA.zip. Osobny workflow desktop-interface.yml buduje instalator 0.4.1. Silnik nie uległ zmianie: źródła sprawdzane względem commita 6c055339129bf71ebd1d9af585ee88d87253509a, a dołączany pakiet pochodzi z niezmiennego artefaktu 13007565110 (328 testów Windows PASS). Duże testy CAD tego silnika należy oceniać osobno w run 41116925092.

Starszy instalator Tauri 0.4.0 i paczka Qt ~184 MB nie zawierają tego nowego okna Svelte.
