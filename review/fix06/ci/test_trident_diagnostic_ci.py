"""Synthetic regressions: diagnostic continuation is never a full CAD PASS."""
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from dsac29 import native_guard, revision_overlap, material_deltas
from dsac29.compare import Record
from dsac29.geometry import describe, _precise_world_bounds
from dsac29.report import produce
from dsac29.cli import process

def part(x,length,name):
    return describe(BRepPrimAPI_MakeBox(gp_Pnt(x,0,0),length,10,10).Shape(),name,name)

def inputs():
    a=[part(0,10,'bad_old'),part(100,10,'good_old')]
    b=[part(0,11,'bad_new'),part(100,11,'good_new')]
    return a,b,[Record(0,None,'REMOVED',''),Record(1,None,'REMOVED',''),
                Record(None,0,'ADDED',''),Record(None,1,'ADDED','')]

def fail_common(old,new,tol):
    if _precise_world_bounds(old)[0]<50:
        raise native_guard.NativeGeometryFailure('UnprovenRepair: source invalid')
    return material_deltas.operate(material_deltas.BRepAlgoAPI_Common,old,new,tol)

def fail_regions(old,new,tol,**kw):
    if old.name=='bad_old':
        raise native_guard.NativeGeometryFailure('INVALID_BREP_AFTER_REPAIR')
    return material_deltas.calculate(old,new,tol,**kw)

class DiagnosticContinuation(unittest.TestCase):
    def test_diagnostic_keeps_all_occurrences_and_never_passes(self):
        a,b,records=inputs();messages=[]
        with patch.object(native_guard,'guarded_common',side_effect=fail_common),\
             patch.object(revision_overlap,'calculate',side_effect=fail_regions):
            out,regions,stat=revision_overlap.merge_material_revisions(
                a,b,records,diagnostic_only=True,progress=messages.append)
        self.assertTrue(stat['incomplete'])
        self.assertTrue(stat['diagnostic_only'])
        self.assertEqual(stat['accepted'],1)
        self.assertEqual(stat['unverified_A'],1)
        self.assertEqual(stat['unverified_B'],1)
        self.assertEqual([(r.a_index,r.b_index,r.status) for r in out],
                         [(None,0,'UNCERTAIN'),(1,1,'CHANGED'),(0,None,'UNCERTAIN')])
        self.assertEqual({r.a_index for r in out if r.a_index is not None},{0,1})
        self.assertEqual({r.b_index for r in out if r.b_index is not None},{0,1})
        self.assertTrue(any('DIAGNOSTIC_ONLY_INCOMPLETE' in m for m in messages))
        self.assertIn('A[0] / B[0]',out[0].note)
        self.assertEqual(len(regions),1)
        with tempfile.TemporaryDirectory() as td:
            folder,error=produce(Path(td),a,b,out,7850.,generate_step=False,
                                 revision_style=True,full_bom=False,
                                 report_context={'revision_overlap':stat})
            self.assertIsNone(error)
            summary=json.loads((folder/'PODSUMOWANIE.json').read_text())
            self.assertFalse(summary['analysis_complete'])
            self.assertFalse(summary['material_analysis_complete'])
            self.assertEqual(summary['statuses']['UNCERTAIN'],2)
            self.assertTrue(summary['revision_overlap']['diagnostic_only'])

    def test_default_strict_mode_still_fails_closed(self):
        a,b,records=inputs()
        with patch.object(native_guard,'guarded_common',side_effect=fail_common),\
             patch.object(revision_overlap,'calculate',side_effect=fail_regions):
            with self.assertRaisesRegex(native_guard.NativeGeometryFailure,'UnprovenRepair'):
                revision_overlap.merge_material_revisions(a,b,records)

    def test_success_is_not_downgraded(self):
        a,b,records=inputs()
        with patch.object(native_guard,'guarded_common',side_effect=lambda old,new,tol:
                          material_deltas.operate(material_deltas.BRepAlgoAPI_Common,old,new,tol)):
            out,regions,stat=revision_overlap.merge_material_revisions(
                a,b,records,diagnostic_only=True)
        self.assertFalse(stat.get('incomplete'))
        self.assertNotIn('diagnostic_only',stat)
        self.assertEqual(sum(r.status=='CHANGED' for r in out),2)
        self.assertEqual(len(regions),2)

    def test_cli_opt_in_defaults_off(self):
        param=inspect.signature(process).parameters['diagnostic_only']
        self.assertIs(param.default,False)

if __name__=='__main__':unittest.main()
