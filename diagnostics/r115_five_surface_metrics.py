"""Measure full bidirectional nearest CAD surface residuals for five unresolved OLSK contacts."""
import io,sys,zipfile,urllib.request,time,json
from pathlib import Path
import numpy as np, vtk
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from dsac29.step_io import load_step
from dsac29.geometry import _basis_rotations,_precise_world_bounds,_bounds_compatible,transform
from dsac29.surface_witness import _surface_mesh
url="https://raw.githubusercontent.com/Open-Lab-Starter-Kit/OLSK-Small-CNC/cae066fa5b78b596743e1f2e432b93539cba8c24/OLSK_Small_CNC_V2/OLSK%20small%20CNC%20v2_Workshop.step.zip"
blob=urllib.request.urlopen(url,timeout=120).read()
with zipfile.ZipFile(io.BytesIO(blob)) as z:
    name=next(n for n in z.namelist() if n.endswith("OLSK small CNC v2_Workshop.step") and "__MACOSX/" not in n)
    Path("OLSK_5_contacts.step").write_bytes(z.read(name))
parts=load_step("OLSK_5_contacts.step",max_solids=5000)
print("IMPORT",len(parts),flush=True)
def metrics(samples,target):
    l=vtk.vtkStaticCellLocator();l.SetDataSet(target);l.BuildLocator()
    cp=[0.,0.,0.];cid=vtk.mutable(0);sid=vtk.mutable(0);dist=vtk.mutable(0.)
    all_dist=[]
    for sample in samples:
        l.FindClosestPoint(sample,cp,cid,sid,dist)
        all_dist.append(float(dist)**.5)
    return {"max":round(max(all_dist),9),"p99":round(float(np.percentile(all_dist,99)),9),
            "gt_008":sum(d>.008 for d in all_dist),"gt_010":sum(d>.010 for d in all_dist),
            "gt_012":sum(d>.012 for d in all_dist),"count":len(all_dist)}
pairs=[(102,105),(102,106),(102,107),(100,108),(100,109),(102,104),(100,106)]
for i,j in pairs:
    a,b=parts[i],parts[j]
    found=False;checked=set()
    for R in [np.eye(3),*_basis_rotations(a,b)]:
        k=tuple(np.round(R.ravel(),9))
        if k in checked:continue
        checked.add(k)
        moved=transform(b.shape,R,a.center-R@b.center)
        if not _bounds_compatible(_precise_world_bounds(a.shape),_precise_world_bounds(moved),.01):continue
        ma,sa=_surface_mesh(a.shape,.001,40000)
        mb,sb=_surface_mesh(moved,.001,40000)
        print("CONTACT",i,j,a.name,b.name,json.dumps({"A_to_B":metrics(sa,mb),"B_to_A":metrics(sb,ma)},ensure_ascii=False),flush=True)
        found=True;break
    if not found:print("NO_ALIGNED_FRAME",i,j,flush=True)
print("CONTACT_METRICS_COMPLETE",flush=True)
