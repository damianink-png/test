"""OCCT Common glue mode diagnostic for invalid contact Boolean pairs."""
import io,sys,zipfile,urllib.request,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from dsac29.step_io import load_step
from dsac29.geometry import _basis_rotations,_precise_world_bounds,_bounds_compatible,transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BOPAlgo import BOPAlgo_GlueEnum
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
url="https://raw.githubusercontent.com/Open-Lab-Starter-Kit/OLSK-Small-CNC/cae066fa5b78b596743e1f2e432b93539cba8c24/OLSK_Small_CNC_V2/OLSK%20small%20CNC%20v2_Workshop.step.zip"
data=urllib.request.urlopen(url,timeout=120).read()
with zipfile.ZipFile(io.BytesIO(data)) as z:
    name=next(n for n in z.namelist() if n.endswith("OLSK small CNC v2_Workshop.step") and "__MACOSX/" not in n)
    Path("olsk_glue.step").write_bytes(z.read(name))
parts=load_step("olsk_glue.step",max_solids=5000)
for i,j in [(102,104),(100,106)]:
    a,b=parts[i],parts[j]
    print("PAIR",i,j,a.name,b.name,"vol",a.volume,b.volume,flush=True)
    checked=set()
    for R in [np.eye(3),*_basis_rotations(a,b)]:
        if tuple(np.round(R.ravel(),9)) in checked:continue
        checked.add(tuple(np.round(R.ravel(),9)))
        moved=transform(b.shape,R,a.center-R@b.center)
        if not _bounds_compatible(_precise_world_bounds(a.shape),_precise_world_bounds(moved),.01):continue
        for mode,glue in (("off",BOPAlgo_GlueEnum.BOPAlgo_GlueOff),("shift",BOPAlgo_GlueEnum.BOPAlgo_GlueShift),("full",BOPAlgo_GlueEnum.BOPAlgo_GlueFull)):
            for fuzzy in [1e-6,1e-4,1e-3]:
                try:
                    op=BRepAlgoAPI_Common(a.shape,moved)
                    op.SetFuzzyValue(fuzzy)
                    op.SetGlue(glue)
                    before=time.perf_counter();op.Build();elapsed=time.perf_counter()-before
                    volume=None
                    if op.IsDone():
                        p=GProp_GProps();BRepGProp.VolumeProperties_s(op.Shape(),p);volume=p.Mass()
                    print("GLUE",mode,"FUZZ",fuzzy,"done",op.IsDone(),"volume",volume,"seconds",round(elapsed,3),flush=True)
                except Exception as e:print("GLUE_ERROR",mode,fuzzy,repr(e),flush=True)
        break
print("GLUE_DIAGNOSTIC_COMPLETE",flush=True)
