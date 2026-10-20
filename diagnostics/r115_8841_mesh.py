"""Test independent two-sided high-resolution surface distance on OLSK terminal pairs."""
import io,sys,zipfile,urllib.request
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
sys.path.insert(0,str(Path(__file__).parent.resolve()))
from dsac29.step_io import load_step
from dsac29.geometry import _basis_rotations,_precise_world_bounds,_bounds_compatible,transform
from r115_mesh_check import check
url="https://raw.githubusercontent.com/Open-Lab-Starter-Kit/OLSK-Small-CNC/cae066fa5b78b596743e1f2e432b93539cba8c24/OLSK_Small_CNC_V2/OLSK%20small%20CNC%20v2_Workshop.step.zip"
data=urllib.request.urlopen(url,timeout=120).read()
with zipfile.ZipFile(io.BytesIO(data)) as z:
    name=next(n for n in z.namelist() if n.endswith("OLSK small CNC v2_Workshop.step") and "__MACOSX/" not in n)
    Path("OLSK_faces.step").write_bytes(z.read(name))
parts=load_step("OLSK_faces.step",max_solids=5000)
print("IMPORT",len(parts),flush=True)
for i,j in [(102,104),(100,106),(240,242),(102,110)]:
    a,b=parts[i],parts[j]
    print("PAIR",i,j,a.name,b.name,flush=True)
    keyset=set()
    for R in [np.eye(3),*_basis_rotations(a,b)]:
        key=tuple(np.round(R.ravel(),9))
        if key in keyset: continue
        keyset.add(key)
        moved=transform(b.shape,R,a.center-R@b.center)
        if not _bounds_compatible(_precise_world_bounds(a.shape),_precise_world_bounds(moved),.01):continue
        print("MESH",i,j,check(a.shape,moved,.008),flush=True)
        break
print("MESH_CHECK_COMPLETE",flush=True)
