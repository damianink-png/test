from __future__ import annotations
import csv,html,json,re
from pathlib import Path
from collections import defaultdict,Counter
from .step_io import export_colored_step, export_differences_step, inspect_step_colors, COLORS
from .compare import Record

STATUS_PL={'SAME':'Bez zmian','RENAMED':'Bez zmian — zmieniona nazwa',
 'MOVED':'Zmiana położenia/obrotu','CHANGED':'Zmieniona geometria','ADDED':'Nowy',
 'REMOVED':'Usunięty','UNCERTAIN':'Wymaga weryfikacji'}

# Csv z separatorem ; i przecinkiem dziesiętnym: polski Excel nie zamienia mas na daty.
# Nie wolno zmieniać wartości na sztuczny tekst z apostrofem – masa ma być liczbą.
from .names import technical

def is_technical_label(value):return technical(value)

def visible_name(name, path=''):
    original = str(name or '').strip()
    if not is_technical_label(original):
        return original
    bits = [p.strip() for p in str(path or '').replace('\\','/').split('/') if p.strip()]
    # Wybierz najbliższą rzeczywistą nazwę komponentu, a nie tag OCAF/STEP.
    valid = [v for v in reversed(bits) if not is_technical_label(v)]
    if valid:
        candidate = valid[0]
        if candidate.casefold().endswith('_asm') and len(valid) > 1:
            candidate = valid[1]
        return candidate
    return 'Element bez nazwy'

def visible_path(path):
    return '/'.join(visible_name(part) for part in str(path or '').replace('\\','/').split('/') if part)

def _fmt(v):
    return '' if v is None else round(float(v),4)

def _csv_value(value):
    if value is None:
        return ''
    if isinstance(value, float):
        return format(value, '.8f').rstrip('0').rstrip('.').replace('.', ',')
    if isinstance(value, int):
        return str(value)
    value = str(value)
    # Numery części 0424... nie mogą stracić początkowego zera w Excelu.
    if re.fullmatch(r'0[0-9]{3,}', value):
        return '="' + value + '"'
    # Excel/arkusze: zabezpieczenie przed wykonaniem formuły z nazw dostawcy.
    if value and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')):
        return "'" + value
    return value

def write_csv(path,headers,rows):
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f,delimiter=';',quoting=csv.QUOTE_MINIMAL)
        w.writerow(headers)
        for row in rows:
            w.writerow([_csv_value(v) for v in row])

def geometry_groups(parts,progress=None):
    """Group only B-Rep-proven rigid equivalents, independent of STEP labels."""
    from .geometry import signature,equivalent_rigid
    import io,hashlib
    from OCP.BRepTools import BRepTools
    from OCP.TopLoc import TopLoc_Location
    groups=defaultdict(list);exact={}
    for index,part in enumerate(parts):
        if progress and index%25==0:progress(f'BOM: grupowanie {index}/{len(parts)} brył')
        # Exact serialized local B-Rep is stronger than the approximate signature.
        # This also recognizes separate STEP definitions of the same geometry.
        stream=io.BytesIO()
        BRepTools.Write_s(part.shape.Located(TopLoc_Location()),stream)
        digest=hashlib.sha256(stream.getvalue()).digest()
        if digest in exact:
            exact[digest].append(index)
            continue
        buckets=groups[signature(part)]
        for items in buckets:
            first=parts[items[0]]
            try:same=part.shape.IsPartner(first.shape) or equivalent_rigid(first,part)[0]
            except Exception:same=False
            if same:
                items.append(index);exact[digest]=items;break
        else:
            items=[index];buckets.append(items);exact[digest]=items
    return [items for buckets in groups.values() for items in buckets]

def _bill(parts,density,group_indices=None):
    rows=[]
    for ids in (geometry_groups(parts) if group_indices is None else group_indices):
        items=[parts[i] for i in ids];first=items[0]
        names=[visible_name(x.name,x.path) for x in items]
        name=next((n for n in names if n!='Element bez nazwy'),'Element bez nazwy')
        unit=first.volume*1e-9*density
        rows.append((name,len(items),round(first.volume,4),round(unit,5),
                     round(sum(x.volume for x in items)*1e-9*density,5),visible_path(first.path)))
    return sorted(rows,key=lambda x:(x[0],x[2]))


