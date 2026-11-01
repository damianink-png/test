import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.compare import Record
from dsac29.report import produce

def box(name,x,y=0,width=12):
 tr=gp_Trsf();tr.SetTranslation(gp_Vec(x,y,0))
 return describe(BRepPrimAPI_MakeBox(width,14,18).Shape().Located(TopLoc_Location(tr)),name,'Złożenie demonstracyjne/'+name)
a=[box('Wspornik 01',0),box('Pokrywa stara',22),box('Uchwyt',44),box('Płyta',66,width=19),box('Usuwany detal',96),box('Do kontroli A',120)]
b=[box('Wspornik 01',0),box('Pokrywa nowa',22),box('Uchwyt',44,25),box('Płyta',66,width=15),box('Nowy detal',96,25),box('Do kontroli B',120)]
r=[Record(0,0,'SAME','Ta sama geometria'),Record(1,1,'RENAMED','Zmiana nazwy',name_changed=True),Record(2,2,'MOVED','Nowe położenie',delta_y=25,distance_mm=25),Record(3,3,'CHANGED','Zmniejszono szerokość płyty',volume_delta_mm3=-1008),Record(4,None,'REMOVED','Usunięto'),Record(None,4,'ADDED','Dodano'),Record(5,5,'UNCERTAIN','Wymaga weryfikacji')]
folder=(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'diagnostics/review06')/'demo'
result,error=produce(folder,a,b,r,generate_step=True,diff_step=False,preview3d=True,revision_style=True,full_bom=True,bom_csv=True,report_context={'A':'Rewizja_A.step','B':'Rewizja_B.step','alignment':{'applied':True,'translation_B_to_A_mm':[-507.4569,249.1752,-524.0],'rotation_B_to_A':[[1,0,0],[0,1,0],[0,0,1]]},'revision_overlap':{'incomplete':True,'reason':'Demonstracyjny brak potwierdzenia Common — nie jest wynikiem testu źródeł użytkownika.','failed_pair':{'a_index':5,'b_index':5}}},progress=lambda s:print(s,flush=True))
assert not error,error
assert (folder/'PODGLAD_KOLOROW_3D.html').exists()
print('DEMO',folder.resolve(),flush=True)
