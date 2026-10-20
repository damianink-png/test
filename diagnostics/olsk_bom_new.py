"""Benchmark exact BOM checks only on public OLSK using pinned newer OCCT."""
import sys,zipfile,io,urllib.request,time,json
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from dsac29.step_io import load_step
from dsac29.geometry_registry import GeometryRegistry
from dsac29.report import geometry_groups
url="https://raw.githubusercontent.com/Open-Lab-Starter-Kit/OLSK-Small-CNC/cae066fa5b78b596743e1f2e432b93539cba8c24/OLSK_Small_CNC_V2/OLSK%20small%20CNC%20v2_Workshop.step.zip"
start=time.perf_counter()
raw=urllib.request.urlopen(url,timeout=120).read()
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    name=next(n for n in z.namelist() if n.endswith("OLSK small CNC v2_Workshop.step") and "__MACOSX/" not in n)
    Path("OLSK_bom_input.step").write_bytes(z.read(name))
parts=load_step("OLSK_bom_input.step",max_solids=5000)
print("IMPORT",len(parts),round(time.perf_counter()-start,2),flush=True)
registry=GeometryRegistry()
groups=geometry_groups(parts,progress=lambda s:print("PROGRESS",round(time.perf_counter()-start,2),s,flush=True),context=registry)
result={"solids":len(parts),"groups":len(groups),"warnings":len(registry.bom_errors),"errors":registry.bom_errors[:30],"stats":dict(registry.stats),"seconds":round(time.perf_counter()-start,2)}
print("RESULT",json.dumps(result,ensure_ascii=False),flush=True)
assert sum(map(len,groups))==len(parts)
assert not registry.bom_errors,'OLSK BOM has unresolved geometric comparisons'
print("R114_PINNED_OCCT_OLSK_BOM_PASS",flush=True)
