"""R11.24 regression: moved only for groups with preserved multiplicity."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf,gp_Vec
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe
from dsac29.compare import compare
from dsac29.geometry_registry import GeometryRegistry
from dsac29.revision_rules import classify_revisions

def model(name,x):
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(float(x),0,0))
    return describe(BRepPrimAPI_MakeBox(20,11,9).Shape().Located(TopLoc_Location(tr)),name,name)

def run(a,b):
    ctx=GeometryRegistry()
    records=compare(a,b,revision_only=True,geometry_context=ctx)
    return classify_revisions(a,b,records,0.01,geometry_context=ctx)

equal=run([model('PLATE',0)],[model('PLATE',35)])
assert len(equal)==1 and equal[0].status=='MOVED',equal
unequal=run([model('PLATE',0)],[model('PLATE',35),model('PLATE',70)])
assert len(unequal)==3,unequal
assert all(x.status!='MOVED' for x in unequal),unequal
assert sum(x.status=='REMOVED' for x in unequal)==1,unequal
assert sum(x.status=='ADDED' for x in unequal)==2,unequal
print('R11.24 PASS: moved only on equal-occurrence 1-to-1 geometry, unequal-count groups are added+removed')
