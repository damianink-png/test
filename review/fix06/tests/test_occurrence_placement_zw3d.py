"""Verified repeat assignment after ZW3D assembly placement rounding."""
import numpy as np
from dataclasses import replace
from collections import Counter
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf, gp_Vec
from dsac29.geometry import describe
from dsac29 import compare as comparator
from dsac29.geometry_registry import GeometryRegistry


def moved(template, dx, name):
    tr=gp_Trsf();tr.SetTranslation(gp_Vec(float(dx),0.,0.))
    return replace(template,shape=template.shape.Moved(TopLoc_Location(tr)),
                   center=template.center+np.array([dx,0.,0.]),name=name)


def test_relative_placement_of_proven_instances_uses_actual_brep_tolerance():
    old=describe(BRepPrimAPI_MakeBox(10.,12.,20.).Shape(),'PROFILE','old')
    new=describe(BRepPrimAPI_MakeBox(10.,12.,20.).Shape(),'PROFILE','new')
    # Independent STEP export changed placement by 0.0002 mm; the previous
    # native-cache limit was 0.00001 mm, rejecting otherwise same instances.
    assert comparator._relative_location_is_same(
        moved(old,90.,'PROFILE'),old,moved(new,90.0002,'PROFILE'),new,.01)
    assert not comparator._relative_location_is_same(
        moved(old,90.,'PROFILE'),old,moved(new,90.03,'PROFILE'),new,.01)


def test_150_occurrences_use_one_proven_original_brep_and_one_to_one_positions(monkeypatch):
    a0=describe(BRepPrimAPI_MakeBox(10.,12.,20.).Shape(),'PROFILE','old')
    b0=describe(BRepPrimAPI_MakeBox(10.,12.,20.).Shape(),'PROFILE','new')
    a=[moved(a0,i*40.,'PROFILE') for i in range(150)]
    b=[moved(b0,i*40.+.0002,'PROFILE') for i in range(150)]
    # Separate export definitions cannot use IsSame/IsPartner between files.
    monkeypatch.setattr(GeometryRegistry,'same_definition',lambda *args:False)
    calls=[]
    def native_positive(*args,**kwargs):
        calls.append(1)
        return True
    monkeypatch.setattr(comparator,'guarded_world_equivalent',native_positive)
    monkeypatch.setattr(comparator,'guarded_world_reexport',native_positive)
    result=comparator.compare(a,b,revision_only=True)
    assert Counter(r.status for r in result)=={'SAME':150}
    assert len(calls)==1,'A proven pair must cover repeated CAD instances'
    assert len({r.a_index for r in result})==150
    assert len({r.b_index for r in result})==150
