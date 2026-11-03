from __future__ import annotations
import csv,html,json,re
from time import perf_counter
from pathlib import Path
from collections import defaultdict,Counter
from .step_io import export_colored_step, export_revision_step, REVISION_COLORS, export_differences_step, inspect_step_colors, COLORS
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

def geometry_groups(parts, progress=None, report_progress=None, context=None, tolerance=0.01, known_groups=None, fast_proven_only=False, time_budget_s=28):
    """Exact BOM grouping with O(1) native-definition and B-Rep lookup.

    - STEP occurrences of the same native definition: definitive identity.
    - Different definitions: identical local B-Rep serialization is proof.
    - Remaining candidates: the ORIGINAL strict rigid B-Rep test is retained.
      Numeric features index candidates; they never decide geometry equality.
    """
    from .geometry import signature, candidate
    from .geometry_registry import GeometryRegistry
    context = context if context is not None else GeometryRegistry()
    deadline=perf_counter()+max(5,float(time_budget_s))
    budget_exceeded=False
    buckets = defaultdict(list)    # geometric candidate signatures -> group indices
    by_definition = {}              # verified native TShape identity -> group
    by_digest = {}                  # exact B-Rep digest + candidate signature -> group
    groups = []
    total = len(parts)
    seeded=set()
    for seed in known_groups or []:
        if not seed:continue
        if any(i in seeded or not 0<=i<total for i in seed) or len(set(seed))!=len(seed):
            raise ValueError('Nieprawidłowe przypisanie potwierdzonych grup BOM')
        group_index=len(groups);groups.append(list(seed));seeded.update(seed)
        buckets[signature(parts[seed[0]])].append(group_index)
        for i in seed:by_definition[context.definition(parts[i])]=group_index
    for index, part in enumerate(parts):
        if progress and index % 25 == 0:
            progress(f'BOM: grupowanie {index}/{total} brył; unikalnych: {len(groups)}')
        if report_progress and (index % 10 == 0 or index == total-1):
            report_progress(index+1, total)
        if index in seeded:continue
        definition = context.definition(part)
        matched = by_definition.get(definition)
        if matched is not None:
            groups[matched].append(index)
            continue
        sig = signature(part)
        # Do not serialize B-Rep of a unique shape if no other geometry in
        # its invariant bucket can possibly match. Heavy STEP assemblies may
        # contain large one-off solids; writing their B-Rep gains nothing.
        if perf_counter()>deadline and not budget_exceeded:
            budget_exceeded=True
            context.stats['bom_budget_exhausted']+=1
            if progress:progress('BOM: przekroczono limit dokładnego grupowania; pozostałe unikalne definicje zachowano jako osobne pozycje.')
        possible = [] if budget_exceeded else [group_index for group_index in buckets.get(sig, ())
                    if candidate(parts[groups[group_index][0]], part, tolerance)]
        digest = None
        if possible:
            # The first occurrence of a definition is hashed only once an
            # independent compatible candidate appears; cached across A/B.
            digest = context.exact_digest(part)
            if digest is not None:
                matched = by_digest.get((sig, digest))
            if matched is None:
                for group_index in possible:
                    first = parts[groups[group_index][0]]
                    if fast_proven_only:
                        # Equality of two independent local B-Rep serializations
                        # proves identity. Numeric signatures or a shared name DO NOT.
                        # Rotated but equivalent independent definitions may remain
                        # separated: fast BOM is explicitly not exhaustive.
                        other = context.exact_digest(first)
                        if digest is not None and other is not None and digest == other:
                            matched = group_index
                            break
                        context.stats['bom_inconclusive_fast_pairs'] += 1
                        continue
                    # One native OCC check can exceed the nominal group
                    # deadline. If it does, do not launch MORE such checks.
                    before_check=perf_counter()
                    try:
                        if context.rigid_equivalent(first, part, tolerance):
                            matched = group_index
                            break
                    except Exception as exc:
                        context.bom_errors.append({'part':part.name,'candidate':first.name,'error':str(exc)})
                        if progress:
                            progress(f'BOM: porównanie B-Rep niepowodzenie {index}/{groups[group_index][0]}: {exc}')
                        # A failure must never turn into an assumed match.
                    finally:
                        if perf_counter()-before_check>3.0 or perf_counter()>deadline:
                            if not budget_exceeded:
                                budget_exceeded=True
                                context.stats['bom_budget_exhausted']+=1
                                if progress:progress(
                                  'BOM: wolne sprawdzanie B-Rep — pominięto dalsze niepotwierdzone grupowanie.')
                            break
        if matched is None:
            matched = len(groups)
            groups.append([])
            buckets[sig].append(matched)
        groups[matched].append(index)
        by_definition[definition] = matched
        if digest is not None:
            by_digest[(sig, digest)] = matched
    if report_progress:
        report_progress(total,total)
    if progress:
        progress(f'BOM: {len(parts)} wystąpień, {len(groups)} grup; '
                 f'natywne={context.stats["native_definition_hits"]}, '
                 f'B-Rep={context.stats["rigid_brep_checks"]}, '
                 f'cache={context.stats["rigid_cache_hits"]}')
    return groups


