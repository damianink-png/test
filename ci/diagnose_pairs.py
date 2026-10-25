import sys,json,time,urllib.request,zipfile,collections
from pathlib import Path
from dsac29.step_io import load_step,ColoredDocument
from dsac29.alignment import _relocate
from dsac29.step_reexport_tolerance import reexport_equivalent_world,shape_valid,coarse_candidate
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from OCP.BRepTools import BRepTools
import numpy as np
root=Path('evidence');root.mkdir(exist_ok=True)
url='https://raw.githubusercontent.com/VoronDesign/Voron-Trident/1a49bdc2c524cd6f4491a01e8fd566d0bd6acd0a/CAD/trident_assembly.step.zip'
urllib.request.urlretrieve(url,'model.zip')
with zipfile.ZipFile('model.zip') as z:z.extractall('model')
a=load_step(str(max(Path('model').rglob('*.step'),key=lambda p:p.stat().st_size)))
writer=ColoredDocument(group_by_status=False,reuse_definitions=True);tr=gp_Trsf();tr.SetTranslation(gp_Vec(1275,-395,210))
for p in a:writer.add(p.shape.Moved(TopLoc_Location(tr)),p.name,(.3,.5,.8),1.)
writer.write('moved.step');b=load_step('moved.step');offset=np.array([-1275.,395.,-210.]);b=[_relocate(p,np.eye(3),offset) for p in b]
counts=collections.Counter();fail=[];used=set()
for i,p in enumerate(a):
 j=min((j for j in range(len(b)) if j not in used),key=lambda j:np.linalg.norm(p.center-b[j].center));used.add(j);q=b[j]
 va,vb=shape_valid(p.shape),shape_valid(q.shape);key='valid' if va and vb else f'invalid_{va}_{vb}'
 good=reexport_equivalent_world(p,q,.01,allow_boolean=False);counts[key+('_proof' if good else '_failed')]+=1
 if not good and len(fail)<15:
  BRepTools.Write_s(p.shape,str(root/f'A_{i}.brep'));BRepTools.Write_s(q.shape,str(root/f'B_{i}.brep'))
  fail.append(dict(i=i,j=j,name=p.name,valid_A=va,valid_B=vb,coarse=bool(coarse_candidate(p,q,.01)),center=float(np.linalg.norm(p.center-q.center))))
 if i%100==0:print(i,dict(counts),flush=True)
 (root/'diagnosis.json').write_text(json.dumps({'counts':dict(counts),'failures':fail},indent=2))
print(dict(counts),flush=True)
