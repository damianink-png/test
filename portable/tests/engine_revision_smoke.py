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
    ('repeated_unequal_count', 11, 0, 7, 'PLATE_123_REV_B', {'CHANGED':7, 'REMOVED':1}),
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
        elif case == 'repeated_unequal_count':
            # The current material policy admits seven individually unique,
            # spatially aligned revisions even if an eighth copy disappeared.
            # Require completed native Common/Cut evidence for every CHANGED
            # pair; never weaken this test to accept a heuristic classification.
            assert summary['revision_overlap']['accepted']==7, summary['revision_overlap']
            assert summary['revision_overlap']['boolean_checks']>=1, summary['revision_overlap']
            changed=[r for r in summary['records'] if r['status']=='CHANGED']
            assert len(changed)==7 and all('Common' in r['confidence'] for r in changed), changed
        elif case == 'repeated_other_name':
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

# Unequal repeated population: a stationary survivor is SAME, a uniquely
# reworked neighbour is CHANGED, and one missing occurrence is REMOVED.
# This exercises the *frozen executable*, not just the Python policy helper.
old=ColoredDocument();new=ColoredDocument()
for i in range(8):
    pos=np.array([i*57.,i*i*3.,0.])
    old.add(transform(BRepPrimAPI_MakeBox(20,10,7).Shape(),np.eye(3),pos),
            'PLATE_123_REV_A',(.2,.5,.8))
    if i<7:
        width=11 if i==6 else 10
        new.add(transform(BRepPrimAPI_MakeBox(20,width,7).Shape(),np.eye(3),pos),
                'PLATE_123_REV_B',(.2,.5,.8))
pa=root/'mixed_unequal_old.step';pb=root/'mixed_unequal_new.step'
old.write(pa);new.write(pb);output=root/'mixed_unequal_stationary'
proc=subprocess.Popen([exe,'--worker','compare','--a',str(pa),'--b',str(pb),
    '--output',str(output),'--revision-style','--no-bom','--generate-step'])
