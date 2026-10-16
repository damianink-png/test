"""Worker for long-running CAD operations; isolated from the Qt event loop."""
import argparse,json,sys,traceback
from pathlib import Path

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--worker',required=True,choices=['compare','mass','mesh'])
    p.add_argument('--a',default='');p.add_argument('--b',default='')
    p.add_argument('--input',default='');p.add_argument('--output',required=True)
    p.add_argument('--tolerance',type=float,default=0.01)
    p.add_argument('--density',type=float,default=7850)
    p.add_argument('--quality',default='normalna')
    p.add_argument('--generate-step',action='store_true')
    p.add_argument('--diff-step',action='store_true')
    p.add_argument('--align',action='store_true')
    p.add_argument('--palette',default='{}')
    p.add_argument('--schema',choices=['AP214IS','AP242DIS'],default='AP214IS')
    ns=p.parse_args(argv)
    folder=Path(ns.output);folder.mkdir(parents=True,exist_ok=True)
    event_file=folder/'_POSTEP_V37.jsonl'
    result_file=folder/'_WYNIK_V37.json'
    for path in (event_file,result_file):
        try:path.unlink()
        except FileNotFoundError:pass
    def emit(message):
        with event_file.open('a',encoding='utf-8') as file:
            file.write(json.dumps({'tekst':str(message)},ensure_ascii=False)+'\n');file.flush()
    try:
        if ns.worker=='compare':
            import os
            os.environ['DSCOMPARE_STEP_SCHEMA']=ns.schema
            from .cli import process
            palette=json.loads(ns.palette)
            output,recs,err=process(ns.a,ns.b,ns.output,ns.tolerance,ns.density,
                   step=ns.generate_step,diff_step=ns.diff_step,preview3d=False,
                   colors=palette,progress=emit,align=ns.align)
            payload={'ok':True,'folder':str(output),'wyniki':len(recs),'blad_step':err}
        elif ns.worker=='mass':
            from .single_mass import analyze_single
            output,s=analyze_single(ns.input,ns.output,ns.density,progress=emit)
            payload={'ok':True,'folder':str(output),'podsumowanie':s}
        else:
            from .mesh_v37 import make_mesh
            info=make_mesh(ns.input,folder/'SCENA_3D.npz',ns.quality,notify=emit)
            payload={'ok':True,'folder':str(folder),'scena':info}
    except Exception:
        emit('BŁĄD: '+traceback.format_exc().splitlines()[-1])
        payload={'ok':False,'error':traceback.format_exc()}
    result_file.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if payload['ok'] else 1
