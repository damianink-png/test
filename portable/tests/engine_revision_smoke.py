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
    ('repeated_afm_revision', 11, 0, 8, 'czesc1_afm2', {'CHANGED':8}),
):
    if case=='repeated_afm_revision':
        model(root/'old.step',name='czesc1_afm0')
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
        if case in ('repeated_named_revision','repeated_afm_revision'):
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

# Actual independent STEP write/read + arbitrary rigid pose in the frozen
# worker, rather than only direct in-memory registration functions.
axis=np.array([1.,2.,3.]);axis/=np.linalg.norm(axis)
x,y,z=axis;k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
rotation=np.eye(3)+np.sin(.63)*k+(1-np.cos(.63))*(k@k)
offset=np.array([1200.,-730.,441.]);rng=np.random.default_rng(779)
old=ColoredDocument();new=ColoredDocument()
for i in range(18):
    shape=BRepPrimAPI_MakeBox(10+i,12+i*.3,8+i*.7).Shape()
    placed=transform(shape,np.eye(3),rng.uniform(-400,400,3))
    old.add(placed,f'COMPONENT_{i}_REV_A',(.2,.5,.8))
    new.add(transform(placed,rotation,offset),f'COMPONENT_{i}_REV_B',(.2,.5,.8))
old.write(root/'rotated_old.step');new.write(root/'rotated_new.step')
output=root/'arbitrary_rigid_step'
proc=subprocess.Popen([exe,'--worker','compare','--a',str(root/'rotated_old.step'),
    '--b',str(root/'rotated_new.step'),'--output',str(output),'--revision-style',
    '--no-bom','--generate-step','--align-auto'])
deadline=time.monotonic()+300
try:
    while proc.poll() is None:
        if time.monotonic()>deadline:raise TimeoutError('Frozen arbitrary rigid STEP test timed out')
        if (output/'_WYROWNANIE_PYTANIE.json').exists():
            raise AssertionError('Unambiguous 18/18 real STEP alignment should be automatic')
        time.sleep(.25)
    assert proc.returncode==0,proc.returncode
    summary=json.loads((output/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
    assert summary['statuses']=={'SAME':18},summary['statuses']
    alignment=summary['alignment']
    assert alignment['applied'] and alignment['method']=='cad_global_consensus_trimmed_refinement',alignment
    assert np.allclose(np.asarray(alignment['rotation_B_to_A'])@rotation,np.eye(3),atol=1e-6)
    assert np.allclose(np.asarray(alignment['rotation_B_to_A'])@offset+alignment['translation_B_to_A_mm'],0,atol=1e-5)
    assert summary['main_step_ready']
    print('Frozen comparison PASS: arbitrary_rigid_step_18_of_18',flush=True)
finally:
    if proc.poll() is None:proc.kill();proc.wait()

# Independent STEP exports cover both changed revisions and the same solid
# re-exported with a different face partition. No mocked import or proof.
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
base=BRepPrimAPI_MakeBox(20,30,5).Shape()
hole=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(6,9,-1),gp_Dir(0,0,1)),2.,7.).Shape()
changed=BRepAlgoAPI_Cut(base,hole).Shape()
partitioned=BRepAlgoAPI_Fuse(BRepPrimAPI_MakeBox(4,30,5).Shape(),
    BRepPrimAPI_MakeBox(gp_Pnt(4,0,0),16,30,5).Shape()).Shape()
for case,new_shape,expected in [('changed_surface_frame',changed,{'CHANGED':8}),
                                ('same_partitioned_frame',partitioned,{'SAME':8})]:
    old=ColoredDocument();new=ColoredDocument()
    offset=np.array([1000.,250.,-50.])
    for i in range(8):
        pos=np.array([i*57.,i*i*3.,(i%3)*40.])
        old.add(transform(base,np.eye(3),pos),'PLATE_123_REV_A',(.2,.5,.8))
        new.add(transform(new_shape,np.eye(3),pos+offset),'PLATE_123_REV_B',(.2,.5,.8))
    pa=root/(case+'_old.step');pb=root/(case+'_new.step')
    old.write(pa);new.write(pb);output=root/case
    proc=subprocess.Popen([exe,'--worker','compare','--a',str(pa),'--b',str(pb),
        '--output',str(output),'--revision-style','--no-bom','--generate-step','--align-auto'])
    deadline=time.monotonic()+300;approved_tokens=set()
    try:
        while proc.poll() is None:
            if time.monotonic()>deadline:raise TimeoutError(case)
            request=output/'_WYROWNANIE_PYTANIE.json'
            if request.exists():
                proposal=json.loads(request.read_text(encoding='utf-8'))
                if proposal['token'] not in approved_tokens:
                    assert not proposal.get('unresolved') and not proposal.get('unrelated'),proposal
                    assert np.allclose(proposal['translation_mm'],-offset,atol=1e-5),proposal
                    (output/'_WYROWNANIE_ODPOWIEDZ.json').write_text(json.dumps(
                        dict(token=proposal['token'],decision='align')),encoding='utf-8')
                    approved_tokens.add(proposal['token'])
            time.sleep(.25)
        assert proc.returncode==0,(case,proc.returncode)
        summary=json.loads((output/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
        assert summary['statuses']==expected,(case,summary['statuses'])
        assert summary['alignment']['applied']
        assert np.allclose(summary['alignment']['translation_B_to_A_mm'],-offset,atol=1e-5)
        assert summary['main_step_ready'] and not summary.get('material_errors'),summary
        if case=='changed_surface_frame':
            assert approved_tokens,'Surface-only placement must require explicit approval'
            assert summary['alignment']['certified_pairs']==[],summary['alignment']
        print('Frozen comparison PASS: '+case,flush=True)
    finally:
        if proc.poll() is None:proc.kill();proc.wait()

# The onefile executable must also work as its own isolated native worker.
a = describe(BRepPrimAPI_MakeBox(20,10,7).Shape(), 'A', 'A')
b = describe(BRepPrimAPI_MakeBox(20,11,7).Shape(), 'B', 'B')
common = guarded_common(a.shape, b.shape, .01, timeout_s=90,
                        process_args=[exe, '--native-brep-compare'])
assert abs(volume(common)-1400)<.001
(root/'NATIVE_OK.json').write_text(json.dumps({'common_mm3':volume(common)}), encoding='utf-8')
print('Frozen native Common PASS', flush=True)
