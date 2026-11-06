"""Synthetic policy-only benchmark; old=full scan, new=focused scan. No user files."""
import json,time,sys
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.geometry import describe
from dsac29.geometry_registry import GeometryRegistry
from dsac29.repeated_geometry import RepeatedMaterialPolicy
from dsac29 import native_guard
n=24
def model(depth,rev):
    return [describe(BRepPrimAPI_MakeBox(gp_Pnt(i*57.,0,0),10,20,5).Shape(),'UNCHANGED','same') for i in range(n)]+[describe(BRepPrimAPI_MakeBox(10,20,depth).Shape(),'DRAWING_123_REV_'+rev,'changed')]
a=model(7,'A');b=model(8,'B');calls=[0];native=native_guard.guarded_rigid
def count(*args,**kwargs):calls[0]+=1;return native(*args,**kwargs)
native_guard.guarded_rigid=count
start=time.perf_counter()
kwargs={} if sys.argv[1]=='old' else dict(old_ids={n},new_ids={n})
p=RepeatedMaterialPolicy(a,b,geometry_context=GeometryRegistry(),**kwargs)
assert p.allows(n,n)
print(json.dumps(dict(version=sys.argv[1],unchanged=n,old_size=p.sizes_a[n],new_size=p.sizes_b[n],native_calls=calls[0],seconds=time.perf_counter()-start)))
