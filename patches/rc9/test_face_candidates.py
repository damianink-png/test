"""Regression: a face centroid is only a lookup hint, never B-Rep proof."""
import numpy as np
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29 import step_reexport_tolerance as reexp


def test_face_centroid_is_hint_not_geometry_proof(monkeypatch):
    shape=BRepPrimAPI_MakeBox(10,20,30).Shape()
    a=describe(shape,'A','A')
    b=describe(shape,'B','B')
    original=reexp._faces
    def perturbed(part):
        faces=original(part)
        if part is b:
            typ,orientation,area,center,bbox=faces[0]
            faces[0]=(typ,orientation,area,center+np.array([.05,0,0]),bbox)
        return faces
    monkeypatch.setattr(reexp,'_faces',perturbed)
    assert reexp.reexport_equivalent_world(a,b,.01,allow_boolean=False)


def test_different_geometry_still_rejected():
    a=describe(BRepPrimAPI_MakeBox(10,20,30).Shape(),'A','A')
    b=describe(BRepPrimAPI_MakeBox(10,20,30.02).Shape(),'B','B')
    assert not reexp.reexport_equivalent_world(a,b,.01,allow_boolean=False)
