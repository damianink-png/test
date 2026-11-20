"""Set bounded complexity-aware timeout for isolated material Common/Cut.

Apply to the source AFTER extracting and overlaying the CAD engine.
This does not change geometric tolerances, matching rules or proof outcomes.
"""
from pathlib import Path
import sys

def patch(path):
    target = Path(path)
    source = target.read_text(encoding='utf-8')
    if 'from .material_complexity import material_operation_timeout' in source:
        print('DSCOMPARE_MATERIAL_TIMEOUT_ALREADY_PATCHED', target)
        return
    original = 'def calculate_isolated(old, new, tolerance=.01, *, common_shape=None, timeout_s=35, process_args=None):'
    if source.count(original) != 1:
        raise RuntimeError('Expected exactly one original 35-second material worker')
    source = source.replace(original, 'def calculate_isolated(old, new, tolerance=.01, *, common_shape=None, timeout_s=None, process_args=None):')
    anchor = 'from .native_guard import NativeGeometryFailure, _load_brep, _preserve_failure, _worker_metrics\n'
    if source.count(anchor) != 1:
        raise RuntimeError('Unrecognized material worker import header')
    source = source.replace(anchor, anchor + 'from .material_complexity import material_operation_timeout\n')
    anchor = "        request=root/'request.json';reply=root/'reply.json' "
    if source.count(anchor) != 1:
        raise RuntimeError('Missing expected B-Rep serialization boundary')
    source = source.replace(anchor,
        "        brep_bytes=sum(Path(req[name]).stat().st_size for name in ('a','b'))\n"
        "        deadline_s=material_operation_timeout(old.shape,new.shape,timeout_s)\n" + anchor)
    # The two processes verify the same file identities without allocating each entire B-Rep.
    digest = "hashlib.sha256(Path(req[key]).read_bytes()).hexdigest()"
    assert source.count(digest) == 2
    source = source.replace(digest, "brep_digest(req[key])")
    header = 'from .material_complexity import material_operation_timeout'
    source = source.replace(header, header + '\nfrom .brep_transport import brep_digest')
    replacements = (
        ("trace.mark('material_regions_isolated','BEGIN',old_name=old.name,new_name=new.name,timeout_s=timeout_s)",
         "trace.mark('material_regions_isolated','BEGIN',old_name=old.name,new_name=new.name,timeout_s=deadline_s,brep_bytes=brep_bytes)"),
        ("subprocess.run([*argv,str(request),str(reply)],timeout=timeout_s,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)",
         "subprocess.run([*argv,str(request),str(reply)],timeout=deadline_s,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)"),
        ("'Obliczenie Common/Cut nieukończone (limit '+str(timeout_s)+' s): '",
         "'Obliczenie Common/Cut nieukończone (limit '+str(deadline_s)+' s): '"),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise RuntimeError('Missing expected material timeout anchor: ' + old)
        source = source.replace(old, new)
    old = "            raise NativeGeometryFailure('Obliczenie Common/Cut nieukończone (limit '+str(deadline_s)+' s): '+str(exc)) from exc"
    new = "            reason=('Obliczenie Common/Cut nieukończone — przekroczony limit ('+str(deadline_s)+' s)' if isinstance(exc,subprocess.TimeoutExpired) else 'Obliczenie Common/Cut nieukończone — błąd geometrii lub procesu')\n            raise NativeGeometryFailure(reason+': '+str(exc)) from exc"
    if source.count(old)!=1: raise RuntimeError('Missing material error classifier')
    source=source.replace(old,new)
    compile(source, str(target), 'exec')
    target.write_text(source, encoding='utf-8')
    print('DSCOMPARE_MATERIAL_TIMEOUT_POLICY_PASS', target)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: patch_material_timeout.py ROOT/dsac29/material_guard.py')
    patch(sys.argv[1])
