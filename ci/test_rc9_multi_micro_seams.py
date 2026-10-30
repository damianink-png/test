"""Fail-closed synthetic regression for STEP world equivalence."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'))
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.step_reexport_tolerance import reexport_equivalent_world
def part(length=20,shift=0):
    s=BRepPrimAPI_MakeBox(length,11,9).Shape()
    if shift:
        t=gp_Trsf();t.SetTranslation(gp_Vec(shift,0,0))
        s=s.Moved(TopLoc_Location(t))
    return describe(s,'TEST','TEST')
a=part()
assert reexport_equivalent_world(a,part(),.01,allow_boolean=False)
assert not reexport_equivalent_world(a,part(20,.03),.01,allow_boolean=False)
assert not reexport_equivalent_world(a,part(20.1),.01,allow_boolean=False)
print('PASS: same geometry accepted; shifted and material-changed rejected')