try:
    proc.wait(timeout=300)
    assert proc.returncode==0,proc.returncode
    summary=json.loads((output/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
    assert summary['statuses']=={'SAME':6,'CHANGED':1,'REMOVED':1},summary['statuses']
    assert summary['revision_overlap']['boolean_checks']>=1,summary['revision_overlap']
    assert all('Common' in r['confidence'] for r in summary['records']
               if r['status']=='CHANGED'),summary['records']
    assert summary['main_step_ready'] and not summary.get('material_errors'),summary
    print('Frozen comparison PASS: mixed_unequal_stationary',flush=True)
finally:
    if proc.poll() is None:proc.kill();proc.wait()

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

# Largest unique inertial anchor must drive the active frozen workflow,
# despite many repeated screws, reversed B order and revision suffix changes.
old=ColoredDocument();new=ColoredDocument();parts=[]
for i in range(20):
    parts.append((BRepPrimAPI_MakeBox(5,6,7).Shape(),np.array([i*41.,i*i*3.,i%3*40.]),'SCREW'))
for i,dims in enumerate([(23,17,11),(37,26,16),(123,85,13)]):
    parts.append((BRepPrimAPI_MakeBox(*dims).Shape(),np.array([i*150.,-170.-i*40.,i*80.]),f'COMP_{i}'))
offset=np.array([1950.,-375.,82.])
for shape,pos,name in parts:old.add(transform(shape,np.eye(3),pos),name+'_afm0',(.2,.5,.8))
for shape,pos,name in reversed(parts):new.add(transform(shape,np.eye(3),pos+offset),name+'_afm2',(.2,.5,.8))
pa=root/'unique_old.step';pb=root/'unique_new.step';old.write(pa);new.write(pb)
output=root/'unique_largest_anchor'
proc=subprocess.Popen([exe,'--worker','compare','--a',str(pa),'--b',str(pb),'--output',str(output),
    '--revision-style','--no-bom','--generate-step','--align-auto'])
deadline=time.monotonic()+300
try:
    while proc.poll() is None:
        if time.monotonic()>deadline:raise TimeoutError('Largest unique frozen anchor test')
        if (output/'_WYROWNANIE_PYTANIE.json').exists():raise AssertionError('Unique full assembly placement must be automatic')
        time.sleep(.25)
    assert proc.returncode==0,proc.returncode
    summary=json.loads((output/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
    assert summary['statuses']=={'SAME':23},summary['statuses']
    alignment=summary['alignment']
    assert alignment['applied'] and alignment['search_algorithm']=='unique_largest_inertia_anchor',alignment
    assert np.allclose(alignment['translation_B_to_A_mm'],-offset,atol=1e-5)
    evidence=alignment['search_diagnostics']['unique_anchor_evidence']
    assert abs(evidence['anchors'][0]['volume']-123*85*13)<.01,evidence
    assert summary['main_step_ready']
    print('Frozen comparison PASS: unique_largest_anchor_23_of_23',flush=True)
finally:
    if proc.poll() is None:proc.kill();proc.wait()

# Identical geometry/count does not make every peer a global-frame witness.
# Two parts move locally by 220 mm after a global translation. Exercise both
# repeated geometry and a six-anchor sparse frame in an otherwise changed model.
for case,repeated,extra in [('repeated_local_moves',True,0),('sparse_six_local_moves',False,72)]:
    old=ColoredDocument();new=ColoredDocument();offset=np.array([1700.,-250.,90.])
    for i in range(8):
        dims=(20,13,7) if repeated else (20+i*3,13+i,7+i*.3)
        shape=BRepPrimAPI_MakeBox(*dims).Shape();pos=np.array([i*77.,(i*i%17)*41.,i%3*51.])
        local=np.array([0.,220.,0.]) if i>=6 else np.zeros(3)
        name='REPEATED' if repeated else f'PART_{i}'
        old.add(transform(shape,np.eye(3),pos),name+'_REV_A',(.2,.5,.8))
        new.add(transform(shape,np.eye(3),pos+offset+local),name+'_REV_B',(.2,.5,.8))
    for i in range(extra):
        old.add(transform(BRepPrimAPI_MakeBox(3+i*.01,4,5).Shape(),np.eye(3),np.array([i*35.,1500.,0.])),f'OLD_{i}',(.2,.5,.8))
        new.add(transform(BRepPrimAPI_MakeBox(60+i,70,80).Shape(),np.eye(3),np.array([10000.+i*100.,10000.,10000.])),f'NEW_{i}',(.2,.5,.8))
    pa=root/(case+'_old.step');pb=root/(case+'_new.step');old.write(pa);new.write(pb);output=root/case
    proc=subprocess.Popen([exe,'--worker','compare','--a',str(pa),'--b',str(pb),'--output',str(output),
        '--revision-style','--no-bom','--generate-step','--align-auto'])
    deadline=time.monotonic()+300;approved=set()
    try:
        while proc.poll() is None:
            if time.monotonic()>deadline:raise TimeoutError(case)
            request=output/'_WYROWNANIE_PYTANIE.json'
            if request.exists():
                proposal=json.loads(request.read_text(encoding='utf-8'))
                if proposal['token'] not in approved:
                    assert not proposal.get('unresolved') and not proposal.get('unrelated'),proposal
                    assert np.allclose(proposal['translation_mm'],-offset,atol=1e-5),proposal
                    (output/'_WYROWNANIE_ODPOWIEDZ.json').write_text(json.dumps(dict(token=proposal['token'],decision='align')),encoding='utf-8')
                    approved.add(proposal['token'])
            time.sleep(.25)
        assert proc.returncode==0,(case,proc.returncode)
        summary=json.loads((output/'PODSUMOWANIE.json').read_text(encoding='utf-8'))
        expected={'SAME':6,'MOVED':2}
        if extra:expected.update(REMOVED=extra,ADDED=extra)
        assert summary['statuses']==expected,(case,summary['statuses'])
        assert approved and summary['alignment']['applied']
        assert summary['alignment']['votes']==6 and summary['alignment']['final_moved_count']==2
        assert len(summary['alignment']['certified_pairs'])==6
        assert summary['main_step_ready']
        moved=[r for r in summary['records'] if r['status']=='MOVED']
        assert len(moved)==2 and all(abs(r['delta_y']-220.)<1e-5 for r in moved),moved
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
