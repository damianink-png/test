"""Fail-closed source-tolerance budget regressions (no CAD files required)."""
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dscompare_rc9_manual'))
from dsac29 import brep_safety
class FakeShape:
    def IsNull(self):return False
def exercise(before,after, *, cap=None, proven=True):
    original,repaired=FakeShape(),FakeShape()
    old={"vertex":before,"edge":before,"face":1e-7}
    new={"vertex":after,"edge":after,"face":1e-7}
    with patch.object(brep_safety,'is_valid',side_effect=lambda x:x is repaired), \
         patch.object(brep_safety,'topology_tolerances',side_effect=lambda x:old if x is original else new), \
         patch.object(brep_safety,'_deep_copy',return_value=FakeShape()), \
         patch.object(brep_safety,'_shape_fix',new=lambda shape,tolerance:repaired), \
         patch.object(brep_safety,'_wire_fix',new=lambda shape,tolerance:repaired), \
         patch.object(brep_safety,'_strict_original_boundary_proof',return_value=proven) as proof:
        try:
            got,changed=brep_safety.validated_copy(original,.005,max_source_tolerance=cap)
            assert got is repaired and changed is True
            return True,proof.call_count
        except brep_safety.UnprovenRepair:
            return False,proof.call_count
assert exercise(.0098271236283297,.009827123628331472,cap=.01)==(True,1)
assert exercise(.0098271236283297,.009827123628331472)==(False,0)
assert exercise(.0101,.0101,cap=.01)==(False,0)
assert exercise(.009827,.009829,cap=.01)==(False,0)
assert exercise(.009827,.009827,cap=.01,proven=False)==(False,2)
try:
    with patch.object(brep_safety,'is_valid',return_value=False):
        brep_safety.validated_copy(FakeShape(),.005,max_source_tolerance=.0101)
except ValueError:pass
else:raise AssertionError('Total tolerance budget >0.01 must be rejected')
print('PASS: source tolerance budget and independent oriented boundary proof')
