from pathlib import Path
from dataclasses import replace
import sys, json, time, collections
import numpy as np
from OCP.gp import gp_Pnt
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Fuse
from dsac29.step_io import load_step
from dsac29.geometry import describe
from dsac29.compare import Record
from dsac29.material_deltas import calculate
from dsac29.alignment import _relocate
from dsac29.preview3d import create_preview
from dsac29.step_io import export_revision_step

source=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path('/mnt/data/r19work/NIST_AS1/REAL_ASSEMBLY_MOVED.step')
outdir=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else Path('/mnt/data/R18_DEMO_WSZYSTKIE_PRZYPADKI');outdir.mkdir(parents=True,exist_ok=True)
A=load_step(str(source));assert len(A)==18
B=[];mapping={};idx_changed=None
for i,p in enumerate(A):
    if i==3:continue # removed bolt's nut
    if i==0:
        remove_box=BRepPrimAPI_MakeBox(gp_Pnt(-1300,-1000,500),gp_Pnt(-850,-250,1050)).Shape()
        add_box=BRepPrimAPI_MakeBox(gp_Pnt(900,-550,600),gp_Pnt(1450,100,1150)).Shape()
        cut=BRepAlgoAPI_Cut(p.shape,remove_box);cut.Build();assert cut.IsDone()
        fuse=BRepAlgoAPI_Fuse(cut.Shape(),add_box);fuse.Build();assert fuse.IsDone()
        q=describe(fuse.Shape(),'PLATE_2026_B','AS1_PE_ASM/PLATE/PLATE_2026_B','NIST AS1 + kontrolowane zmiany OCC')
    elif i==2:
        q=_relocate(p,np.eye(3),np.array([680.,-100.,0.]))
        q=replace(q,path='AS1_PE_ASM/BOLTS/BOLT_PRZESTAWIONY')
    elif i==1:
        q=replace(p,name='L-BRACKET_PRZEMIANOWANY',path='AS1_PE_ASM/BRACKETS/L-BRACKET_PRZEMIANOWANY')
    else:q=p
    mapping[i]=len(B);B.append(q)
# New part is a translated copy of an authentic component, not a dummy cube.
new=_relocate(A[2],np.eye(3),np.array([1800.,800.,0.]))
new=replace(new,name='BOLT_DODANY_R2026',path='AS1_PE_ASM/NOWE/BOLT_DODANY_R2026')
added_idx=len(B);B.append(new)
records=[];regions={}
for i,p in enumerate(A):
    if i==3:
        records.append(Record(i,None,'REMOVED','Usunięty łącznik w rewizji B'))
    elif i==0:
        records.append(Record(i,mapping[i],'CHANGED','Zmiana geometrii i zmiana nazwy; ubyło i przybyło materiału',name_changed=True))
    elif i==2:
        records.append(Record(i,mapping[i],'MOVED','Element przeniesiony o +680 mm w X, -100 mm w Y'))
    elif i==1:
        records.append(Record(i,mapping[i],'SAME','B-Rep bez zmian; zmieniona nazwa dostawcy',name_changed=True))
    else:
        records.append(Record(i,mapping[i],'SAME','Bez zmian'))
records.append(Record(None,added_idx,'ADDED','Nowy element w rewizji B'))
changed_id=next(k for k,r in enumerate(records) if r.status=='CHANGED')
reg=calculate(A[0],B[0]);regions[changed_id]=reg
print('MATERIAL',reg.common_mm3,reg.added_mm3,reg.removed_mm3,flush=True)
assert reg.added_mm3>1000 and reg.removed_mm3>1000
colors={
'SAME':(22/255,163/255,74/255),
'ADDED':(37/255,99/255,235/255),
'REMOVED':(239/255,68/255,68/255),
'MOVED':(139/255,92/255,246/255),
'MOVED_OLD':(196/255,181/255,253/255),
'CHANGED_COMMON':(56/255,189/255,248/255),
'CHANGED_ADDED':(245/255,158/255,11/255),
'CHANGED_REMOVED':(190/255,18/255,60/255),
}
scene=outdir/'R18_PODGLAD_3D_WSZYSTKIE_PRZYPADKI.html'
t0=time.monotonic()
info=create_preview(str(scene),records,A,B,colors=colors,old_alpha=.40,material_regions=regions)
print('HTML',info,'SEC',time.monotonic()-t0,'BYTES',scene.stat().st_size,flush=True)
# Write independent metadata for auditing demo semantics.
rows=[dict(index=i,kind=r.status,original_name=A[r.a_index].name if r.a_index is not None else '',new_name=B[r.b_index].name if r.b_index is not None else '',name_changed=r.name_changed) for i,r in enumerate(records)]
meta={'model':'NIST/CAx-IF AS1-PE-203 (rzeczywisty publiczny STEP)',
      'scenario':'Kontrolowane zmiany na rzeczywistych bryłach OCP: nowy/usunięty/przestawiony/zmieniona geometria/zmieniona nazwa',
      'model_geometry_source':'https://github.com/kovacsv/occt-import-js/blob/main/test/testfiles/cax-if/as1_pe_203.stp',
      'source_parts':len(A),'comparison_records':len(records),'preview':info,
      'material':{'common_mm3':reg.common_mm3,'added_mm3':reg.added_mm3,'removed_mm3':reg.removed_mm3},
      'statuses':dict(collections.Counter(r.status for r in records)),
      'records':rows}
(outdir/'OPIS_TESTU.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf8')
print('STATUS',meta['statuses'],flush=True)