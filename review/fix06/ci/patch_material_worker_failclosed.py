"""Fail-closed fix for isolated material B-Rep failures (no PyInstaller crash popup).

Only patch the frozen source when both exact anchors are present. The CAD
algorithm, geometric tolerances, and matching decisions remain unchanged.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1])

def replace(path,old,new):
    p=root/path
    source=p.read_text(encoding='utf-8')
    if source.count(old)!=1:
        raise RuntimeError(f'Expected exactly one verified patch anchor in {p}: {source.count(old)}')
    p.write_text(source.replace(old,new),encoding='utf-8')

replace('dsac29/native_guard.py',
"""    if req.get('operation') == 'material_regions':
        from .material_guard import worker as material_worker
        return material_worker(req,result_path)
""",
"""    if req.get('operation') == 'material_regions':
        from .material_guard import worker as material_worker
        try:
            return material_worker(req,result_path)
        except Exception as exc:
            # An unproven repair is not a PyInstaller fatal exception.
            # Never turn failed B-Rep proof into a positive material result.
            from .brep_safety import UnprovenRepair
            error_code=('INVALID_BREP_AFTER_REPAIR' if isinstance(exc,UnprovenRepair)
                        else 'MATERIAL_BOOLEAN_UNVERIFIED')
            response=dict(ok=False,error_code=error_code,
                          error=f'{type(exc).__name__}: {exc}')
            try:
                target=Path(result_path)
                temporary=target.with_suffix('.partial')
                temporary.write_text(json.dumps(response,ensure_ascii=False),encoding='utf-8')
                temporary.replace(target)
            except OSError:
                pass
            sys.stderr.write(error_code+': '+response['error']+'\n')
            sys.stderr.flush()
            # Avoid unsafe OCCT/PyInstaller teardown after invalid topology.
            # The parent treats exit 70 as an incomplete proof.
            os._exit(70)
""")
replace('dsac29/material_guard.py',
"""            if p.returncode:raise RuntimeError('Proces materiału: '+str(p.returncode)+' '+p.stderr.decode('utf8',errors='replace')[-2000:])
            data=json.loads(reply.read_text(encoding='utf8'))
            if data.get('ok') is not True:raise ValueError('Brak poprawnego wyniku')
""",
"""            # Isolated worker writes a structured failure before exiting 70.
            # Its negative reply must never be accepted as geometry evidence.
            data=json.loads(reply.read_text(encoding='utf8')) if reply.exists() else None
            if not isinstance(data,dict) or data.get('ok') is not True:
                reason=(str(data.get('error_code',''))+': '+str(data.get('error',''))
                        if isinstance(data,dict) else p.stderr.decode('utf8',errors='replace')[-1000:])
                raise ValueError('Niepotwierdzona geometria: '+reason)
            if p.returncode:
                raise RuntimeError('Proces materiału zakończył się błędem '+str(p.returncode))
""")
print('MATERIAL_WORKER_FAILCLOSED_PATCH_PASS',root,flush=True)
