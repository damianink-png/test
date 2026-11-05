"""Exercise the exact CAD engine embedded in the current Tauri portable delivery."""
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe, transform
from dsac29.step_io import ColoredDocument
from dsac29.native_guard import guarded_common
from dsac29.material_deltas import volume

exe = str(Path(sys.argv[1]).resolve())
root = Path(sys.argv[2]).resolve()
root.mkdir(parents=True, exist_ok=True)


def model(path, width=10, shift=0, count=8, name="PLATE_123_REV_A"):
    doc = ColoredDocument()
    shape = BRepPrimAPI_MakeBox(20, width, 7).Shape()
    for i in range(count):
        placed = transform(shape, np.eye(3), np.array([i*57+shift, i*i*3, 0.]))
        doc.add(placed, name, (.2, .5, .8))
    doc.write(path)


model(root/'old.step')
for case, width, shift, count, name, expected in (
    ('repeated_named_revision', 11, 0, 8, 'PLATE_123_REV_B', {'CHANGED':8}),
    ('repeated_other_name', 11, 0, 8, 'OTHER_123_REV_B', {'REMOVED':8, 'ADDED':8}),
    ('repeated_unequal_count', 11, 0, 7, 'PLATE_123_REV_B', {'REMOVED':8, 'ADDED':7}),
    ('global_shift', 10, 1000, 8, 'PLATE_123_REV_B', {'SAME':8}),
):
    model(root/f'{case}.step', width, shift, count, name)
    output = root/case
    args = [exe, '--worker', 'compare', '--a', str(root/'old.step'),
            '--b', str(root/f'{case}.step'), '--output', str(output),
            '--revision-style', '--no-bom', '--generate-step', '--preview3d']
    if shift:
        args.append('--align-auto')
    proc = subprocess.Popen(args)
    approved = False
    deadline = time.monotonic()+300
    try:
        while proc.poll() is None:
            if time.monotonic()>deadline:
                raise TimeoutError(f'Frozen worker timeout: {case}')
            request = output/'_WYROWNANIE_PYTANIE.json'
            if shift and request.exists() and not approved:
                proposal = json.loads(request.read_text(encoding='utf-8'))
                assert not proposal.get('unresolved') and not proposal.get('unrelated'), proposal
                assert np.allclose(proposal['translation_mm'], [-1000, 0, 0]), proposal
                (output/'_WYROWNANIE_ODPOWIEDZ.json').write_text(json.dumps(
                    dict(token=proposal['token'], decision='align')), encoding='utf-8')
                approved = True
            time.sleep(.25)
        assert proc.returncode == 0, (case, proc.returncode)
        summary = json.loads((output/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
        assert summary['statuses'] == expected, (case, summary['statuses'])
        assert summary['main_step_ready'], summary
        assert not summary.get('material_errors'), summary.get('material_errors')
        if case=='repeated_named_revision':
            assert summary['revision_overlap']['accepted']==8
        elif case in ('repeated_other_name','repeated_unequal_count'):
            assert summary['revision_overlap']['boolean_checks']==0
        if shift:
            assert summary['alignment']['applied'], summary['alignment']
            assert np.allclose(summary['alignment']['translation_B_to_A_mm'], [-1000, 0, 0])
        (output/'FROZEN_OK.json').write_text(json.dumps(dict(case=case, statuses=expected)), encoding='utf-8')
        print(f'Frozen comparison PASS: {case}', flush=True)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()

# The onefile executable must also work as its own isolated native worker.
a = describe(BRepPrimAPI_MakeBox(20,10,7).Shape(), 'A', 'A')
b = describe(BRepPrimAPI_MakeBox(20,11,7).Shape(), 'B', 'B')
common = guarded_common(a.shape, b.shape, .01, timeout_s=90,
                        process_args=[exe, '--native-brep-compare'])
assert abs(volume(common)-1400)<.001
(root/'NATIVE_OK.json').write_text(json.dumps({'common_mm3':volume(common)}), encoding='utf-8')
print('Frozen native Common PASS', flush=True)
