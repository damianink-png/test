"""Inspect only failed aligned OCCT intersection on public OLSK terminal contacts."""
import io,sys,zipfile,urllib.request,time,json
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from dsac29.step_io import load_step
from dsac29.geometry import _basis_rotations,_precise_world_bounds,_bounds_compatible,transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf,gp_Vec
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.ShapeAnalysis import ShapeAnalysis_ShapeTolerance
url="https://raw.githubusercontent.com/Open-Lab-Starter-Kit/OLSK-Small-CNC/cae066fa5b78b596743e1f2e432b93539cba8c24/OLSK_Small_CNC_V2/OLSK%20small%20CNC%20v2_Workshop.step.zip"
data=urllib.request.urlopen(url,timeout=120).read()
with zipfile.ZipFile(io.BytesIO(data)) as z:
    p=next(n for n in z.namelist() if n.endswith("OLSK small CNC v2_Workshop.step") and "__MACOSX/" not in n)
    Path("olsk_contact.step").write_bytes(z.read(p))
parts=load_step("olsk_contact.step",max_solids=5000)
for i,j in [(102,104),(100,106)]:
    a,b=parts[i],parts[j]
    print("PAIR",i,j,a.name,b.name,"vol",a.volume,b.volume,flush=True)
    bounds=_precise_world_bounds(a.shape)
    k=0
    for R in [np.eye(3),*_basis_rotations(a,b)]:
        t=a.center-R@b.center;moved=transform(b.shape,R,t)
        if not _bounds_compatible(bounds,_precise_world_bounds(moved),.01):continue
        k+=1;print("ALIGNED",k,"center_diff",np.linalg.norm(a.center-(R@b.center+t)),flush=True)
        for axis,eps in [(0,0),(0,1e-6),(0,1e-5),(0,1e-4),(0,1e-3),(1,1e-5),(2,1e-5),(0,-1e-5)]:
            sh=moved
            if eps:
                tr=gp_Trsf(); vec=[0.,0.,0.];vec[axis]=eps
                tr.SetTranslation(gp_Vec(*vec))
                sh=BRepBuilderAPI_Transform(moved,tr,True).Shape()
            try:
                op=BRepAlgoAPI_Common(a.shape,sh)
                op.SetFuzzyValue(1e-4)
                tic=time.perf_counter();op.Build();secs=round(time.perf_counter()-tic,2)
                done=op.IsDone(); mass=None
                if done:
                    props=GProp_GProps();BRepGProp.VolumeProperties_s(op.Shape(),props);mass=props.Mass()
                print("TRY",axis,eps,done,mass,secs,flush=True)
            except Exception as e:print("TRY_ERROR",axis,eps,repr(e),flush=True)
        break
    print("ALIGNED_COUNT",k,flush=True)
print("CONTACT_DIAGNOSTIC_COMPLETE")
