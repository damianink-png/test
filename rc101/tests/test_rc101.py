import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from dsac29.geometry import describe
from dsac29.compare import Record,compare
from dsac29.residual_identity import recover
from dsac29.native_guard import NativeGeometryFailure

def part(length=20):return describe(BRepPrimAPI_MakeBox(length,10,10).Shape(),'bracket','assembly/bracket')
def records():return [Record(0,None,'REMOVED',''),Record(None,0,'ADDED','')]

def test_rescue_descriptor_drift_requires_real_proof():
 a,b=part(),part();b.center+=np.array([.05,0,0])
 result=recover([a],[b],records(),.01)
 assert [r.status for r in result]==['SAME']

def test_real_geometry_change_never_same():
 a,b=part(),part(20.1)
 result=recover([a],[b],records(),.01)
 assert [r.status for r in result]==['REMOVED','ADDED']

def test_ambiguous_occurrences_not_guessed(monkeypatch):
 import dsac29.residual_identity as m
 monkeypatch.setattr(m,'guarded_world_reexport',lambda *a,**k:pytest.fail('ambiguous proof'))
 rec=[Record(0,None,'REMOVED',''),Record(None,0,'ADDED',''),Record(None,1,'ADDED','')]
 assert recover([part()],[part(),part()],rec,.01)==rec

def test_failed_proof_aborts(monkeypatch):
 import dsac29.residual_identity as m
 def failed(*args,**kwargs):raise NativeGeometryFailure('timeout')
 monkeypatch.setattr(m,'guarded_world_reexport',failed)
 with pytest.raises(NativeGeometryFailure):recover([part()],[part()],records(),.01)

def test_aligned_search_uses_proof_radius():
 a,b=part(),part();b.center+=np.array([.05,0,0])
 result=compare([a],[b],.01,revision_only=True,step_reexport_tolerance=True)
 assert len(result)==1 and result[0].status=='SAME'
