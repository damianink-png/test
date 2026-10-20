"""Compare OCCT settings without modifying geometry. Public OLSK STEP only."""
from pathlib import Path
import sys,time,json,io,zipfile,urllib.request
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from dsac29.step_io import load_step
from dsac29 import geometry
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
url="https://raw.githubusercontent.com/Open-Lab-Starter-Kit/OLSK-Small-CNC/cae066fa5b78b596743e1f2e432b93539cba8c24/OLSK_Small_CNC_V2/OLSK%20small%20CNC%20v2_Workshop.step.zip"
blob=urllib.request.urlopen(url,timeout=120).read()
with zipfile.ZipFile(io.BytesIO(blob)) as z:
    name=next(n for n in z.namelist() if n.endswith("OLSK small CNC v2_Workshop.step") and "__MACOSX/" not in n)
    Path("OLSK_modes.step").write_bytes(z.read(name))
parts=load_step("OLSK_modes.step",max_solids=5000)
print("LOADED",len(parts),flush=True)
a,b=parts[102],parts[104]
print("PAIR",a.name,b.name,a.volume,b.volume,flush=True)
modes=[
 ("default",{}),
 ("no-inverted",{"inverted":False}),
 ("non-destructive",{"nondestructive":True}),
 ("obb",{"obb":True}),
 ("no-inverted-and-obb",{"inverted":False,"obb":True}),
 ("fuzzy-zero",{"fuzzy":0}),
 ("fuzzy-small",{"fuzzy":1e-7}),
 ("fuzzy-large",{"fuzzy":1e-3}),
]
for label,opts in modes:
    calls=[0];start=time.perf_counter()
    def test_common(left,right,tolerance):
        calls[0]+=1
        alg=BRepAlgoAPI_Common(left,right)
        alg.SetFuzzyValue(opts.get("fuzzy",max(tolerance/100,1e-6)))
        if "inverted" in opts:alg.SetCheckInverted(opts["inverted"])
        if "nondestructive" in opts:alg.SetNonDestructive(opts["nondestructive"])
        if "obb" in opts:alg.SetUseOBB(opts["obb"])
        alg.Build()
        if not alg.IsDone():raise RuntimeError("MODE_COMMON_FAILED")
        props=GProp_GProps();BRepGProp.VolumeProperties_s(alg.Shape(),props)
        return max(0.,float(props.Mass()))
    geometry._common_volume=test_common
    # No alternative Cut here: measure Common method itself.
    geometry._cut_volume=lambda *args: (_ for _ in ()).throw(RuntimeError("no Cut in this experiment"))
    try:
        answer=geometry.equivalent_rigid(a,b)
        print("MODE",label,"answer",answer[0],"calls",calls[0],"sec",round(time.perf_counter()-start,2),flush=True)
    except Exception as e:
        print("MODE",label,"error",str(e),"calls",calls[0],"sec",round(time.perf_counter()-start,2),flush=True)
print("MODES_COMPLETED",flush=True)
