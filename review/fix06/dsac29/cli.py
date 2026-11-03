from __future__ import annotations
import argparse,sys,traceback
from time import perf_counter
from math import ceil
from pathlib import Path
from .import_cache import load_step_persistent as load_step
from .compare import compare, ShiftDetected
from .report import produce
from . import trace_r22 as trace


def process(a_path,b_path,output,tolerance=0.01,density=7850.,step=True,progress=print,cancelled=None,colors=None,diff_step=True,preview3d=False,align=False,direct_scene=False,manual_review=None,revision_style=False,old_alpha=0.4,thumbnails=False,max_solids=20000,full_bom=True,bom_fast=False,bom_csv=True,auto_align=False,alignment_approval=None,force_unrelated=False,material_approval=None):
    from .palette import semantic_overrides
    colors=semantic_overrides(colors)
    ts=perf_counter()
    trace.mark('fingerprints','BEGIN')
    from .manual_pairs import fingerprint
    # One validated full-file digest per distinct STEP input. Share with the
    # serial import cache; never trust merely path/size/mtime as identity.
    source_stats={};fingerprints={};memo={}
    for role,raw in (('A',a_path),('B',b_path)):
        src=Path(raw);before=src.stat()
        stat_key=(str(src.resolve()),before.st_size,before.st_mtime_ns)
        digest=memo.get(stat_key)
        if digest is None:
            digest=fingerprint(src)
        after=src.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            raise RuntimeError('Plik STEP został zmieniony w trakcie obliczania SHA-256: '+src.name)
        source_stats[role]=(after.st_size,after.st_mtime_ns)
        fingerprints[role]=digest
        memo[stat_key]=digest
    trace.mark('fingerprints','END',same_sha256=fingerprints['A']==fingerprints['B'])
    trace.mark('import','BEGIN')
    if manual_review and manual_review['fingerprints']!=fingerprints:raise ValueError('Pliki źródłowe zmieniły się od analizy; pary ręczne nie zostały zastosowane')
    import_stats={"A":{},"B":{}}
    identical_sources=(fingerprints['A']==fingerprints['B'] and not manual_review)
    import_mode='sekwencyjny'
    import_parallel_wall_s=None
    import_parallel_worker_s=None
    ta=perf_counter()
    a=b=None
    if not identical_sources:
        from .parallel_import import should_parallel, load_pair
        # Parallel import for moderate files, sequential for large models.
        combined_size=Path(a_path).stat().st_size+Path(b_path).stat().st_size
        parallel,reason=should_parallel(a_path,b_path)
        if combined_size>75_000_000:
            parallel,reason=False,'duże STEP: import sekwencyjny chroni pamięć'
        if parallel:
            try:
                a,b,import_stats,import_parallel_worker_s,import_parallel_wall_s=load_pair(
                    a_path,b_path,output,max_solids=max_solids,progress=progress,cancelled=cancelled,
                    source_proofs={role:{"sha256":fingerprints[role],"stat":source_stats[role]} for role in ("A","B")})
                import_mode='rownolegly_dwa_procesy'
                import_a_s=import_parallel_worker_s['A']
                import_b_s=import_parallel_worker_s['B']
            except (InterruptedError,TimeoutError):
                raise
            except Exception as exc:
                if progress:progress('Import równoległy niedostępny ('+str(exc)[:250]+'). Ponawiam bezpiecznie sekwencyjnie.')
                import_stats={"A":{},"B":{}}
                a=b=None
                import_mode='sekwencyjny_fallback'
        elif progress:
            progress('Import standardowy: '+reason)
    if a is None:
        if progress:progress('Wczytywanie starszej wersji modelu…')
        a=load_step(a_path,progress=progress,diagnostics=import_stats["A"],max_solids=max_solids,
                    precomputed_sha256=fingerprints['A'],source_stat=source_stats['A'])
        import_a_s=perf_counter()-ta
        if progress:progress(f'Wczytywanie A: {import_a_s:.1f} s; brył: {len(a)}')
        tb=perf_counter()
        if identical_sources:
            b=a
            import_stats['B']=dict(import_stats['A'])
            if progress:progress('R11: identyczna zawartość STEP (SHA-256). Import B i B-Rep pominięte bez utraty pewności.')
        else:
            if progress:progress('Wczytywanie nowszej wersji modelu…')
            b=load_step(b_path,progress=progress,diagnostics=import_stats["B"],max_solids=max_solids,
                        precomputed_sha256=fingerprints['B'],source_stat=source_stats['B'])
        import_b_s=perf_counter()-tb
        if progress:progress(f'Wczytywanie B: {import_b_s:.1f} s; brył: {len(b)}')
    trace.mark('import','END',solids_a=len(a),solids_b=len(b))
    alignment={'requested':bool(align or auto_align),'enabled':False}
    alignment_started=perf_counter()
    (Path(output)/'OSTRZEZENIA.txt').unlink(missing_ok=True)
    # R14: Never register the whole assembly before examining stage-1 matches.
    # Treat legacy --align and GUI auto-align as the same deferred workflow.
    should_align=bool(align or auto_align) and not identical_sources and not manual_review
    alignment_s=perf_counter()-alignment_started
    from .geometry_registry import GeometryRegistry
    geometry_context=GeometryRegistry()
    tc=perf_counter()
    deferred_s=0.0
    trace.mark('signatures','BEGIN',solids_a=len(a),solids_b=len(b))
    if not identical_sources and not manual_review:
        from .similarity_gate import check_related,ModelsUnrelated
        try:
            check_related(a,b)
        except ModelsUnrelated as exc:
            if force_unrelated:
                if progress:progress('UWAGA: '+str(exc)+' Kontynuuję na życzenie użytkownika.')
            elif alignment_approval is not None:
                choice=alignment_approval({'status':'unrelated','unrelated':True,'reason':str(exc)})
                if choice!='original':
                    raise InterruptedError('Anulowano porównanie prawdopodobnie niezwiązanych modeli.')
                if progress:progress('Kontynuuję porównanie mimo ostrzeżenia o różnej geometrii.')
            else:
                raise

    trace.mark('signatures','END')
    def inspect_stage1(matched,free_a,free_b):
        if not should_align:return None
        from .deferred_alignment import propose_from_stage1
        with trace.phase('translation_candidates',matched=len(matched),remaining_a=len(free_a),remaining_b=len(free_b)):
            return propose_from_stage1(a,b,matched,free_a,free_b,tolerance,progress,cancelled)

    step_reexport_tol=False
    certified_pairs=[]
    def do_compare(stage_hook=None):
        return compare(a,b,tolerance,progress=progress,cancelled=cancelled,
                       revision_only=revision_style and not manual_review,
                       exact_serialization=True,geometry_context=geometry_context,
                       stage1_check=stage_hook,step_reexport_tolerance=step_reexport_tol,certified_pairs=certified_pairs)

    proposal=None
    with trace.phase('initial_comparison'):
        try:
            rec=do_compare(inspect_stage1 if should_align else None)
        except ShiftDetected as caught:
            proposal=caught.proposal
            trace.mark('alignment_proposal','FOUND',votes=proposal.get('votes'),translation=proposal.get('translation_B_to_A_mm'))
    if should_align:
        trace.mark('alignment','BEGIN',proposal=bool(proposal))
        from .alignment import align_assembly,AlignmentUnavailable,_relocate
        import numpy as np
        shift_start=perf_counter()
        alignment.update(status='original_coordinates',method='stage1_first',
                         reason='Wstępna analiza nie potwierdziła lepszego globalnego przesunięcia.')
        if proposal is None:
            # Stage 1 ruled out expensive registration, not all possible
            # geometric differences; continue the ordinary compare unchanged.
            if rec:
                baseline=sum(r.status in ('SAME','RENAMED') for r in rec)
                population=min(len(a),len(b))
                if baseline<max(2,ceil(.20*population)):
                    alignment.update(status='unresolved_no_hypothesis',
                        reason='Nie potwierdzono globalnego przesunięcia; oryginalne współrzędne zachowane. '
                               'Przy mocno zmienionych rewizjach istnieje możliwość niewykrytego przesunięcia.')
                    if progress:progress('UWAGA: '+alignment['reason'])
        else:
            decision=None
            automatic=False
            # Automatic relocation is reserved for a LARGE, fully B-Rep
            # confirmed and unambiguous gain over the original CAD frame.
            if proposal.get('status')=='registered':
                votes=int(proposal.get('votes',0))
                original=int(proposal.get('previous_world_matches',0))
                pop=min(len(a),len(b))
                if (votes>=max(2*original,original+ceil(.30*pop))
                    and votes>=max(8,ceil(.50*pop))):
                    decision='align'
                    automatic=True
                    if progress:progress('Jednoznaczne przesunięcie B→A: '+
                        str(proposal.get('translation_B_to_A_mm'))+' mm; '
                        f'{votes} potwierdzeń B-Rep vs {original} bez przesunięcia. '
                        'Wyrównuję automatycznie.')
            if decision is None:
                if alignment_approval is None:
                    raise RuntimeError('Niepewne przesunięcie wymaga decyzji użytkownika.')
                decision=alignment_approval(proposal)
            if decision=='search':
                try:
                    _,proposal=align_assembly(a,b,tolerance,progress)
                    decision=alignment_approval(proposal)
                except AlignmentUnavailable as exc:
                    # An unsuccessful explicit search must not reopen the
                    # same "search for shift" dialog indefinitely.
                    alignment.update(status='search_failed_original',applied=False,
                                     reason='Nie znaleziono potwierdzonego przesunięcia: '+str(exc))
                    if progress:
                        progress('UWAGA: '+alignment['reason']+
                                 ' Kontynuuję porównanie w oryginalnych współrzędnych.')
                    decision='original'
            if decision=='original':
                if alignment.get('status')=='search_failed_original':
                    alignment.update(applied=False)
                else:
                    alignment.update(**{**proposal,'status':'original_by_user','applied':False,
                                        'reason':'Użytkownik wybrał oryginalne położenie.'})
            elif decision=='align' and proposal.get('status') in ('registered','already_aligned'):
                rotation=np.asarray(proposal.get('rotation_B_to_A',np.eye(3)))
                offset=np.asarray(proposal.get('translation_B_to_A_mm',[0,0,0]))
                b=[_relocate(p,rotation,offset) for p in b]
                alignment={**proposal,'approved_by_user':not automatic,'applied':True}
                step_reexport_tol=bool(proposal.get('step_reexport_tolerance'))
                certified_pairs=proposal.get('certified_pairs',[])
            else:
                raise InterruptedError('Anulowano analizę — modele pozostały niezmienione.')
            # The re-export rescue already proved EVERY CAD face of EVERY
            # occurrence. Avoid a redundant third native B-Rep pass, which can
            # hang on complex copied STEP edges with near-coincident trims.
            proven=proposal.get('full_pair_map') or []
            if alignment.get('applied') and len(proven)==len(a)==len(b):
                from .names import genuine_rename
                from .compare import Record
                rec=[]
                for i,j in proven:
                    name_changed=genuine_rename(a[i],b[j])
                    rec.append(Record(i,j,'SAME',
                        'Potwierdzona zgodność powierzchni CAD po przesunięciu B→A',
                        name_changed=name_changed))
                if progress:progress(f'B-Rep STEP: {len(rec)} brył zgodnych. Wykorzystano zapisane dowody geometryczne bez powtarzania porównania.')
            else:
                # Only one FULL comparison runs. The first pass stopped at stage 1.
                with trace.phase('final_comparison_after_alignment',certified_pairs=len(certified_pairs)):
                    rec=do_compare()
        trace.mark('alignment','END',applied=bool(alignment.get('applied')),certified_pairs=len(certified_pairs))
        deferred_s=perf_counter()-shift_start
        alignment_s+=deferred_s
    if manual_review:
        from .manual_pairs import apply_pairs
        rec=apply_pairs(a,b,rec,manual_review['pairs'],tolerance)
    precomputed_regions={}
    overlap_diagnostics=None
    if revision_style:
        trace.mark('revision_classification','BEGIN',pairs=len(rec))
        from .revision_rules import classify_revisions
        rec=classify_revisions(a,b,rec,tolerance,progress=progress,geometry_context=geometry_context,geometry_first=True)
        from .revision_overlap import merge_material_revisions
        rec,precomputed_regions,overlap_diagnostics=merge_material_revisions(a,b,rec,tolerance,progress,cancelled,review_approval=material_approval,geometry_context=geometry_context)
        trace.mark('revision_classification','END',pairs=len(rec),boolean_checks=(overlap_diagnostics or {}).get('boolean_checks'))
        if progress:
            same=sum(r.status in ("SAME","RENAMED") for r in rec)
            renamed=sum(r.name_changed for r in rec if r.status in ("SAME","RENAMED"))
            progress(f"Po wyrównaniu: {same} brył BEZ ZMIAN geometrycznych (różnice zapisu nazw: {renamed}).")
    matching_s=perf_counter()-tc-deferred_s
    if progress:progress(f'Dopasowanie geometrii: {matching_s:.1f} s')
    if progress:progress('Zapis modelu STEP, raportu i BOM...')
    t_output=perf_counter()
    trace.mark('export_step_html_bom','BEGIN',records=len(rec),step=bool(step),preview=bool(preview3d),bom=bool(full_bom))
    folder,err=produce(output,a,b,rec,density,generate_step=step,colors=colors,
                       diff_step=diff_step,tolerance=tolerance,progress=progress,preview3d=preview3d,revision_style=revision_style,old_alpha=old_alpha,geometry_context=geometry_context,full_bom=full_bom,bom_fast=bom_fast,bom_csv=bom_csv,report_context={
                        "A":Path(a_path).name,"B":Path(b_path).name,
                        "source_A":str(Path(a_path).resolve()),
                        "source_B":str(Path(b_path).resolve()),
                        "import":import_stats,"alignment":alignment,"tolerance_mm":tolerance,
                        "fingerprints":fingerprints,
                        "manual_pairs":manual_review['pairs'] if manual_review else [],
                        "revision_overlap":overlap_diagnostics},
                       precomputed_material_regions=precomputed_regions)
    output_stage_s=perf_counter()-t_output
    trace.mark('export_step_html_bom','END',duration_s=round(output_stage_s,3),step_error=err)
    if progress:progress(f'Zapis wyników (STEP + raport + BOM): {output_stage_s:.1f} s')
    import json
    # report.produce already wrote HTML and summary once using report_context.
    # Do not read/write multi-MB HTML again just to prepend the provenance.
    summary=json.loads((folder/'PODSUMOWANIE.json').read_text(encoding='utf8'))
    if thumbnails:
        from .thumbnails46 import make_thumbnail
        for role,parts in [('A',a),('B',b)]:
            try:make_thumbnail(parts,folder/f'MINIATURA_{role}.json')
            except Exception as exc:
                if progress:progress('Miniatura niedostępna: '+str(exc))
    if direct_scene:
        from .scene42 import make_result_scene
        try:
            info=make_result_scene(a,b,rec,folder,colors,progress)
            if not info['complete']:
                warning=f"Niepełny podgląd: {info['rendered_records']}/{info['expected_records']} pozycji. Zobacz SCENA_DIAGNOSTYKA.json."
                (folder/'UWAGI_SCENA.txt').write_text(warning,encoding='utf-8')
                if progress:progress(warning)
        except Exception as exc:
            (folder/'UWAGI_SCENA.txt').write_text(str(exc),encoding='utf-8')
            if progress:progress('Podgląd niedostępny: '+str(exc))
    timing={'import_A_including_fingerprint_s':import_a_s,'import_B_s':import_b_s,'import_mode':import_mode,'parallel_import_wall_s':import_parallel_wall_s,'parallel_worker_import_s':import_parallel_worker_s,'alignment_preflight_and_optional_registration_s':alignment_s,'alignment_status':alignment.get('status','not_requested'),'matching_and_classification_s':matching_s,'bom_grouping_s':summary.get('bom_seconds',0),
         'step_and_reports_stage_s':output_stage_s,
         'total_s':perf_counter()-ts,'registry':dict(geometry_context.stats),'slowest_bom_or_population_checks':geometry_context.slow_checks}
    (folder/'CZASY_ANALIZY.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2),encoding='utf-8')
    if progress:progress(f'Łączny czas przetwarzania: {perf_counter()-ts:.1f} s')
    if progress:progress('Gotowe: '+str(folder)+((' (UWAGA eksport STEP: '+err+')') if err else ''))
    return folder,rec,err


def main(argv=None):
    p=argparse.ArgumentParser(description='DS Assembly Compare V2.9 B-Rep STEP prototype')
    p.add_argument('a',help='Model A, STEP/STP')
    p.add_argument('b',help='Model B, STEP/STP')
    p.add_argument('-o','--output',default='DSAC_V29_WYNIKI')
    p.add_argument('--tolerance',type=float,default=0.01,help='mm, default 0.01')
    p.add_argument('--density',type=float,default=7850.,help='kg/m³; default steel 7850')
    p.add_argument('--no-step',action='store_true',help='Do not create colored STEP')
    ns=p.parse_args(argv)
    try:
        if ns.density<=0 or ns.density>25000:raise ValueError('Nieprawidlowa gestosc')
        folder,recs,err=process(ns.a,ns.b,ns.output,ns.tolerance,ns.density,not ns.no_step)
        print('\nRAPORT:',folder/'RAPORT.html')
        return 0 if err is None else 2
    except Exception:
        traceback.print_exc()
        return 1
if __name__=='__main__':sys.exit(main())
