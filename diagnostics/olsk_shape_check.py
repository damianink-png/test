"""Diagnose input B-Rep validity and safe healing of public OLSK solids."""
import sys,zipfile,io,urllib.request,time,json
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from dsac29.step_io import load_step
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.ShapeFix import ShapeFix_Shape
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
url="https://raw.githubusercontent.com/Open-Lab-Starter-Kit/OLSK-Small-CNC/cae066fa5b78b596743e1f2e432b93539cba8c24/OLSK_Small_CNC_V2/OLSK%20small%20CNC%20v2_Workshop.step.zip"
t=time.perf_counter()
data=urllib.request.urlopen(url,timeout=120).read()
with zipfile.ZipFile(io.BytesIO(data)) as z:
    name=next(n for n in z.namelist() if n.endswith("OLSK small CNC v2_Workshop.step") and "__MACOSX/" not in n)
    Path("OLSK_diagnostic.step").write_bytes(z.read(name))
parts=load_step("OLSK_diagnostic.step",max_solids=5000)
print("LOADED",len(parts),round(time.perf_counter()-t,2),flush=True)
for marker in ["HGR15T800H_FILE_1","fath_2_2","8841T42","3000-b-2rs-tvh","Side beam cover"]:
    found=[(i,x) for i,x in enumerate(parts) if marker.lower() in x.name.lower()]
    print("PATTERN",marker,"COUNT",len(found),flush=True)
    for i,x in found[:8]:
        t1=time.perf_counter()
        try:
            valid=BRepCheck_Analyzer(x.shape,False).IsValid()
            row={"index":i,"name":x.name,"volume":round(x.volume,6),"valid_before":bool(valid),"check_seconds":round(time.perf_counter()-t1,3)}
            if not valid:
                t2=time.perf_counter()
                fixer=ShapeFix_Shape(x.shape);fixer.SetPrecision(1e-7);performed=fixer.Perform();fixed=fixer.Shape()
                vp=GProp_GProps();BRepGProp.VolumeProperties_s(fixed,vp)
                ap=GProp_GProps();BRepGProp.SurfaceProperties_s(fixed,ap)
                row.update(heal_performed=bool(performed),heal_seconds=round(time.perf_counter()-t2,2),valid_after=bool(BRepCheck_Analyzer(fixed,False).IsValid()),volume_diff=round(vp.Mass()-x.volume,8),area_diff=round(ap.Mass()-x.area,8))
            print(json.dumps(row,ensure_ascii=False),flush=True)
        except Exception as exc:print("ERROR",i,repr(exc),flush=True)
print("DIAG_COMPLETE",flush=True)
