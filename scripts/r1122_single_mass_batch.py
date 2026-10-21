"""Batch mass estimates from several models with individual and combined reports.

Keep existing single-model algorithm intact: one load_step and grouping per
model. Total mass is a sum; identical items across *different* files are not
coalesced into a global unique BOM.
"""
from __future__ import annotations
import csv,html,json,re
from pathlib import Path

def analyze_many(paths, folder, density=7850.0, progress=None, max_solids=20000):
    from .single_mass import analyze_single
    from .z3_support import resolve_model
    if not isinstance(paths,list) or not paths or len(paths)>500:
        raise ValueError('Lista modeli musi zawierać od 1 do 500 plików')
    if not (0<float(density)<=25000):
        raise ValueError('Niepoprawna gęstość')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    seen=set();files=[]
    for raw in paths:
        if not isinstance(raw,str) or not raw.strip():
            raise ValueError('Nieprawidłowa ścieżka modelu')
        path=Path(raw).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in ('.step','.stp'):
            raise ValueError('Brak poprawnego pliku STEP/STP: '+str(path))
        key=str(path).casefold()
        if key in seen:continue
        seen.add(key)
        files.append(path)
    if not files:
        raise ValueError('Brak modeli do analizy')
    rows=[];entries=[]
    count_solids=0;count_bom=0;total=0.0
    headers=['Nazwa części','Ilość','Objętość jednej sztuki [mm³]',
             'Masa jednej sztuki [kg]','Masa łączna [kg]','Ścieżka w złożeniu']
    for index,path in enumerate(files,1):
        safe=re.sub(r'[^a-zA-Z0-9_-]+','_',path.stem)[:48] or 'model'
        item_dir=folder/'MODELE'/f'{index:03d}_{safe}'
        if progress:progress(f'[{index}/{len(files)}] Analiza modelu: {path.name}')
        _,data=analyze_single(str(path),item_dir,density,progress=progress,preview=False,max_solids=max_solids)
        count_solids+=int(data['liczba_bryl'])
        count_bom+=int(data['liczba_pozycji'])
        total+=float(data['masa_calosci_kg'])
        if count_solids>max_solids:
            raise ValueError(f'Łączna liczba brył przekracza limit {max_solids}; przerwano bez publikacji raportu zbiorczego.')
        with (item_dir/'MASY_CZESCI.csv').open(encoding='utf-8-sig',newline='') as stream:
            parts=list(csv.reader(stream,delimiter=';'))[1:]
        for fields in parts:
            if len(fields)<5:raise ValueError(f'Uszkodzony BOM: {path}')
            name=f'{path.name} / {fields[0]}'
            row=[name]+fields[1:]
            if len(row)<6:row+=['']*(6-len(row))
            rows.append(row[:6])
        entries.append({
            'plik':str(path),'nazwa':path.name,'masa_kg':float(data['masa_calosci_kg']),
            'liczba_bryl':int(data['liczba_bryl']),'liczba_pozycji':int(data['liczba_pozycji']),
            'raport':str((item_dir/'RAPORT_MASY.html').relative_to(folder)).replace('\\','/'),
            'folder':str(item_dir),
            'pominięte_powierzchnie':int(data.get('import_diagnostics',{}).get('faces_outside_solids',0)),
        })
    summary={'plik':f'Zestawienie zbiorcze ({len(files)} modeli)',
       'liczba_plikow':len(files),'liczba_bryl':count_solids,
       'liczba_pozycji':count_bom,'gestosc_kg_m3':float(density),
       'masa_calosci_kg':round(total,6),'modele':entries,
       'zastosowane_zalozenia':'Suma mas modeli; nie wykonano deduplikacji części pomiędzy oddzielnymi plikami',
       'import_diagnostics':{'faces_outside_solids':sum(e['pominięte_powierzchnie'] for e in entries)}}
    (folder/'PODSUMOWANIE_MASY.json').write_text(
        json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    with (folder/'MASY_CZESCI.csv').open('w',encoding='utf-8-sig',newline='') as fh:
        writer=csv.writer(fh,delimiter=';',lineterminator='\n');writer.writerow(headers);writer.writerows(rows)
    with (folder/'MASY_PLIKI.csv').open('w',encoding='utf-8-sig',newline='') as fh:
        writer=csv.writer(fh,delimiter=';',lineterminator='\n')
        writer.writerow(['Model','Ścieżka','Masa [kg]','Bryły','Pozycje BOM'])
        for e in entries:
            writer.writerow([e['nazwa'],e['plik'],f"{e['masa_kg']:.6f}",e['liczba_bryl'],e['liczba_pozycji']])
    table=''.join(
       '<tr><td>'+html.escape(str(i))+'</td><td>'+html.escape(e['nazwa'])+'</td>'
       +'<td>'+str(e['liczba_bryl'])+'</td><td>'+str(e['liczba_pozycji'])+'</td>'
       +'<td>'+f"{e['masa_kg']:.3f}"+'</td>'
       +'<td><a href="'+html.escape(e['raport'],quote=True)+'">Otwórz raport modelu</a></td></tr>'
       for i,e in enumerate(entries,1))
    details=''.join(
        '<details><summary>'+html.escape(e['nazwa'])+' — '+f"{e['masa_kg']:.3f} kg"+'</summary>'
        +'<p>Bryły: '+str(e['liczba_bryl'])+'; pozycje: '+str(e['liczba_pozycji'])+'</p>'
        +'<a href="'+html.escape(e['raport'],quote=True)+'">Szczegółowy BOM i raport</a>'
        +'</details>'
        for e in entries)
    report='''<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8"><title>DS Compare — zestawienie mas</title>
    <style>body{font:15px Segoe UI,Arial,sans-serif;background:#111821;color:#eaf1fa;max-width:1250px;margin:35px auto;padding:15px}
    table{border-collapse:collapse;width:100%}th,td{padding:12px;border-bottom:1px solid #334150;text-align:left}
    th{background:#202c3b}a{color:#78bdff}details,.box{padding:18px;background:#1c2735;border-radius:12px;margin:10px 0}
    summary{cursor:pointer;font-weight:600}</style></head><body>
    <h1>DS Compare — zbiorcze zestawienie mas</h1><div class="box">
    <p><strong>Modeli:</strong> '''+str(len(files))+''' &nbsp; <strong>Brył:</strong> '''+str(count_solids)+''' &nbsp;
    <strong>Pozycji BOM:</strong> '''+str(count_bom)+''' &nbsp; <strong>Łączna masa:</strong> '''+f'{total:.3f}'+''' kg</p>
    <p>Gęstość: '''+f'{float(density):.1f}'+''' kg/m³ · Sumowanie osobnych modeli bez deduplikacji między plikami.</p></div>
    <h2>Zestawienie modeli</h2><table><thead><tr><th>Lp.</th><th>Plik</th><th>Bryły</th><th>Pozycje</th><th>Masa [kg]</th><th>Raport</th></tr></thead><tbody>
    '''+table+'''</tbody></table><h2>Raporty szczegółowe</h2>'''+details+'''</body></html>'''
    (folder/'RAPORT_MASY.html').write_text(report,encoding='utf8')
    if progress:progress(f'Gotowe: {len(files)} modeli, {count_solids} brył, masa {total:.3f} kg')
    return folder,summary
