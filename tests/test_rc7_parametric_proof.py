"""RC7: parametric identity is a positive proof, not a loose similarity guess."""
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.gp import gp_Pnt
from dsac29.geometry import describe
from dsac29.step_reexport_tolerance import reexport_equivalent_world


def test_identical_independently_constructed_boxes_are_proven():
    a=describe(BRepPrimAPI_MakeBox(20.,15.,10.).Shape(),"A","A")
    b=describe(BRepPrimAPI_MakeBox(20.,15.,10.).Shape(),"B","B")
    assert reexport_equivalent_world(a,b,.01,allow_boolean=False)


def test_real_cut_feature_is_not_proven_equal():
    base=BRepPrimAPI_MakeBox(20.,15.,10.).Shape()
    tool=BRepPrimAPI_MakeBox(gp_Pnt(18.,6.,0.),gp_Pnt(20.,9.,10.)).Shape()
    cut=BRepAlgoAPI_Cut(base,tool)
    cut.Build()
    assert cut.IsDone()
    a=describe(base,"A","A")
    b=describe(cut.Shape(),"B","B")
    assert not reexport_equivalent_world(a,b,.01,allow_boolean=False)
