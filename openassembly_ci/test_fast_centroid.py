"""Validate exact world-centroid reuse for repeated rigid XCAF occurrences."""
import math
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf, gp_Vec, gp_Ax1, gp_Dir, gp_Pnt
from openassembly.stepio import _measure, _local_measure

def integral_center(shape):
    prop = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, prop)
    p = prop.CentreOfMass()
    return p.X(), p.Y(), p.Z()

def assert_centroid_equal(shape, world):
    data = _local_measure(shape)
    result = _measure(shape, world, data)
    assert math.dist(result[2], integral_center(world)) < 1e-7
    assert result[0] > 0

def test_location_translation_and_rotation():
    shape = BRepPrimAPI_MakeBox(12., 23., 34.).Shape()
    assert_centroid_equal(shape, shape)
    for angle in (0.0, 0.4, 1.2, 2.7):
        t = gp_Trsf()
        t.SetRotation(gp_Ax1(gp_Pnt(0., 0., 0.), gp_Dir(1., 1., 1.)), angle)
        t.SetTranslationPart(gp_Vec(53., -11., 27.))
        world = shape.Moved(TopLoc_Location(t))
        assert shape.IsPartner(world)
        assert_centroid_equal(shape, world)

def test_non_partner_fallback():
    shape = BRepPrimAPI_MakeBox(12., 23., 34.).Shape()
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(5., 7., 9.))
    copied = BRepBuilderAPI_Transform(shape, t, True).Shape()
    assert not shape.IsPartner(copied)
    assert_centroid_equal(shape, copied)
