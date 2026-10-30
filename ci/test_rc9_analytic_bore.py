"""Strict cone canonicalization and fail-closed bore recognizer regressions.

The large Trident/Voron real-BRep tests remain authoritative for material
classification, STEP and HTML; these unit tests never replace them.
"""
import math
import sys
from pathlib import Path

# The workflow invokes this file directly from dscompare_rc9_manual.
# Python sets sys.path[0] to ci/, so explicitly include the extracted app.
# Keep all geometry assertions and fail-closed checks unchanged.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dscompare_rc9_manual'))

import numpy as np
from OCP.gp import gp_Ax3,gp_Pnt,gp_Dir,gp_Cone
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.parametric_identity import surface_equal
from dsac29.analytic_bore_delta import try_added_bore

p=gp_Pnt(0,0,0)
a=gp_Cone(gp_Ax3(p,gp_Dir(0,0,1)),math.pi/4,1)
b=gp_Cone(gp_Ax3(p,gp_Dir(0,0,-1)),-math.pi/4,1)
c=gp_Cone(gp_Ax3(p,gp_Dir(0,0,-1)),math.pi/4,1)
d=gp_Cone(gp_Ax3(p,gp_Dir(0,0,-1)),-math.pi/4,1.1)
faces=[BRepBuilderAPI_MakeFace(x,0,2*math.pi,0,.3).Face() for x in (a,b,c,d)]
box=Bnd_Box();BRepBndLib.AddOptimal_s(faces[0],box,False,False)
bounds=np.array(box.Get(),dtype=float)
assert surface_equal(faces[0],faces[1],bounds,1e-6), 'Equivalent reversed cone parametrization rejected'
assert not surface_equal(faces[0],faces[2],bounds,1e-6), 'Opposite cone nappe incorrectly accepted'
assert not surface_equal(faces[0],faces[3],bounds,1e-6), 'Changed cone radius incorrectly accepted'

s=BRepPrimAPI_MakeBox(10,10,10).Shape()
assert try_added_bore(s,s,.01) is None, 'Identical shapes cannot be a changed bore'
print('RC9_CONE_AND_BORE_FAIL_CLOSED_PASS')
