"""OCP regression: failed native proof cannot abort or silently misclassify other parts."""
import importlib
import unittest
from unittest.mock import patch
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29.geometry import describe
from dsac29.native_guard import NativeGeometryFailure

comparison=importlib.import_module('dsac29.compare')

def make_parts():
    a=[describe(BRepPrimAPI_MakeBox(
        gp_Pnt(float(i*200),0,0),10.,10.,10.).Shape(),
        f'part_{i}',f'part_{i}') for i in range(600)]
    b=list(a)
    b[0]=describe(BRepPrimAPI_MakeBox(
        gp_Pnt(0.,0.,0.),10.,10.,10.).Shape(),'part_0','part_0_new')
    return a,b

class TridentNativeFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a,cls.b=make_parts()

    def check_uncertain(self,records):
        self.assertEqual(len(records),600)
        self.assertEqual(sum(r.status=='SAME' for r in records),599)
        self.assertEqual(sum(r.status=='UNCERTAIN' for r in records),1)
        self.assertFalse(any(r.status in ('REMOVED','ADDED','CHANGED','MOVED') for r in records))
        self.assertEqual({r.a_index for r in records},set(range(600)))
        self.assertEqual({r.b_index for r in records},set(range(600)))

    def test_world_native_failure_continues(self):
        with patch.object(comparison,'guarded_world_reexport',
                          side_effect=NativeGeometryFailure('UnprovenRepair: invalid wire')) as worker, \
             patch.object(comparison,'equivalent_rigid',return_value=(False,None,None)):
            records=comparison.compare(self.a,self.b,tolerance=.01,step_reexport_tolerance=True)
        self.assertGreaterEqual(worker.call_count,1)
        self.check_uncertain(records)

    def test_rigid_native_failure_continues(self):
        with patch.object(comparison,'guarded_world_reexport',return_value=False), \
             patch.object(comparison,'equivalent_rigid',
                          side_effect=NativeGeometryFailure('native rigid crash')):
            records=comparison.compare(self.a,self.b,tolerance=.01,step_reexport_tolerance=True)
        self.check_uncertain(records)

    def test_global_budget_still_fails_closed(self):
        with patch.object(comparison,'guarded_world_reexport',return_value=False), \
             patch.object(comparison,'equivalent_rigid',
                          side_effect=NativeGeometryFailure('Budżet izolowanych porównań B-Rep wyczerpany')):
            with self.assertRaisesRegex(NativeGeometryFailure,'Budżet izolowanych'):
                comparison.compare(self.a,self.b,tolerance=.01,step_reexport_tolerance=True)

if __name__=='__main__':
    unittest.main()
