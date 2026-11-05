"""Worker for long-running CAD operations; isolated from the Qt event loop."""
import argparse,json,sys,traceback
from pathlib import Path

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--worker',required=True,choices=['compare','mass','mesh','detail','import','diagnostic'])
    p.add_argument('--source-proof',default='{}',help=argparse.SUPPRESS)
    p.add_argument('--preview3d',action='store_true')
    p.add_argument('--thumbnails',action='store_true')
    p.add_argument('--revision-style',action='store_true')
    p.add_argument('--old-alpha',type=float,default=0.4)
    p.add_argument('--no-preview',action='store_true')
    p.add_argument('--manual-review',default='')
    p.add_argument('--record',type=int,default=0)
    p.add_argument('--a',default='');p.add_argument('--b',default='')
    p.add_argument('--input',default='');p.add_argument('--output',required=True)
    p.add_argument('--inputs-file',default='',help='JSON list of CAD model paths for batch mass')
    p.add_argument('--diagnostic-step',default='',help='Local STEP path; aggregate counts only')
    p.add_argument('--tolerance',type=float,default=0.01)
    p.add_argument('--density',type=float,default=7850)
    p.add_argument('--quality',default='normalna')
    p.add_argument('--generate-step',action='store_true')
    p.add_argument('--no-bom',action='store_true',help='Only STEP and complete change report; omit grouped BOM')
    p.add_argument('--fast-bom',action='store_true',help='Only group provably identical B-Reps; rotated copies may stay separate')
    p.add_argument('--no-bom-csv',action='store_true',help='Keep BOM in HTML only, no BOM_A.csv/BOM_B.csv')
    p.add_argument('--safe-export',action='store_true',help='ZW3D-safe flat export (default)')
    p.add_argument('--flat-zw3d',action='store_true',help='Write solid-only flat STEP without ABSR assembly nodes')
    p.add_argument('--absr-test',action='store_true',help='Add independent flat STEP for importer testing; native STEP remains unchanged')
    p.add_argument('--legacy-step-assemblies',action='store_true',help='Opt-in legacy assembly with empty product containers')
    p.add_argument('--body-colors',action='store_true',help='Use only solid and definition STEP styling to avoid face-subshape clutter in ZW3D')
    p.add_argument('--diff-step',action='store_true')
    p.add_argument('--align',action='store_true')
    p.add_argument('--align-auto',action='store_true',help='Check common coordinates, ask approval if B needs moving')
    p.add_argument('--allow-review-decision',action='store_true',help='Ask whether to create an explicitly incomplete report if material proof fails')
    p.add_argument('--direct-scene',action='store_true')
    p.add_argument('--palette',default='{}')
    p.add_argument('--max-solids',type=int,default=20000)
    p.add_argument('--step-verify',choices=['auto','full','fast'],default='auto')
    p.add_argument('--schema',choices=['AP214IS','AP242DIS'],default='AP214IS')
    ns=p.parse_args(argv)
    folder=Path(ns.output);folder.mkdir(parents=True,exist_ok=True)
    event_file=folder/'_POSTEP_V37.jsonl'
    result_file=folder/'_WYNIK_V37.json'
    # Record the executable/build actually serving this job; a timeout cannot
    # silently masquerade as another installed or cached engine version.
    build_root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
    try:build=json.loads((build_root/'build_info.json').read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):build={}
    (folder/'ENGINE_BUILD.json').write_text(json.dumps({
        'executable':sys.executable,'frozen':bool(getattr(sys,'frozen',False)),
        'build':build},ensure_ascii=False,indent=2),encoding='utf-8')

    for path in (event_file,result_file):
        try:path.unlink()
        except FileNotFoundError:pass
    from .progress_events import ProgressEvents
    emit=ProgressEvents(event_file)
    if ns.worker=='compare':
        from . import trace_r22
        trace_r22.setup(folder)
    try:
        from .process_lifetime import contain_children
        contain_children()
        if ns.worker=='import':
            from .parallel_import import import_worker
            import_worker(ns.input, ns.output, ns.max_solids, emit,source_proof=json.loads(ns.source_proof))
            payload={'ok':True,'folder':str(folder)}
        elif ns.worker=='diagnostic':
            from .local_tests import run as run_local_diagnostics
            diagnostics=run_local_diagnostics(folder,progress=emit,source_step=ns.diagnostic_step or None)
            payload={'ok':diagnostics['ok'],'folder':str(folder),
                     'passed':diagnostics['passed'],'total':diagnostics['total'],
                     'report':diagnostics['report']}
        elif ns.worker=='compare':
            import os
            os.environ['DSCOMPARE_STEP_SCHEMA']=ns.schema
            os.environ['DSCOMPARE_STEP_VERIFY']=ns.step_verify
            os.environ['DSCOMPARE_FLAT_FALLBACK']='1' if ns.flat_zw3d else '0'
            os.environ['DSCOMPARE_ABSR_TEST_OUTPUT']='1' if ns.absr_test else '0'
            os.environ['DSCOMPARE_BODY_COLORS']='1' if ns.body_colors else '0'
            os.environ['DSCOMPARE_SAFE_EXPORT']='0'  # native status subassemblies, no phantom leaf products
            from .cli import process
            import time,uuid
            def approve_alignment(proposal):
                request=folder/'_WYROWNANIE_PYTANIE.json'
                answer=folder/'_WYROWNANIE_ODPOWIEDZ.json'
                try:request.unlink(missing_ok=True);answer.unlink(missing_ok=True)
                except OSError:pass
                token=uuid.uuid4().hex
                info={
                    'token':token,'status':'needs_confirmation',
                    'translation_mm':[round(float(v),3) for v in proposal.get('translation_B_to_A_mm',(0,0,0))],
                    'method':str(proposal.get('method','')),
                    'votes':int(proposal.get('votes',0)),
                    'anchors':int(proposal.get('anchors',0)),
                    'unresolved':proposal.get('status')=='unresolved',
                    'unrelated':proposal.get('status')=='unrelated',
                    'reason':proposal.get('reason',''),
                    'search_failed':proposal.get('search_failed',False),
                    'search_diagnostics':proposal.get('search_diagnostics',{}),
                    'material_unverified':proposal.get('status')=='material_unverified',
                    'unverified_A':int(proposal.get('unverified_A',0)),
                    'unverified_B':int(proposal.get('unverified_B',0)),
                }
                request.write_text(json.dumps(info,ensure_ascii=False),encoding='utf8')
                emit('Analiza wymaga decyzji użytkownika: '+('raport częściowy' if info['material_unverified'] else 'modele mogą być różne' if info['unrelated'] else 'wyrównanie modeli')+'…')
                deadline=time.monotonic()+600
                while time.monotonic()<deadline:
                    if answer.exists():
                        try:
                            resp=json.loads(answer.read_text(encoding='utf8'))
                            allowed=('review','cancel') if info['material_unverified'] else ('align','original','search','cancel')
                            if resp.get('token')==token and resp.get('decision') in allowed:
                                return resp['decision']
                        except (OSError,ValueError):pass
                    time.sleep(.2)
                raise RuntimeError('Przekroczono czas oczekiwania na decyzję użytkownika (10 minut).')
            palette=json.loads(ns.palette)
            output,recs,err=process(ns.a,ns.b,ns.output,ns.tolerance,ns.density,
                   full_bom=not ns.no_bom,bom_fast=ns.fast_bom,bom_csv=not ns.no_bom_csv,max_solids=ns.max_solids,step=ns.generate_step,diff_step=ns.diff_step,preview3d=ns.preview3d,
                   colors=palette,progress=emit,align=ns.align,auto_align=ns.align_auto,alignment_approval=approve_alignment if ns.align_auto else None,revision_style=ns.revision_style,thumbnails=ns.thumbnails,old_alpha=ns.old_alpha,direct_scene=ns.direct_scene,manual_review=json.loads(Path(ns.manual_review).read_text(encoding='utf-8')) if ns.manual_review else None,material_approval=lambda proposal: (emit('Zapisuję automatycznie raport częściowy; niepotwierdzone części pozostają do sprawdzenia.'), 'review')[1])
            summary=json.loads((output/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
            main_ready=bool(summary.get('step_ready',False))
            payload={'ok':bool(not ns.generate_step or main_ready),
                     'folder':str(output),'wyniki':len(recs),'blad_step':err,
                     'step_ready':main_ready,
                     'analysis_complete':summary.get('analysis_complete',True),
                     'optional_diff_errors':summary.get('optional_diff_errors',[]),
                     'alignment':summary.get('alignment',{})}
        elif ns.worker=='detail':
            from .scene42 import make_detail
            target=make_detail(Path(ns.input),ns.record,ns.tolerance,emit)
            payload={'ok':True,'folder':str(target)}
        elif ns.worker=='mass':
            from .single_mass import analyze_single
            from .mass_batch import analyze_many
            if ns.inputs_file:
                files=json.loads(Path(ns.inputs_file).read_text(encoding='utf8'))
                output,s=analyze_many(files,ns.output,ns.density,progress=emit,max_solids=ns.max_solids)
            else:
                output,s=analyze_single(ns.input,ns.output,ns.density,progress=emit,preview=not ns.no_preview,max_solids=ns.max_solids)
            from .standalone_mass_materials import enhance_mass_html, MassReportFormatError
            editable=False
            try:
                editable=enhance_mass_html(output,ns.density)
            except MassReportFormatError as exc:
                # The geometry and computed CSV/JSON are already finished.
                emit('UWAGA: Masa została obliczona; edytor materiałów niedostępny: '+str(exc))
                try:
                    (Path(output)/'UWAGI_RAPORT_MASY.txt').write_text(str(exc),encoding='utf-8')
                except OSError:
                    pass
            except Exception:
                # Preserve the successful CAD mass calculation, and log any
                # unexpected optional HTML-editor failure for diagnosis.
                details=traceback.format_exc()
                emit('UWAGA: Masa została obliczona, lecz raport materiałów nie został rozszerzony. Sprawdź DIAGNOSTYKA_RAPORT_MASY.txt.')
                try:
                    (Path(output)/'DIAGNOSTYKA_RAPORT_MASY.txt').write_text(details,encoding='utf-8')
                except OSError:
                    pass
            if editable:
                emit('Raport masy: edytowalne materiały i gęstości dla każdej pozycji BOM; zapis JSON i CSV.')
            elif not (Path(output)/'RAPORT_MASY.html').is_file():
                emit('UWAGA: Brak RAPORT_MASY.html — zachowano obliczoną masę i plik CSV.')
            payload={'ok':True,'folder':str(output),'podsumowanie':s,
                     'materials_editable':bool(editable)}
        else:
            from .mesh_v37 import make_mesh
            info=make_mesh(ns.input,folder/'SCENA_3D.npz',ns.quality,notify=emit)
            payload={'ok':True,'folder':str(folder),'scena':info}
    except Exception as exc:
        issue=traceback.format_exc()
        emit('BŁĄD: '+issue.splitlines()[-1])
        # Keep a full readable trace even when GUI/log collection is interrupted.
        try:
            (folder/'DIAGNOSTYKA_BLEDU.txt').write_text(issue,encoding='utf8')
        except OSError:pass
        from .import_validation import InvalidStepSolid
        from .native_guard import NativeGeometryFailure
        payload={'ok':False,'error':str(exc) if isinstance(exc,(InvalidStepSolid,NativeGeometryFailure)) else issue,
                 'diagnostic_file':str(folder/'DIAGNOSTYKA_BLEDU.txt')}
    if ns.worker=='compare':
        trace_r22.mark('worker','END' if payload.get('ok') else 'ERROR',ok=bool(payload.get('ok')))
    result_file.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if payload['ok'] else 1
