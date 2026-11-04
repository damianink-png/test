"""Set bounded complexity-aware timeout for isolated material Common/Cut.

Apply to the source AFTER extracting and overlaying the CAD engine.
This does not change geometric tolerances, matching rules or proof outcomes.
"""
from pathlib import Path
import sys

POLICY = '''

def material_operation_timeout(brep_bytes, override=None):
    """Choose deadline from serialized local B-Rep bytes, never dimensions.

    Geometry bytes are already on disk. No additional CAD computation runs.
    Explicit overrides remain available for diagnostics and small test limits.
    """
    from math import isfinite
    if override is not None:
        limit = float(override)
        if not isfinite(limit) or not 0 < limit <= 900:
            raise ValueError('Nieprawidłowy limit Common/Cut')
        return limit
    size = int(brep_bytes)
    if size < 0:
        raise ValueError('Niepoprawny rozmiar B-Rep')
    if size >= 8 * 1024 * 1024:
        return 240
    if size >= 2 * 1024 * 1024:
        return 180
    if size >= 256 * 1024:
        return 120
    return 60
'''


def patch(path):
    target = Path(path)
    source = target.read_text(encoding='utf-8')
    if 'def material_operation_timeout(' in source:
        print('DSCOMPARE_MATERIAL_TIMEOUT_ALREADY_PATCHED', target)
        return
    original = 'def calculate_isolated(old, new, tolerance=.01, *, common_shape=None, timeout_s=35, process_args=None):'
    if source.count(original) != 1:
        raise RuntimeError('Expected exactly one original 35-second material worker')
    source = source.replace(original, 'def calculate_isolated(old, new, tolerance=.01, *, common_shape=None, timeout_s=None, process_args=None):')
    anchor = 'from .native_guard import NativeGeometryFailure, _load_brep, _preserve_failure, _worker_metrics\n'
    if source.count(anchor) != 1:
        raise RuntimeError('Unrecognized material worker import header')
    source = source.replace(anchor, anchor + POLICY + '\n')
    anchor = "        request=root/'request.json';reply=root/'reply.json' "
    if source.count(anchor) != 1:
        raise RuntimeError('Missing expected B-Rep serialization boundary')
    source = source.replace(anchor,
        "        brep_bytes=sum(Path(req[name]).stat().st_size for name in ('a','b'))\n"
        "        deadline_s=material_operation_timeout(brep_bytes,timeout_s)\n" + anchor)
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
    compile(source, str(target), 'exec')
    target.write_text(source, encoding='utf-8')
    print('DSCOMPARE_MATERIAL_TIMEOUT_POLICY_PASS', target)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: patch_material_timeout.py ROOT/dsac29/material_guard.py')
    patch(sys.argv[1])