def reuse_verified_bom_groups(groups_a, records, count_a, count_b):
    """Transfer proven A grouping through a complete one-to-one SAME mapping.

    This is deliberately conservative: moved, changed, added, removed and
    uncertain records force independent grouping of revision B.
    """
    if count_a != count_b:
        return None
    a_to_b = {}
    seen_b = set()
    for record in records:
        ai, bi = record.a_index, record.b_index
        if (record.status not in ('SAME', 'RENAMED') or ai is None or bi is None
                or ai in a_to_b or bi in seen_b or not 0 <= ai < count_a
                or not 0 <= bi < count_b):
            return None
        a_to_b[ai] = bi
        seen_b.add(bi)
    if len(a_to_b) != count_a or len(seen_b) != count_b:
        return None
    if sorted(i for group in groups_a for i in group) != list(range(count_a)):
        return None
    return [[a_to_b[i] for i in group] for group in groups_a]


def partial_verified_bom_groups(groups_a,records,count_a,count_b):
    """Reuse only established geometry correspondences, never guessed pairs."""
    mapping={};seen=set()
    for record in records:
        ai,bi=record.a_index,record.b_index
        if record.status not in ('SAME','RENAMED','MOVED') or ai is None or bi is None:continue
        if ai in mapping or bi in seen or not 0<=ai<count_a or not 0<=bi<count_b:return []
        mapping[ai]=bi;seen.add(bi)
    if sorted(i for group in groups_a for i in group)!=list(range(count_a)):return []
    return [[mapping[i] for i in group if i in mapping] for group in groups_a if any(i in mapping for i in group)]


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
            diff_step=True,tolerance=0.01,progress=None, preview3d=False, revision_style=False, old_alpha=0.4, geometry_context=None,full_bom=True,report_context=None,bom_fast=False,bom_csv=True,precomputed_material_regions=None):
    from .geometry_registry import GeometryRegistry
    geometry_context=geometry_context if geometry_context is not None else GeometryRegistry()
    out=Path(folder);out.mkdir(parents=True,exist_ok=True)
    from .stage_fast import StageWriter
    stage=StageWriter(out)
    stage.update(step="eksport" if generate_step else "pominieto",reports="oczekuje",report_percent=0)
    for name in ('NAZWY_TE_SAME_GEOMETRIE.csv','NAZWY_ZMIENIONA_GEOMETRIA.csv','DIAGNOSTYKA_DOPASOWANIA.json','ZAKRES_IMPORTU.txt','PODGLAD_KOLOROW_3D.html','UWAGI_PODGLAD_3D.txt','POROWNANIE_KOLORY.step','ROZNICE_BREP.step','DIAGNOSTYKA_KOLOROW.json','POROWNANIE_KOLORY_DIAGNOSTYKA_STEP.json','GRUPY_ZW3D.json','OSTRZEZENIA.txt','BŁĄD_EKSPORTU_STEP.txt','UWAGI_ROZNICE_BREP.txt','DETAL_ROZNICE.csv','MATERIAL_ROZNICE.csv','BOM_A.csv','BOM_B.csv','BOM_GRUPY_A.json','BOM_GRUPY_B.json','UWAGI_BOM.txt','RAPORT_ZMIAN.html','RAPORT.html','PODSUMOWANIE.json','CZASY_ANALIZY.json'):
        (out/name).unlink(missing_ok=True)
    # One native Boolean decomposition shared across main STEP, HTML and CSV.
    # Do this before export, never create inconsistent secondary calculations.
    from .material_deltas import all_changes,COLORS as MATERIAL_COLORS
    material_regions,material_errors=all_changes(records,a,b,tolerance,progress,precomputed_material_regions) if revision_style else ({},{})
    if material_errors:
        (out/'UWAGI_ROZNICE_BREP.txt').write_text('\n'.join(
            f'{i+1}: {error}' for i,error in material_errors.items()),encoding='utf8')
    rows=[]
    for record_index,r in enumerate(records):
        old=a[r.a_index] if r.a_index is not None else None
        new=b[r.b_index] if r.b_index is not None else None
        rows.append([STATUS_PL[r.status],('TAK' if r.name_changed or r.status=='RENAMED' else ''),visible_name(old.name,old.path) if old else '',
                     visible_name(new.name,new.path) if new else '',
                     visible_path(old.path) if old else '',visible_path(new.path) if new else '',
                     _fmt(r.delta_x),_fmt(r.delta_y),_fmt(r.delta_z),_fmt(r.distance_mm),
                     _fmt(r.volume_delta_mm3),r.note,_fmt(r.rotation_deg),r.confidence,
                     _fmt(material_regions[record_index].common_mm3) if record_index in material_regions else '',
                     _fmt(material_regions[record_index].added_mm3) if record_index in material_regions else '',
                     _fmt(material_regions[record_index].removed_mm3) if record_index in material_regions else '',
                     ('Zweryfikowano Boolean' if record_index in material_regions else
                      'Błąd Boolean: '+material_errors[record_index] if record_index in material_errors else '')])
    headers=['Rodzaj zmiany','Różnica nazw A/B','Nazwa A','Nazwa B','Ścieżka A','Ścieżka B',
             'Różnica X [mm]','Różnica Y [mm]','Różnica Z [mm]','Przesunięcie środka [mm]',
             'Różnica objętości [mm³]','Uwagi','Obrót dopasowania [°]','Pewność dopasowania','Materiał wspólny [mm³]','Materiał dodany [mm³]','Materiał usunięty [mm³]','Weryfikacja różnic']
    renamed_rows=[(a[r.a_index].name,b[r.b_index].name,a[r.a_index].path,b[r.b_index].path)
                  for r in records if r.a_index is not None and r.b_index is not None
                  and (r.name_changed or r.status=='RENAMED') and r.status in ('SAME','RENAMED')]
    if renamed_rows:
        write_csv(out/'NAZWY_TE_SAME_GEOMETRIE.csv',
                  ['Nazwa A','Nazwa B','Ścieżka A','Ścieżka B'],renamed_rows)
    renamed_changed=[(a[r.a_index].name,b[r.b_index].name,a[r.a_index].path,b[r.b_index].path)
                     for r in records if r.status=='CHANGED' and r.name_changed
                     and r.a_index is not None and r.b_index is not None]
    if renamed_changed:
        write_csv(out/'NAZWY_ZMIENIONA_GEOMETRIA.csv',
                  ['Nazwa A','Nazwa B','Ścieżka A','Ścieżka B'],renamed_changed)
    diagnostic={'zmienione_rewizje':sum(r.status=='CHANGED' for r in records),
                'zmieniona_geometria_i_nazwa':len(renamed_changed),
                'dobor_podobnych_rewizji':(report_context or {}).get('revision_overlap'),
                'bez_zmian_geometrii':len([r for r in records if r.status in ('SAME','RENAMED')]),
                'nazwy_rozne_geometria_ta_sama':len(renamed_rows),
                'statusy_szczegolowe':dict(Counter(r.status for r in records)),
                'wyrównanie':(report_context or {}).get('alignment',{}),
                'zasada':'SAME = identyczna geometria i położenie po wyrównaniu; nazwa jest informacją niezależną'}
    (out/'DIAGNOSTYKA_DOPASOWANIA.json').write_text(json.dumps(diagnostic,ensure_ascii=False,indent=2),encoding='utf8')
    color_check={}
    err=None;details={'written':False,'solids':0,'changes':[],'errors':[]}
    if generate_step:
        try:
            if progress:progress('Etap 1/3: budowanie kolorowego STEP (może potrwać przy dużych złożeniach)...')
            step_start=perf_counter()
            color_check=(export_revision_step(str(out/'POROWNANIE_KOLORY.step'),records,a,b,colors,old_alpha,progress=progress,material_regions=material_regions) if revision_style else export_colored_step(str(out/'POROWNANIE_KOLORY.step'),records,a,b,colors))
            if progress:progress(f"Kolorowy STEP zapisany po {perf_counter()-step_start:.1f} s; weryfikacja: {color_check.get('weryfikacja','brak')}")
            # Exporter used the selected full or structural verification mode.
            (out/'DIAGNOSTYKA_KOLOROW.json').write_text(json.dumps(color_check,ensure_ascii=False,indent=2),encoding='utf-8')
            if not (out/'POROWNANIE_KOLORY.step').is_file() or (out/'POROWNANIE_KOLORY.step').stat().st_size<100:
                raise RuntimeError('Brak pełnego wynikowego STEP')
            # Atomic marker only after the selected export validation succeeded.
            # UI may now hand off STEP while BOM/HTML work continues in worker.
            stage.update(step='gotowy',reports='przygotowanie',report_percent=5,
                         step_bytes=(out/'POROWNANIE_KOLORY.step').stat().st_size,verification=color_check.get('weryfikacja','nieznana'))
            if progress:progress(f"STEP GOTOWY — możesz otworzyć w ZW3D; raporty powstają dalej ({color_check['pokolorowane_etykiety']} brył)")
        except Exception as exc:
            err=str(exc)
            stage.update(step='blad',step_error=err,reports='przygotowanie',report_percent=5)
            import traceback
            (out/'BŁĄD_EKSPORTU_STEP.txt').write_text(traceback.format_exc(),encoding='utf-8')
            if progress:progress('BŁĄD EKSPORTU STEP: '+err)
    # Reporting begins AFTER STEP is verified. No unnecessary STEP re-import.
    write_csv(out/'ZMIANY.csv',headers,rows)
    # Single final RAPORT.html; no misleading second/early report.
    stage.update(basic_report_ready=False,full_bom=full_bom,reports='bom_a' if full_bom else 'html',report_percent=12)
    bom_warnings=[]
    def safe_groups(parts,role,start,end,known_groups=None):
        before=len(geometry_context.bom_errors)
        before_budget=geometry_context.stats.get('bom_budget_exhausted',0)
        effective_fast=bom_fast or len(parts)>180
        if effective_fast and not bom_fast:
            warning=f'BOM {role}: duże złożenie ({len(parts)} brył); szybkie grupowanie wyłącznie po potwierdzonej geometrii. Liczba pozycji może być większa.'
            bom_warnings.append(warning)
            if progress:progress(warning)
        try:
            result=geometry_groups(parts,progress,report_progress=lambda i,n:stage.update(
                reports='bom_'+role.lower(),report_percent=start+int((end-start)*i/max(1,n))),
                context=geometry_context,tolerance=tolerance,fast_proven_only=effective_fast,time_budget_s=28,
                **({'known_groups':known_groups} if known_groups else {}))
            if geometry_context.stats.get('bom_budget_exhausted',0)>before_budget:
                bom_warnings.append(f'BOM {role}: przekroczono 28 s na grupowanie, niepotwierdzone duplikaty pokazano osobno. Masa całkowita i liczba brył nie zmieniły się.')
            if len(geometry_context.bom_errors)>before:
                warning=f'BOM {role}: grupowanie niepełne; {len(geometry_context.bom_errors)-before} błędów sprawdzania geometrii. Nierozstrzygnięte części zachowano osobno.'
                bom_warnings.append(warning)
                if progress:progress(warning)
            return result
        except Exception as exc:
            warning=f'BOM {role}: nie udało się pogrupować części ({exc}); zestawienie zawiera osobno każde wystąpienie.'
            bom_warnings.append(warning)
            if progress:progress(warning)
            return [[i] for i in range(len(parts))]
    bom_seconds=0.0
    bom_a=[];bom_b=[]
    if full_bom:
        bom_start=perf_counter()
        if progress:progress(f'Etap 2/3: grupowanie BOM A ({len(a)} brył).')
        groups_a=safe_groups(a,"A",12,44)
        if progress:progress(f'BOM A ukończony po {perf_counter()-bom_start:.1f} s; grup: {len(groups_a)}.')
        if progress:progress(f'Etap 2/3: grupowanie BOM B ({len(b)} brył).')
        if b is a:
            groups_b=groups_a
            stage.update(reports='bom_b',report_percent=76)
            if progress:progress('BOM B wykorzystuje grupy A z ostrzeżeniami.' if bom_warnings else 'BOM B ponownie wykorzystuje zweryfikowane grupy identycznego STEP A.')
        else:
            # Matching already proved each SAME/RENAMED pair. Equality is
            # transitive, so A's verified BOM groups transfer through a complete
            # bijection; no second geometry pass is needed in this safe case.
            transferred = None if bom_warnings else reuse_verified_bom_groups(groups_a,records,len(a),len(b))
            if transferred is not None:
                groups_b = transferred
                stage.update(reports='bom_b',report_percent=76)
                if progress:progress('BOM B: ponowne użycie zweryfikowanych grup A i dopasowań rewizji.')
            else:
                seeds=[] if bom_warnings else partial_verified_bom_groups(groups_a,records,len(a),len(b))
                groups_b=safe_groups(b,"B",44,76,known_groups=seeds)
        if progress:progress(f'BOM A+B ukończony po {perf_counter()-bom_start:.1f} s; grup B: {len(groups_b)}.')
        stage.update(reports="zapisywanie_bom",report_percent=78)
        bom_a=_bill(a,density,groups_a);bom_b=_bill(b,density,groups_b)
        from .material_mass_report import render_mass_report
        (out/'MASA_MATERIALY.html').write_text(render_mass_report(bom_a,bom_b,density),encoding='utf-8')
        for role,parts,groups in [('A',a,groups_a),('B',b,groups_b)]:
            mapping=[{'ilosc':len(ids),'wystapienia':[{'index':i,'name':parts[i].name,'path':parts[i].path} for i in ids]} for ids in groups]
            (out/f'BOM_GRUPY_{role}.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
        bh=['Nazwa','Ilość','Objętość jednej sztuki [mm³]','Masa jednej sztuki [kg]','Masa łączna [kg]','Ścieżka w złożeniu']
        if bom_csv:
            write_csv(out/'BOM_A.csv',bh,bom_a)
            write_csv(out/'BOM_B.csv',bh,bom_b)
        if bom_fast and geometry_context.stats['bom_inconclusive_fast_pairs']:
            bom_warnings.append('Szybki BOM: pominięto '+str(geometry_context.stats['bom_inconclusive_fast_pairs'])+
                ' kosztownych testów B-Rep. Takie same części o różnych definicjach CAD mogą pozostać w osobnych pozycjach. '+
                'Aby je połączyć, wybierz w Ustawieniach „BOM dokładny”.')
        bom_seconds=perf_counter()-bom_start
    total_a=sum(s.volume*density*1e-9 for s in a)
    total_b=sum(s.volume*density*1e-9 for s in b)
    counts=Counter(x.status for x in records)
    same_geometry=counts.get('SAME',0)+counts.get('RENAMED',0)
    changed_names=sum(bool(r.name_changed or r.status=='RENAMED')
                      for r in records if r.status in ('SAME','RENAMED'))
    palette={**COLORS,**(REVISION_COLORS if revision_style else {}),**MATERIAL_COLORS,**(colors or {})}
    if revision_style:
        palette['CHANGED']=palette['CHANGED_NEW']
        palette['UNCERTAIN']=palette['UNCERTAIN_NEW']
    palette['RENAMED']=palette['SAME']
    def hex_color(key):
        return '#' + ''.join(f'{round(min(1.,max(0.,c))*255):02x}' for c in palette[key])
    # Rows carry a stable machine status, independent of the Polish table labels.
    body=''.join('<tr data-renamed="'+('1' if r.name_changed or r.status=='RENAMED' else '0')+'" data-status="'+html.escape(r.status)+'">'+''.join('<td>'+html.escape(_csv_value(v) if isinstance(v,(int,float)) else str(v))+'</td>' for v in row)+'</tr>' for r,row in zip(records,rows))
    th=''.join('<th>'+html.escape(x)+'</th>' for x in headers)
    status=(f'Bez zmian geometrycznych: {same_geometry} (różne zapisy nazw: {changed_names}); '+
            ' '.join(f'{STATUS_PL[k]}: {v}' for k,v in sorted(counts.items()) if k not in ('SAME','RENAMED')))
    def pl_float(value, places=3):
        return f'{value:.{places}f}'.replace('.', ',')
    legend=''.join(f'<span><i class="dot" style="background:{hex_color(k)}"></i>{html.escape(STATUS_PL[k])}</span>' for k in ('SAME','RENAMED','MOVED','CHANGED','ADDED','REMOVED','UNCERTAIN'))
    flat_export=bool(color_check.get('tryb_bez_pustych_kontenerow') or color_check.get('eksport_plaski_bez_absr'))
    if revision_style:
        legend=''.join(f'<span><i class="dot" style="background:{hex_color(k)}"></i>{label}</span>' for k,label in [('SAME','Bez zmian'),('MOVED','Przesunięte — nowe B'),('CHANGED_NEW','Zmieniona geometria — B'),('UNCERTAIN_NEW','Wymaga sprawdzenia'),('REMOVED','Usunięte — A'),('ADDED','Nowe — B')])
        structure_note=('Bez pustych ABSR: plaski STEP — kazda rzeczywista bryla jest osobnym produktem z typem zmiany w nazwie. Nie ma podzlozen wedlug statusu.'
                        if flat_export else 'STEP ze struktura podzlozen — importer moze wyswietlac dodatkowe puste kontenery.')
        if material_regions:
            detail_colors=''.join(
                f'<span><i class="dot" style="background:#{"".join(f"{round(c*255):02x}" for c in palette[k])}"></i>{name}</span>'
                for k,name in [('CHANGED_COMMON','Zmieniony detal — materiał wspólny'),
                               ('CHANGED_ADDED','Dodany materiał'),
                               ('CHANGED_REMOVED','Usunięty materiał')])
            legend+='<div class="legend">'+detail_colors+'</div><p>W zmienionych detalach osobno pokazano materiał wspólny, dodany i usunięty. Ich kolory odpowiadają drugiemu wierszowi legendy.</p>'
        legend+=f'<p>Przezroczystość starej wersji: {round((1-old_alpha)*100)}%. Przesunięte i zmienione pary: stara A jest jaśniejsza i przezroczysta, nowa B ma pełny kolor. Przezroczystość zależy od importera ZW3D. {structure_note}</p>'
    htmltxt=f'''<!doctype html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>DS Compare — raport porównania modeli</title>
<style>body{{font:14px system-ui,sans-serif;max-width:1600px;margin:32px auto;padding:0 18px;background:#101820;color:#e6edf4}}h1{{font-size:26px}}p{{line-height:1.55}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{border:1px solid #34465c;padding:7px;text-align:left;vertical-align:top}}th{{background:#29394b;position:sticky;top:0}}tr:nth-child(even){{background:#192638}}.panel{{background:#192638;border:1px solid #34465c;border-radius:10px;padding:18px;margin:16px 0}}.legend{{display:flex;gap:18px;flex-wrap:wrap}}.dot{{display:inline-block;width:13px;height:13px;border-radius:3px;margin-right:7px}}small{{color:#abbaca}}input,select{{padding:10px;background:#24364b;color:white;border:1px solid #46607c;border-radius:5px;box-sizing:border-box}}input{{width:100%;max-width:520px}}.filters{{display:flex;flex-wrap:wrap;gap:12px;align-items:center}}select{{min-width:190px}}.bom-panel{{padding:0;overflow:hidden}}.bom-panel summary{{cursor:pointer;padding:17px 20px;font-size:17px;font-weight:650;list-style-position:inside}}.bom-panel summary:hover{{background:#24364b}}.bom-panel summary:focus-visible{{outline:2px solid #82aaff}}.bom-content{{padding:0 16px 16px}}.bom-panel:not([open]){{background:#192638}}</style></head><body>
<h1>DS Compare — raport porównania modeli</h1><div class="panel"><p><b>Wynik:</b> {html.escape(status)}</p><p><b>Liczba brył:</b> A = {len(a)}, B = {len(b)}</p>
<p><b>Masa A:</b> {pl_float(total_a)} kg &nbsp; <b>Masa B:</b> {pl_float(total_b)} kg &nbsp; <b>Różnica:</b> {pl_float(total_b-total_a)} kg</p>
<small>Gęstość: {pl_float(density,1)} kg/m³, jednostki STEP: mm. Masy obliczone z geometrii — bez odczytu materiałów ZW3D. BOM A i BOM B znajdują się w zwijanych sekcjach pod tabelą zmian.</small></div>
<div class="panel legend">{legend}</div>
<p><b>Widoczność elementów nakładających się:</b> {"W płaskim STEP wybieraj części po prefiksie statusu/nazwie i ukrywaj osobno w ZW3D; brak pustych podzłożeń." if flat_export else "W drzewie złożenia wyłącz grupę A_STARA lub B_NOWA w kategorii przesunięć."} Przezroczystość STEP zależy od importera CAD.</p>
<div class="panel filters"><label for="status">Rodzaj zmiany: <select id="status"><option value="ALL">Wszystkie</option><option value="SAME">Bez zmian</option><option value="RENAMED">Różne nazwy, ta sama geometria</option><option value="MOVED">Przesunięte</option><option value="ADDED">Nowe</option><option value="REMOVED">Usunięte</option><option value="CHANGED">Zmieniona geometria</option><option value="UNCERTAIN">Do sprawdzenia</option></select></label><input id="search" type="search" placeholder="Szukaj nazwy, ścieżki, uwag…" aria-label="Szukaj w raporcie"><span id="count" aria-live="polite"></span></div>
<div style="overflow:auto;max-height:75vh"><table id="table"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>
<script>(function(){{ const rows=[...document.querySelectorAll('#table tbody tr')],q=document.getElementById('search'),filter=document.getElementById('status'),count=document.getElementById('count'); function update(){{let visible=0;const text=q.value.toLocaleLowerCase('pl').trim(),status=filter.value;for(const row of rows){{const ok=(status==='ALL'||(status==='SAME'&&['SAME','RENAMED'].includes(row.dataset.status))||(status==='RENAMED'&&row.dataset.renamed==='1')||row.dataset.status===status)&&row.textContent.toLocaleLowerCase('pl').includes(text);row.hidden=!ok;row.style.display=ok?'':'none';if(ok)visible++;}}count.textContent='Pozycji: '+visible+' / '+rows.length;}}q.addEventListener('input',update);filter.addEventListener('change',update);update();}})();</script></body></html>'''
    if full_bom:
        # BOM can be folded independently; the changes table must stay immediately visible.
        sections=[]
        for label,items in (("A — stara rewizja",bom_a),("B — nowa rewizja",bom_b)):
            heads=['Nazwa','Ilość','Objętość [mm³]','Masa / szt. [kg]','Masa łączna [kg]','Ścieżka']
            ths=''.join('<th>'+html.escape(h)+'</th>' for h in heads)
            cells=''.join('<tr>'+''.join('<td>'+html.escape(_csv_value(v) if isinstance(v,(int,float)) else str(v))+'</td>' for v in item)+'</tr>' for item in items)
            header=f'BOM {html.escape(label)} · {len(items)} grup · {sum(int(x[1]) for x in items)} szt.'
            sections.append(f'<details class="panel bom-panel"><summary>{header}</summary><div class="bom-content"><div style="overflow:auto;max-height:65vh"><table><thead><tr>{ths}</tr></thead><tbody>{cells}</tbody></table></div></div></details>')
        # Place collapsed BOM *after* the visible revision changes table.
        htmltxt=htmltxt.replace('<script>(function()', ''.join(sections)+'<script>(function()',1)
    if revision_style:
        htmltxt=htmltxt.replace(' i ROZNICE_BREP.step (kolorowy model dodanego i usuniętego materiału, jeżeli eksport się powiedzie)', ' (pełne części obu rewizji, jeżeli eksport się powiedzie)')
    if not full_bom:htmltxt=htmltxt.replace('BOM A i BOM B znajdują się w zwijanych sekcjach pod tabelą zmian.','Pełny BOM wyłączony; porównanie i masa obejmują wszystkie wczytane bryły.')
    if bom_warnings:
        (out/'UWAGI_BOM.txt').write_text('\n'.join(bom_warnings),encoding='utf-8')
        htmltxt=htmltxt.replace('<body>','<body><p role=alert>'+html.escape(' '.join(bom_warnings))+'</p>',1)
    # Import scope, provenance and registration warnings are inserted BEFORE
    # final write, rather than reopening and rewriting the whole HTML 1-3x.
    context_info=report_context or {}
    notices=[]
    partial_material=bool((context_info.get('revision_overlap') or {}).get('incomplete') or counts.get('UNCERTAIN') or material_errors)
    if partial_material:
        reason=(context_info.get('revision_overlap') or {}).get('reason','Niepotwierdzone pozycje lub niepełne obliczenia materiału.')
        message='Raport częściowy: nie potwierdzono wszystkich różnic materiału. Elementy wymagające sprawdzenia oznaczono osobno. Masy pochodzą z importowanych brył; część geometrii wymaga weryfikacji. '+str(reason)
        notices.append('<div class="panel" role="alert"><strong>'+html.escape(message)+'</strong></div>')
        (out/'ANALIZA_NIEKOMPLETNA.txt').write_text(message+'\n',encoding='utf8')
    else:
        (out/'ANALIZA_NIEKOMPLETNA.txt').unlink(missing_ok=True)
    from .alignment_notice import alignment_notice
    registration_note=alignment_notice(context_info.get('alignment',{}))
    if registration_note:
        notices.append('<div class="panel" role="note"><strong>Położenie modeli</strong><p>'+html.escape(registration_note)+'</p></div>')
    omitted=sum(int(v.get('faces_outside_solids',0))
                for v in context_info.get('import',{}).values())
    if omitted:
        warning=f'Zakres porównania: tylko bryły SOLID. Pominięto {omitted} powierzchni poza bryłami (A+B).'
        (out/'ZAKRES_IMPORTU.txt').write_text(warning,encoding='utf8')
        notices.append('<p role="alert">'+html.escape(warning)+'</p>')
    if context_info.get('alignment',{}).get('warning'):
        warning=context_info['alignment']['warning']
        (out/'OSTRZEZENIA.txt').write_text(warning+'\n',encoding='utf8')
        notices.append('<p role="alert"><strong>'+html.escape(warning)+'</strong></p>')
    if revision_style:
        note=(f'<div class="panel"><b>A — stara rewizja:</b> {html.escape(str(context_info.get("A","")))}'
              f'<br><b>B — nowa rewizja:</b> {html.escape(str(context_info.get("B","")))}'
              f'<br>Tolerancja: {tolerance} mm</div>')
        notices.append(note)
        if err:notices.append('<p role="alert"><b>Eksport STEP nie powiódł się:</b> '+html.escape(err)+'</p>')
    if notices:
        htmltxt=htmltxt.replace('<body>','<body>'+''.join(notices),1)
    stage.update(reports='html',report_percent=89)
    final_report=out/'RAPORT.html'
    draft=out/'RAPORT.html.tmp'
    stage.update(basic_report_ready=False,report_percent=91)
    if diff_step:
        if progress:progress('Etap po B-Rep 4/4: obliczanie dodatkowego STEP różnic materiałowych...')
        try:
            if progress:progress('Tworzenie STEP z fragmentami dodanymi i usuniętymi...')
            details=export_differences_step(str(out/'ROZNICE_BREP.step'),records,a,b,tolerance,progress,colors=palette,material_regions=material_regions)
        except Exception as exc:
            details['errors'].append(str(exc))
    # Errors from optional ROZNICE_BREP.step must never invalidate the main
    # POROWNANIE_KOLORY.step, even when the optional exporter raises.
    if details["errors"] and progress:
        progress('UWAGA: opcjonalny STEP różnic materiałowych: '+'; '.join(details["errors"]))
    late_notices=[]
    if details["errors"]:
        late_notices.append("Opcjonalny STEP różnic materiałowych: "+"; ".join(details["errors"]))
    preview_info=None
    if preview3d:
        try:
            if progress:progress('Generowanie niezależnego podglądu 3D w kolorze...')
            from .preview3d import create_preview
            preview_info=create_preview(out/'PODGLAD_KOLOROW_3D.html', records, a, b,
                                        colors=palette,progress=progress,old_alpha=old_alpha,material_regions=material_regions,alignment=context_info.get('alignment',{}),dual_revisions=True)
        except Exception as exc:
            late_notices.append('Podgląd 3D: '+str(exc))
            (out/'UWAGI_PODGLAD_3D.txt').write_text(str(exc),encoding='utf-8')
            if progress:progress('Podgląd 3D niedostępny: '+str(exc))
    if material_regions:
        write_csv(out/'MATERIAL_ROZNICE.csv',
            ['Nazwa A','Nazwa B','Ścieżka złożenia','Materiał wspólny [mm³]',
             'Dodany [mm³]','Usunięty [mm³]'],[
            [a[records[i].a_index].name,b[records[i].b_index].name,
             b[records[i].b_index].path,info.common_mm3,info.added_mm3,info.removed_mm3]
            for i,info in sorted(material_regions.items())])
    if details['changes']:
        write_csv(out/'DETAL_ROZNICE.csv',
            ['Nazwa A','Nazwa B','Usunięty materiał [mm3]','Dodany materiał [mm3]'],details['changes'])
    if details['errors']:
        warnings_path=out/'UWAGI_ROZNICE_BREP.txt'
        old_warnings=warnings_path.read_text(encoding='utf-8') if warnings_path.exists() else ''
        prefix=old_warnings.rstrip('\n')+'\n' if old_warnings else ''
        warnings_path.write_text(prefix+'\n'.join('Opcjonalny STEP: '+e for e in details['errors']),encoding='utf-8')
    if material_errors:
        late_notices.append('Niedostępne dokładne różnice materiału dla '+str(len(material_errors))+
                            ' par: w STEP zachowano pełne części A i B zamiast zgadywać kolory.')
    if late_notices:
        htmltxt=htmltxt.replace('<body>','<body>'+''.join('<p role="alert">'+html.escape(message)+'</p>' for message in late_notices),1)
    from .report_view import enhance_report
    available=[(name,label) for name,label in [('PODGLAD_KOLOROW_3D.html','Podgląd 3D'),('POROWNANIE_KOLORY.step','Kolorowy STEP'),('ZMIANY.csv','Zmiany CSV'),('BOM_A.csv','BOM A'),('BOM_B.csv','BOM B')] if (out/name).is_file()]
    from .result_insights import enriched_records,overview_html
    enriched=enriched_records(records,a,b,context_info.get('revision_overlap'),material_errors)
    overview=overview_html(enriched,context_info,tolerance,not partial_material and not material_errors)
    if not (out/'PODGLAD_KOLOROW_3D.html').is_file():
        import re
        overview=re.sub(r'<a class="preview-link"[^>]*>.*?</a>','',overview)
    htmltxt=htmltxt.replace('<div class="panel filters">',overview+'<div class="panel filters">',1)
    if (out/'MASA_MATERIALY.html').is_file():
        htmltxt=htmltxt.replace('<body>','<body><p><a href="MASA_MATERIALY.html">Masa części — materiały i gęstości (edytuj)</a></p>',1)
    htmltxt=enhance_report(htmltxt,palette,counts,(out/'PODGLAD_KOLOROW_3D.html').is_file(),available)
    draft.write_text(htmltxt,encoding='utf-8');draft.replace(final_report)
    stage.update(basic_report_ready=True,reports='finalizacja',report_percent=95)
    if progress:progress('Finalizowanie raportu i podsumowania...')
    (out/'PODSUMOWANIE.json').write_text(json.dumps({'statuses':counts,
                        'same_geometry_count':same_geometry,'renamed_geometry_count':changed_names,'geometry_and_name_changed_count':len(renamed_changed),
                        'solids_A':len(a),'solids_B':len(b),
                        'colors_hex':{k:hex_color(k) for k in palette},'density_kg_m3':density,'mass_A_kg':total_a,'mass_B_kg':total_b,
                        'step_verification':color_check.get('weryfikacja'),'step_export_error':err,'optional_diff_errors':list(details['errors']),
                        'main_step_error':err,'main_step_ready':bool(generate_step and err is None and (out/'POROWNANIE_KOLORY.step').is_file()),
                        'step_ready':bool(generate_step and err is None and (out/'POROWNANIE_KOLORY.step').is_file()),
                        'import_diagnostics':context_info.get('import',{}),
                        'source_fingerprints':context_info.get('fingerprints',{}),
                        'manual_pairs':context_info.get('manual_pairs',[]),
                        'alignment':context_info.get('alignment',{}),
                        'analysis_complete':not partial_material,'material_analysis_complete':not partial_material,
                        'revision_overlap':context_info.get('revision_overlap',{}),
                        'source_A':context_info.get('source_A',''),
                        'source_B':context_info.get('source_B',''),
                        'tolerance_mm':tolerance,
                        'export_style':'revision_A_B' if revision_style else 'standard',
                        'old_alpha':old_alpha,
                        'full_bom':full_bom,'bom_grouping_complete':bool(full_bom and not bom_warnings),'bom_mode':'szybki' if bom_fast else 'dokladny','bom_csv':bool(full_bom and bom_csv),'bom_seconds':bom_seconds,'bom_warnings':bom_warnings,'diff_step':details,'material_regions':[{**{'record_index':i},**{'common_mm3':v.common_mm3,'added_mm3':v.added_mm3,'removed_mm3':v.removed_mm3}} for i,v in sorted(material_regions.items())],'material_errors':material_errors,'preview_3d':preview_info,'records':enriched},indent=2,ensure_ascii=False),encoding='utf-8')
    stage.update(reports='gotowe',report_percent=100)
    return out,err
