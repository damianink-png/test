"""Conservative whole-frame performance regression on 380 native CAD solids."""
import sys,time
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf,gp_Vec
from dsac29.geometry import describe
from dsac29.alignment import align_assembly
from dsac29.registration_gate import frame_support
from dsac29.compare import compare
shape=BRepPrimAPI_MakeBox(5,7,9).Shape()
def part(i,offset=0):
 tr=gp_Trsf();tr.SetTranslation(gp_Vec(i*27+offset,(i%15)*60,(i//15)*12))
 return describe(shape.Located(TopLoc_Location(tr)),'PROFIL','PROFIL')
a=[part(i) for i in range(380)]
for glob in (0,1000):
 b=[part(i,glob+(0 if i<231 else 14)) for i in range(380)]
 start=time.perf_counter()
 aligned,info=align_assembly(a,b,.01)
 assert info['status']==('already_aligned' if not glob else 'registered'),info
 assert np.allclose(info['translation_B_to_A_mm'],[-glob,0,0]),info
 assert frame_support(a,aligned,.01,verify_all=True)['count']==231
 rec=compare(a,aligned,.01,revision_only=True,exact_serialization=True)
 assert sum(r.status=='SAME' for r in rec)==231
 print('PASS R9',glob,'mm',round(time.perf_counter()-start,2),'s')
print('R9 full assembly 380/231 regression PASS')