def produce(folder,a,b,records,density=7850.,generate_step=True,colors=None,
            diff_step=True,tolerance=0.01,progress=None, preview3d=False):
    out=Path(folder);out.mkdir(parents=True,exist_ok=True)
    for name in ('POROWNANIE_KOLORY.step','ROZNICE_BREP.step','DIAGNOSTYKA_KOLOROW.json','BŁĄD_EKSPORTU_STEP.txt','UWAGI_ROZNICE_BREP.txt','DETAL_ROZNICE.csv'):
        (out/name).unlink(missing_ok=True)
    rows=[]
    for r in records:
        old=a[r.a_index] if r.a_index is not None else None
        new=b[r.b_index] if r.b_index is not None else None
        rows.append([STATUS_PL[r.status],visible_name(old.name,old.path) if old else '',
                     visible_name(new.name,new.path) if new else '',
                     visible_path(old.path) if old else '',visible_path(new.path) if new else '',
                     _fmt(r.delta_x),_fmt(r.delta_y),_fmt(r.delta_z),_fmt(r.distance_mm),
                     _fmt(r.volume_delta_mm3),r.note,_fmt(r.rotation_deg),r.confidence])
    headers=['Rodzaj zmiany','Nazwa A','Nazwa B','Ścieżka A','Ścieżka B',
             'Różnica X [mm]','Różnica Y [mm]','Różnica Z [mm]','Przesunięcie środka [mm]',
             'Różnica objętości [mm³]','Uwagi','Obrót dopasowania [°]','Pewność dopasowania']
    write_csv(out/'ZMIANY.csv',headers,rows)
    groups_a=geometry_groups(a,progress);groups_b=geometry_groups(b,progress)
    bom_a=_bill(a,density,groups_a);bom_b=_bill(b,density,groups_b)
    for role,parts,groups in [('A',a,groups_a),('B',b,groups_b)]:
        mapping=[{'ilosc':len(ids),'wystapienia':[{'index':i,'name':parts[i].name,'path':parts[i].path} for i in ids]} for ids in groups]
        (out/f'BOM_GRUPY_{role}.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
    bh=['Nazwa','Ilość','Objętość jednej sztuki [mm³]','Masa jednej sztuki [kg]','Masa łączna [kg]','Ścieżka w złożeniu']
    write_csv(out/'BOM_A.csv',bh,bom_a)
    write_csv(out/'BOM_B.csv',bh,bom_b)
    total_a=sum(s.volume*density*1e-9 for s in a)
    total_b=sum(s.volume*density*1e-9 for s in b)
    counts=Counter(x.status for x in records)
    palette={**COLORS,**(colors or {})}
    def hex_color(key):
        return '#' + ''.join(f'{round(min(1.,max(0.,c))*255):02x}' for c in palette[key])
    body=''.join('<tr>'+''.join('<td>'+html.escape(_csv_value(v) if isinstance(v,(int,float)) else str(v))+'</td>' for v in row)+'</tr>' for row in rows)
    th=''.join('<th>'+html.escape(x)+'</th>' for x in headers)
    status=' '.join(f'{STATUS_PL[k]}: {v}' for k,v in sorted(counts.items()))
    def pl_float(value, places=3):
        return f'{value:.{places}f}'.replace('.', ',')
    legend=''.join(f'<span><i class="dot" style="background:{hex_color(k)}"></i>{html.escape(STATUS_PL[k])}</span>' for k in ('SAME','RENAMED','MOVED','CHANGED','ADDED','REMOVED','UNCERTAIN'))
    htmltxt=f'''<!doctype html><html lang="pl"><head><meta charset="utf-8">
<title>DS Compare — raport porównania modeli</title>
<style>body{{font:14px system-ui,sans-serif;max-width:1600px;margin:32px auto;padding:0 18px;background:#101820;color:#e6edf4}}h1{{font-size:26px}}p{{line-height:1.55}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{border:1px solid #34465c;padding:7px;text-align:left;vertical-align:top}}th{{background:#29394b;position:sticky;top:0}}tr:nth-child(even){{background:#192638}}.panel{{background:#192638;border:1px solid #34465c;border-radius:10px;padding:18px;margin:16px 0}}.legend{{display:flex;gap:18px;flex-wrap:wrap}}.dot{{display:inline-block;width:13px;height:13px;border-radius:3px;margin-right:7px}}small{{color:#abbaca}}input{{padding:10px;width:100%;background:#24364b;color:white;border:1px solid #46607c;border-radius:5px;box-sizing:border-box}}</style></head><body>
<h1>DS Compare — raport porównania modeli</h1><div class="panel"><p><b>Wynik:</b> {html.escape(status)}</p><p><b>Liczba brył:</b> A = {len(a)}, B = {len(b)}</p>
<p><b>Masa A:</b> {pl_float(total_a)} kg &nbsp; <b>Masa B:</b> {pl_float(total_b)} kg &nbsp; <b>Różnica:</b> {pl_float(total_b-total_a)} kg</p>
<small>Przyjęta gęstość: {pl_float(density,1)} kg/m³ (jednakowa dla wszystkich brył), jednostka geometrii STEP: mm. Masa nie pochodzi z danych materiałowych ZW3D. BOM grupuje zgodną geometrię niezależnie od nazw. Nazwy i ścieżki wszystkich wystąpień są zapisane w BOM_GRUPY_A/B.json. Nie jest to natywna struktura złożeń.</small></div>
<div class="panel legend">{legend}</div>
<p><b>Uwaga:</b> prototyp testuje geometrię B-Rep za pomocą operacji Boolean, także po wyrównaniu sztywnym. Nie jest to porównanie historii operacji CAD ani bezpośredni odczyt pliku Z3. Niektóre symetryczne bryły i trudne modele STEP mogą wymagać ręcznej weryfikacji.</p>
<p>Pliki: ZMIANY.csv, BOM_A.csv, BOM_B.csv, POROWNANIE_KOLORY.step i ROZNICE_BREP.step (kolorowy model dodanego i usuniętego materiału, jeżeli eksport się powiedzie).</p>
<input id="search" placeholder="Filtruj zmiany: nazwa, status, uwagi" oninput="const q=this.value.toLowerCase();document.querySelectorAll('#table tbody tr').forEach(r=>r.style.display=r.innerText.toLowerCase().includes(q)?'':'none')">
<div style="overflow:auto;max-height:75vh"><table id="table"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div></body></html>'''
    (out/'RAPORT.html').write_text(htmltxt,encoding='utf-8')
    err=None;details={'written':False,'solids':0,'changes':[],'errors':[]}
    if generate_step:
        try:
            if progress:progress('Eksport podstawowego kolorowego STEP...')
            color_check=export_colored_step(str(out/'POROWNANIE_KOLORY.step'),records,a,b,colors)
            if progress:progress('Weryfikacja kolorów STEP po ponownym imporcie...')
            # Exporter already verified every face after reimport.
            (out/'DIAGNOSTYKA_KOLOROW.json').write_text(json.dumps(color_check,ensure_ascii=False,indent=2),encoding='utf-8')
            if progress:progress(f"Zapisano kolorowy STEP: {color_check['pokolorowane_etykiety']} brył i {color_check['pokolorowane_powierzchnie']} powierzchni ze stylem")
        except Exception as exc:
            err=str(exc)
            (out/'BŁĄD_EKSPORTU_STEP.txt').write_text(err,encoding='utf-8')
    if diff_step:
        try:
            if progress:progress('Tworzenie STEP z fragmentami dodanymi i usuniętymi...')
            details=export_differences_step(str(out/'ROZNICE_BREP.step'),records,a,b,tolerance,progress,colors=palette)
        except Exception as exc:
            details['errors'].append(str(exc))
    if details["errors"]:err=(err+"; " if err else "")+"Różnice materiału: "+"; ".join(details["errors"])
    preview_info=None
    if preview3d:
        try:
            if progress:progress('Generowanie niezależnego podglądu 3D w kolorze...')
            from .preview3d import create_preview
            preview_info=create_preview(out/'PODGLAD_KOLOROW_3D.html', records, a, b,
                                        colors=palette,progress=progress)
        except Exception as exc:
            (out/'UWAGI_PODGLAD_3D.txt').write_text(str(exc),encoding='utf-8')
            if progress:progress('Podgląd 3D niedostępny: '+str(exc))
    if details['changes']:
        write_csv(out/'DETAL_ROZNICE.csv',
            ['Nazwa A','Nazwa B','Usunięty materiał [mm3]','Dodany materiał [mm3]'],details['changes'])
    if details['errors']:
        (out/'UWAGI_ROZNICE_BREP.txt').write_text('\n'.join(details['errors']),encoding='utf-8')
    (out/'PODSUMOWANIE.json').write_text(json.dumps({'statuses':counts,'solids_A':len(a),'solids_B':len(b),
                        'colors_hex':{k:hex_color(k) for k in palette},'density_kg_m3':density,'mass_A_kg':total_a,'mass_B_kg':total_b,
                        'step_export_error':err,'diff_step':details,'preview_3d':preview_info,'records':[vars(r) for r in records]},indent=2,ensure_ascii=False),encoding='utf-8')
    return out,err
