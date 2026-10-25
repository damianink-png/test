"""RC6 regression: fast wire indexing must not grant equality by descriptors."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf, gp_Vec
from dsac29.geometry import describe
from dsac29.step_reexport_tolerance import reexport_equivalent_world

def box(x=12):
    return BRepPrimAPI_MakeBox(x,17,19).Shape()

def holed(radius=2):
    from OCP.gp import gp_Ax2,gp_Pnt,gp_Dir
    cutter=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(6,8,-2),gp_Dir(0,0,1)),radius,24).Shape()
    cut=BRepAlgoAPI_Cut(box(),cutter)
    cut.Build()
    assert cut.IsDone()
    return cut.Shape()

def verified(a,b):
    return reexport_equivalent_world(describe(a,'A','A'),describe(b,'B','B'),.01,allow_boolean=False)

def test_equal_independent_boxes():
    assert verified(box(),box())

def test_changed_box_not_equal():
    assert not verified(box(),box(12.5))

def test_equal_independent_holed_solids():
    assert verified(holed(),holed())

def test_changed_hole_not_equal():
    assert not verified(holed(2),holed(2.5))

def test_displaced_holed_solid_not_equal():
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(2,0,0))
    assert not verified(holed(),BRepBuilderAPI_Transform(holed(),tr,True).Shape())
