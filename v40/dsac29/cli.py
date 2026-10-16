from __future__ import annotations
import argparse,sys,traceback
from time import perf_counter
from pathlib import Path
from .step_io import load_step
from .compare import compare
from .report import produce


def process(a_path,b_path,output,tolerance=0.01,density=7850.,step=True,progress=print,cancelled=None,colors=None,diff_step=True,preview3d=False,align=False):
    ts=perf_counter()
    if progress:progress('Wczytywanie starszej wersji modelu…')
    a=load_step(a_path,progress=progress)
    if progress:progress(f'Wczytywanie A: {perf_counter()-ts:.1f} s; brył: {len(a)}')
    tb=perf_counter()
    b=load_step(b_path,progress=progress)
    if progress:progress(f'Wczytywanie B: {perf_counter()-tb:.1f} s; brył: {len(b)}')
    alignment={'enabled':False}
    if align:
        from .alignment import align_assembly
        b,alignment=align_assembly(a,b,tolerance,progress)
    tc=perf_counter()
    rec=compare(a,b,tolerance,progress=progress,cancelled=cancelled)
    if progress:progress(f'Dopasowanie geometrii: {perf_counter()-tc:.1f} s')
    if progress:progress('Zapis raportów CSV/HTML i modelu porównawczego STEP...')
    folder,err=produce(output,a,b,rec,density,generate_step=step,colors=colors,
                       diff_step=diff_step,tolerance=tolerance,progress=progress,preview3d=preview3d)
    import json
    summary_path=folder/'PODSUMOWANIE.json'
    summary=json.loads(summary_path.read_text(encoding='utf-8'))
    summary.update(alignment=alignment,source_A=str(Path(a_path).resolve()),source_B=str(Path(b_path).resolve()),tolerance_mm=tolerance)
    summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
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
