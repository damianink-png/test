"""Reproducible native CAD registration cases; run with either source tree.

PYTHONPATH=<assembled-engine> python registration_benchmark.py <label> <json>
No timing threshold, mocks, corporate files, or dependency on Open3D/TEASER.
"""
from dataclasses import replace
from pathlib import Path
from time import perf_counter
import json
import sys
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.alignment import _relocate
from dsac29.compare import Record
from dsac29.deferred_alignment import propose_from_stage1


def scenario(n=18,repeated=False,rotated=False,noise=False,stable=None):
    rng=np.random.default_rng(779)
    stable=n if stable is None else stable
    axis=np.array([1.,2.,3.]);axis/=np.linalg.norm(axis)
    x,y,z=axis;k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
    r=np.eye(3)+np.sin(.63)*k+(1-np.cos(.63))*(k@k) if rotated else np.eye(3)
    t=np.array([1200.,-730.,441.]);a=[];b=[]
    for i in range(n):
        d=0 if repeated else i
        shape=BRepPrimAPI_MakeBox(10+d,12+d*.3,8+d*.7).Shape() if i<stable else BRepPrimAPI_MakeBox(300+i,200,100).Shape()
        p=_relocate(describe(shape,'OLD_REV_A','a'),np.eye(3),rng.uniform(-400,400,3))
        q=_relocate(p,r,t)
        if i>=stable:
            shape=BRepPrimAPI_MakeBox(500+i,300,200).Shape()
            q=_relocate(describe(shape,'NEW_REV_B','b'),r,t+p.center)
        if noise and i<stable:
            q=replace(q,center=q.center+np.array([.18,-.08,.04]),
                      volume=q.volume*1.01,area=q.area*1.005,eigenvalues=q.eigenvalues*1.02)
        a.append(p);b.append(q)
    return a,b[::-1],r,t


results=[]
for name,kwargs in [
    ('translation',{}),
    ('translation_reexport_drift',{'noise':True}),
    ('rotation_reexport_drift',{'rotated':True,'noise':True}),
    ('repeated_rotation',{'n':24,'repeated':True,'rotated':True}),
    ('sparse_8_of_80_reexport',{'n':80,'stable':8,'noise':True}),
]:
    a,b,r,t=scenario(**kwargs);started=perf_counter()
    proposal=propose_from_stage1(a,b,[],range(len(a)),range(len(b)),.01)
    registered=bool(proposal and proposal.get('status')=='registered')
    frame_error=None
    if registered:
        rr=np.asarray(proposal['rotation_B_to_A']);tt=np.asarray(proposal['translation_B_to_A_mm'])
        frame_error=float(np.linalg.norm(rr@r-np.eye(3))+np.linalg.norm(rr@t+tt))
    results.append({'case':name,'registered':registered,'correct_frame':registered and frame_error<1e-5,
                    'frame_error':frame_error,'seconds':round(perf_counter()-started,4),
                    'native_certified_pairs':len((proposal or {}).get('certified_pairs',[]))})
output={'label':sys.argv[1],'synthetic_cases':results,
        'correct_frames':sum(r['correct_frame'] for r in results),'total':len(results)}
Path(sys.argv[2]).write_text(json.dumps(output,indent=2),encoding='utf-8')
print(json.dumps(output))
