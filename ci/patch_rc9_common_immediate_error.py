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
        os.environ['DSCOMPARE_COMMON_FAILFAST_REPLY']=str(result_path)
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

# A malformed OCCT result can hang while unwinding its C++ objects BEFORE
# the outer worker exception handler is entered. Exit at the negative-volume
# detection site, only when the isolated Common worker supplied a reply path.
material=root/'dsac29'/'material_deltas.py'
m=material.read_text(encoding='utf-8')
old_negative="""        if not math.isfinite(signed) or signed < -max(1e-5,float(tolerance)**3):
            raise RuntimeError(f'OCCT Common returned impossible signed volume {signed:.9g} mm3; no valid material intersection')"""
new_negative="""        if not math.isfinite(signed) or signed < -max(1e-5,float(tolerance)**3):
            error=f'OCCT Common returned impossible signed volume {signed:.9g} mm3; no valid material intersection'
            from os import environ, _exit
            from pathlib import Path
            import json
            reply_path=environ.get('DSCOMPARE_COMMON_FAILFAST_REPLY')
            if reply_path:
                # Explicit negative verdict, never a fabricated empty Common.
                destination=Path(reply_path)
                destination.write_text(json.dumps(dict(ok=False,error=error)),encoding='utf-8')
                destination.with_suffix('.phase').write_text('common_rejected',encoding='utf-8')
                _exit(70)
            raise RuntimeError(error)"""
if m.count(old_negative)!=1:raise SystemExit(f'Negative Common anchor count {m.count(old_negative)}')
m=m.replace(old_negative,new_negative)
ast.parse(m)
material.write_text(m,encoding='utf-8')
print('RC9 negative Common exits before unsafe OCCT object teardown in isolated child')

# Keep the OCCT binding untouched in unit tests.  Patching OCP.GProp classes
# globally can destabilize the native runtime during teardown on Windows.
# Extract only the signed-volume read behind a narrow, mockable function.
material=root/'dsac29'/'material_deltas.py'
m=material.read_text(encoding='utf-8')
volume_anchor="""        properties=GProp_GProps()
        BRepGProp.VolumeProperties_s(result,properties)
        signed=float(properties.Mass())"""
if m.count(volume_anchor)!=1:
    raise SystemExit(f'Common signed-volume anchor count {m.count(volume_anchor)}')
m=m.replace(volume_anchor,"        signed=_common_signed_volume(result)")
helper="""

def _common_signed_volume(shape):
    \"\"\"Read OCCT signed volume without monkeypatching C++ binding classes.\"\"\"
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    props=GProp_GProps()
    BRepGProp.VolumeProperties_s(shape,props)
    return float(props.Mass())
"""
if 'def _common_signed_volume(' in m:
    raise SystemExit('Common signed-volume helper already present')
m+=helper
ast.parse(m)
material.write_text(m,encoding='utf-8')
print('RC9 signed Common volume isolated behind mockable Python helper')
