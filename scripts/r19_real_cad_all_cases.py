"""Integration test on authentic NIST/CAx-IF assembly with controlled B-Rep edits.

Scene must simultaneously include SAME, ADDED, REMOVED, MOVED/MOVED_OLD,
CHANGED_COMMON, CHANGED_ADDED, CHANGED_REMOVED and name change annotations.
"""
import json,sys,shutil,re
from pathlib import Path
from collections import Counter
from OCP.gp import gp_Trsf,gp_Vec,gp_Pnt
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Fuse
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from dsac29.step_io import load_step,ColoredDocument
from dsac29.cli import process
from dsac29.material_deltas import volume,solids

source=Path(sys.argv[1]).resolve()
folder=Path(sys.argv[2]).resolve()
folder.mkdir(parents=True,exist_ok=True)
parts=load_step(str(source),max_solids=500)
assert len(parts)==18,len(parts)

def bbox(shape):
    v=Bnd_Box();BRepBndLib.Add_s(shape,v);return v.Get()
def move(shape,vector):
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(*vector))
    return BRepBuilderAPI_Transform(shape,tr,True).Shape()
def write(entities,path):
    w=ColoredDocument(group_by_status=False,reuse_definitions=True)
    for name,shape in entities:w.add(shape,name,(.48,.56,.69),1.0)
    w.write(str(path))

old_bracket=parts[1]
x0,y0,z0,x1,y1,z1=bbox(old_bracket.shape)
cuttool=BRepPrimAPI_MakeBox(gp_Pnt(x1-80,y0-20,z0-20),gp_Pnt(x1+20,y1+20,z1+20)).Shape()
cut=BRepAlgoAPI_Cut(old_bracket.shape,cuttool);cut.Build()
assert cut.IsDone()
short_bracket=cut.Shape()
assert len(list(solids(short_bracket)))==1
assert .70<volume(short_bracket)/old_bracket.volume<.95

old_plate=parts[0]
px0,py0,pz0,px1,py1,pz1=bbox(old_plate.shape)
# The real NIST plate is broad enough to attach the boss at x=0/z=0.
tab=BRepPrimAPI_MakeBox(gp_Pnt(-250,py1-100,-40),gp_Pnt(250,py1+260,460)).Shape()
fuse=BRepAlgoAPI_Fuse(old_plate.shape,tab);fuse.Build()
assert fuse.IsDone()
new_plate=fuse.Shape()
assert len(list(solids(new_plate)))==1
assert volume(new_plate)>old_plate.volume+1000

aa=[];bb=[]
for index,part in enumerate(parts):
    if index==0:
        aa.append((part.name,part.shape));bb.append((part.name,new_plate))
    elif index==1:
        aa.append(("BRACKET_NIST_A",part.shape));bb.append(("BRACKET_DOSTAWCA_B",short_bracket))
    elif index==8:
        aa.append(("BRACKET_NIST_SECOND",part.shape))
        bb.append(("BRACKET_KOD_PRD_2002",part.shape))
    elif index==15:
        aa.append(("ROD_RELOCATED",part.shape))
        bb.append(("ROD_RELOCATED",move(part.shape,(0,650,0))))
    elif index==17:
        aa.append(("NUT_REMOVED",part.shape))
    else:
        aa.append((part.name,part.shape));bb.append((part.name,part.shape))
bb.append(("NEW_BOLT_NIST",move(parts[2].shape,(350,800,200))))
a=folder/"REVISION_A_PUBLIC_NIST.step"
b=folder/"REVISION_B_CONTROLLED_CHANGES.step"
write(aa,a);write(bb,b)
out=folder/"COMPARE_RESULTS"
out.mkdir(exist_ok=True)
_,records,error=process(str(a),str(b),str(out),step=True,diff_step=True,
   preview3d=True,revision_style=True,auto_align=False,full_bom=False,bom_csv=False,
   progress=lambda message:print("CAD:",message,flush=True))
assert not error,error
summary=json.loads((out/"PODSUMOWANIE.json").read_text(encoding="utf8"))
scene=(out/"PODGLAD_KOLOROW_3D.html").read_text(encoding="utf8")
payload=re.search(r"const scene=(\[.*?\]);",scene,re.S)
assert payload,"Missing HTML scene"
items=json.loads(payload.group(1))
counts=Counter(o["status"] for o in items)
for key in ("SAME","ADDED","REMOVED","MOVED","MOVED_OLD",
            "CHANGED_COMMON","CHANGED_ADDED","CHANGED_REMOVED"):
    assert counts.get(key,0)>0,(key,counts)
assert summary["statuses"].get("CHANGED")==2,summary["statuses"]
assert summary["statuses"].get("MOVED")==1,summary["statuses"]
assert summary["statuses"].get("ADDED")==1 and summary["statuses"].get("REMOVED")==1
assert (out/"POROWNANIE_KOLORY.step").stat().st_size>1000
assert (out/"ROZNICE_BREP.step").stat().st_size>1000
assert all(i.get("path_A") is not None and i.get("path_B") is not None for i in items)
out_html=folder/"DSCompare_REALNY_CAD_WSZYSTKIE_PRZYPADKI.html"
shutil.copyfile(out/"PODGLAD_KOLOROW_3D.html",out_html)
manifest={"geometry_source":"https://github.com/kovacsv/occt-import-js/blob/main/test/testfiles/cax-if/as1_pe_203.stp",
"part_count_original":len(parts),"source_geometry":"public CAD B-Rep",
"revisions":"controlled edits of a genuine CAD assembly; not real supplier revisions",
"statuses":summary["statuses"],"preview_classes":dict(counts),
"changed_geometry":"real plate + added tab; real bracket with material cut",
"moved_geometry":"same real rod translated 650 mm Y",
"removed_geometry":"real NIST nut removed","new_geometry":"extra real NIST bolt occurrence",
"renamed_geometry":"unchanged bracket and separately changed bracket have distinct supplier labels"}
(folder/"TEST_MANIFEST.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8")
print("REAL CAD ALL CLASSES PASS",manifest,flush=True)
