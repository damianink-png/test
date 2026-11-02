"""Synthetic regression tests for the strict Trident audit; no geometry claims."""
import json
import tempfile
import unittest
from pathlib import Path
import trident_exact_audit as audit

def good_summary():
    return {
        "source_A":"Trident_Assembly1.step",
        "source_B":"trident_assembly.step",
        "source_fingerprints":{
            "A":audit.SOURCES["Trident_Assembly1.step"]["sha256"],
            "B":audit.SOURCES["trident_assembly.step"]["sha256"],
        },
        "solids_A":2,"solids_B":2,
        "statuses":{"SAME":1,"REMOVED":1,"ADDED":1},
        "records":[
            {"status":"SAME","a_index":0,"b_index":0,"verification":"confirmed"},
            {"status":"REMOVED","a_index":1,"b_index":None,"verification":"confirmed"},
            {"status":"ADDED","a_index":None,"b_index":1,"verification":"confirmed"},
        ],
        "analysis_complete":True,"material_analysis_complete":True,
        "revision_overlap":{"failed_pairs_total":0,"incomplete":False},
        "material_errors":[],"step_export_error":None,
    }

def inspect(data):
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"PODSUMOWANIE.json"
        p.write_text(json.dumps(data),encoding="utf-8")
        return audit.strict_summary(p)

class TridentAuditRegression(unittest.TestCase):
    def test_complete_valid(self):
        self.assertTrue(inspect(good_summary())["strict_pass"])
    def test_duplicate_a_occurrence(self):
        d=good_summary()
        d["records"][1]["a_index"]=0
        self.assertIn("incomplete_or_duplicate_A_coverage",inspect(d)["audit_errors"])
    def test_missing_b_occurrence(self):
        d=good_summary()
        d["records"].pop()
        d["statuses"].pop("ADDED")
        self.assertIn("incomplete_or_duplicate_B_coverage",inspect(d)["audit_errors"])
    def test_misleading_status_counts(self):
        d=good_summary()
        d["statuses"]["SAME"]=2
        self.assertIn("status_counts_do_not_match_records",inspect(d)["audit_errors"])
    def test_wrong_input_sha(self):
        d=good_summary()
        d["source_fingerprints"]["B"]="0"*64
        self.assertIn("source_fingerprints_missing_or_mismatched",inspect(d)["audit_errors"])
    def test_uncertain_not_a_pass(self):
        d=good_summary()
        d["records"][0]["status"]="UNCERTAIN"
        d["statuses"]={"UNCERTAIN":1,"REMOVED":1,"ADDED":1}
        self.assertIn("uncertain_records",inspect(d)["audit_errors"])
    def test_material_errors_not_a_pass(self):
        d=good_summary()
        d["material_errors"]={"1":"common failed"}
        self.assertIn("material_errors",inspect(d)["audit_errors"])
    def test_partial_not_a_pass(self):
        d=good_summary()
        d["analysis_complete"]=False
        self.assertIn("analysis_marked_incomplete",inspect(d)["audit_errors"])

if __name__=="__main__":
    unittest.main()
