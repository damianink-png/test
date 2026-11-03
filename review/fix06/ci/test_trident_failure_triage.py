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
        with self.assertRaises(AssertionError):
            analyze(a,s)

    def test_occurrence_guard(self):
        a, s = fixture()
        a['comparison']['covered_A'] = 1
        with self.assertRaises(AssertionError):
            analyze(a,s)

    def test_multiple_failure_flags(self):
        self.assertEqual(set(categories('UnprovenRepair: invalid wire; fallback Timeout')),
                         {'INVALID_TOPOLOGY','TIMEOUT_OR_BUDGET'})

if __name__ == '__main__':
    unittest.main()
