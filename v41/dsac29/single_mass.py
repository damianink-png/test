"""Analiza jednego modelu STEP: liczba brył, ilości części i masy z zadanej gęstości."""
from __future__ import annotations
import html
import json
from pathlib import Path
from .step_io import load_step
from .report import _bill, write_csv

CSV_HEADERS = ['Nazwa części', 'Ilość', 'Objętość jednej sztuki [mm³]',
               'Masa jednej sztuki [kg]', 'Masa łączna [kg]', 'Ścieżka w złożeniu']

def analyze_single(path, folder, density=7850.0, progress=None):
    if not (0 < float(density) <= 25000):
        raise ValueError('Gęstość musi być dodatnia i nie przekraczać 25 000 kg/m³')
    path = Path(path)
    if progress: progress('Odczytywanie geometrii STEP...')
    solids = load_step(str(path), progress=progress)
    if progress: progress('Obliczanie mas i przygotowywanie zestawienia...')
    rows = _bill(solids, density)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    write_csv(folder/'MASY_CZESCI.csv', CSV_HEADERS, rows)
    total = sum(x.volume*density*1e-9 for x in solids)
    summary = {'plik': str(path), 'gestosc_kg_m3': density,
               'liczba_bryl': len(solids), 'liczba_pozycji': len(rows),
               'masa_calosci_kg': round(total, 6)}
    (folder/'PODSUMOWANIE_MASY.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    def number(x, digits=4): return f'{x:.{digits}f}'.replace('.', ',')
    body=''.join('<tr>' + ''.join('<td>'+html.escape(number(v) if isinstance(v,float) else str(v))+'</td>' for v in row[:5])+'</tr>' for row in rows)
    page=f'''<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>DS Compare — analiza masy</title>
<style>body{{background:#10141b;color:#f0f3f7;font:14px Segoe UI,Arial,sans-serif;max-width:1300px;margin:36px auto;padding:0 22px}}
table{{width:100%;border-collapse:collapse}}th,td{{border-bottom:1px solid #344254;padding:11px;text-align:left}}th{{background:#243040}}
.card{{background:#1b2430;padding:22px;border-radius:12px;margin:24px 0}}</style></head><body>
<h1>DS Compare — analiza masy jednego modelu</h1><div class="card"><p><b>Model:</b> {html.escape(path.name)}</p>
<p><b>Liczba brył:</b> {len(solids)} &nbsp; <b>Pozycji BOM:</b> {len(rows)}</p>
<p><b>Masa całkowita:</b> {number(total,3)} kg &nbsp; <b>Gęstość:</b> {number(density,1)} kg/m³</p>
<small>Masy wyliczono z objętości brył i jednej zadanej gęstości. Nie odczytano materiałów z ZW3D.</small></div>
<table><thead><tr>{''.join('<th>'+html.escape(h)+'</th>' for h in CSV_HEADERS[:5])}</tr></thead><tbody>{body}</tbody></table></body></html>'''
    (folder/'RAPORT_MASY.html').write_text(page, encoding='utf-8')
    if progress: progress(f'Gotowe: {len(solids)} brył, {len(rows)} pozycji, {total:.3f} kg')
    return folder, summary
