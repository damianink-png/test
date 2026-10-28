"""Terminate a failed isolated Common worker without waiting for OCCT destructors.

A malformed Common may already have produced a negative signed volume, but
Python/OCCT object teardown can hang for the full 90 s. Only the isolated
Common failure path exits immediately. Never synthesize a valid intersection.
"""
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'
p=root/'dsac29'/'native_guard.py'
s=p.read_text(encoding='utf-8')
old="""        report('common_operate')
        common = operate(BRepAlgoAPI_Common,a_shape,b_shape,float(req['tolerance']))
        report('common_write')"""
new="""        report('common_operate')
        try:
            common = operate(BRepAlgoAPI_Common,a_shape,b_shape,float(req['tolerance']))
        except Exception as exc:
            # The operation already failed. Persist an explicit incomplete
            # verdict before terminating this disposable native worker.
            # os._exit avoids a possible hang in destructors of invalid OCCT
            # Boolean results; the coordinator still raises failure.
            error=f'{type(exc).__name__}: {exc}'
            report('common_rejected')
            Path(result_path).write_text(json.dumps(dict(ok=False,error=error)),encoding='utf-8')
            sys.stderr.write(error+'\\n')
            sys.stderr.flush()
            os._exit(70)
        report('common_write')"""
if s.count(old)!=1:raise SystemExit(f'Common worker anchor count {s.count(old)}')
s=s.replace(old,new)
old2="""            raise NativeGeometryFailure('Odizolowany OCC Common zakończył się błędem '+str(proc.returncode)+' '+proc.stderr.decode('utf8',errors='replace')[-2000:])"""
new2="""            error=''
            if reply.exists():
                try:
                    payload=json.loads(reply.read_text(encoding='utf-8'))
                    if payload.get('ok') is False:
                        error=str(payload.get('error',''))[:2000]
                except (OSError,ValueError,TypeError):
                    pass
            raise NativeGeometryFailure('Odizolowany OCC Common zakończył się błędem '+str(proc.returncode)+' '+(error or proc.stderr.decode('utf8',errors='replace')[-2000:]))"""
if s.count(old2)!=1:raise SystemExit(f'Common parent anchor count {s.count(old2)}')
s=s.replace(old2,new2)
ast.parse(s)
p.write_text(s,encoding='utf-8')
print('RC9 isolated Common fail-fast exit installed; errors remain incomplete')
