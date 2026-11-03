import copy
import unittest
from trident_failure_triage import EXPECTED, analyze, categories

def fixture():
    a = {'inputs': {name: {'bytes': size, 'sha256': digest, 'verified': True}
                    for name, (size, digest) in EXPECTED.items()},
         'comparison': {'solids_A': 2, 'solids_B': 3, 'covered_A': 2, 'covered_B': 3,
                        'statuses': {'SAME': 1, 'ADDED': 2, 'REMOVED': 1, 'UNCERTAIN': 1},
                        'failed_pairs': [{'error': 'UnprovenRepair: invalid wire; fallback Timeout'}],
                        'failed_pairs_total': 1, 'strict_pass': False, 'uncertain_records': 1}}
    s = {'source_fingerprints': {'A': EXPECTED['Trident_Assembly1.step'][1],
                                'B': EXPECTED['trident_assembly.step'][1]},
         'solids_A': 2, 'solids_B': 3, 'statuses': a['comparison']['statuses'],
         'analysis_complete': False, 'material_analysis_complete': False}
    return a, s

class TriageTests(unittest.TestCase):
    def test_incomplete_is_not_pass(self):
        a, s = fixture()
        self.assertEqual(analyze(a,s)['status'], 'INCOMPLETE')

    def test_sha_guard(self):
        a, s = fixture()
        a['inputs']['Trident_Assembly1.step']['sha256'] = '0'*64
        with self.assertRaises(ValueError):
            analyze(a,s)

    def test_occurrence_guard(self):
        a, s = fixture()
        a['comparison']['covered_A'] = 1
        with self.assertRaises(ValueError):
            analyze(a,s)

    def test_multiple_failure_flags(self):
        self.assertEqual(set(categories('UnprovenRepair: invalid wire; fallback Timeout')),
                         {'INVALID_TOPOLOGY','TIMEOUT_OR_BUDGET'})

    def test_failed_pair_cannot_be_full_pass(self):
        a, s = fixture()
        a['comparison']['strict_pass'] = True
        # Keep the histogram consistent: failed_pairs_total alone must block PASS.
        s['analysis_complete'] = True
        s['material_analysis_complete'] = True
        self.assertEqual(analyze(a, s)['status'], 'INCOMPLETE')

    def test_missing_verification_fails_closed(self):
        a, s = fixture()
        del a['inputs']['Trident_Assembly1.step']['verified']
        with self.assertRaises(ValueError):
            analyze(a, s)

    def test_sample_exceeds_total_fails_closed(self):
        a, s = fixture()
        a['comparison']['failed_pairs_total'] = 0
        with self.assertRaises(ValueError):
            analyze(a, s)

    def test_malformed_status_fails_closed(self):
        a, s = fixture()
        a['comparison']['statuses']['UNCERTAIN'] = -1
        with self.assertRaises(ValueError):
            analyze(a, s)

    def test_uncertain_histogram_mismatch_rejected(self):
        a, s = fixture()
        a['comparison']['uncertain_records'] = 0
        with self.assertRaisesRegex(ValueError, 'UNCERTAIN histogram mismatch'):
            analyze(a, s)

    def test_uncertain_histogram_cannot_be_boolean(self):
        a, s = fixture()
        a['comparison']['statuses']['UNCERTAIN'] = True
        s['statuses'] = a['comparison']['statuses']
        with self.assertRaises(ValueError):
            analyze(a, s)

    def test_clean_evidence_pass(self):
        a, s = fixture()
        a['comparison']['failed_pairs'] = []
        a['comparison']['failed_pairs_total'] = 0
        a['comparison']['uncertain_records'] = 0
        a['comparison']['statuses']['UNCERTAIN'] = 0
        a['comparison']['strict_pass'] = True
        s['analysis_complete'] = True
        s['material_analysis_complete'] = True
        self.assertEqual(analyze(a, s)['status'], 'PASS')

if __name__ == '__main__':
    unittest.main()
