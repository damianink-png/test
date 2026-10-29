"""Regression for exact analytic bounds; never use a bound as SAME proof."""
import os
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]/"dscompare_rc9_manual"
sys.path.insert(0,str(root))
from OCP.BRepPrimAPI import BRepPrimAPI_MakeTorus
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Shape
from dsac29.geometry import describe
from dsac29.step_reexport_tolerance import reexport_equivalent_world

source=(root/"dsac29"/"step_reexport_tolerance.py").read_text(encoding="utf-8")
assert "BRepBndLib.AddOptimal_s(a.shape,exact_a,False,False)" in source
assert "BRepBndLib.AddOptimal_s(b.shape,exact_b,False,False)" in source
assert "BRepBndLib.AddOptimal_s(f,bound,False,False)" in source
assert "surface_and_trim_proof" in source

shape=BRepPrimAPI_MakeTorus(10.,3.).Shape()
loose=Bnd_Box();BRepBndLib.Add_s(shape,loose,False)
optimal=Bnd_Box();BRepBndLib.AddOptimal_s(shape,optimal,False,False)
assert loose.Get()[3]-optimal.Get()[3] > .01, "Fixture must expose conservative AABB inflation"
a=describe(shape,"a","a")
same=describe(BRepPrimAPI_MakeTorus(10.,3.).Shape(),"same","same")
changed=describe(BRepPrimAPI_MakeTorus(10.,3.1).Shape(),"changed","changed")
assert reexport_equivalent_world(a,same,.01,allow_boolean=False)
assert not reexport_equivalent_world(a,changed,.01,allow_boolean=False)

# Optional real-world replay of Trident A327/B327 from run 40906508416.
folder=os.getenv("RC9_OPTIMAL_BREP_PAIR_DIR")
if folder:
    parts=[]
    for name in ("A","B"):
        shape=TopoDS_Shape()
        with (Path(folder)/(name+".brep")).open("rb") as stream:
            assert BRepTools.Read_s(shape,stream,BRep_Builder()) is not False
        parts.append(describe(shape,name,name))
    assert reexport_equivalent_world(*parts,.01,allow_boolean=False), "Captured CAD pair must pass full surface/trim proof"
print("PASS: analytic bounds prefilter, strict positive proof and changed geometry negative")
