import unittest
from dsac29.overlap_evidence import classify_overlap

class OverlapEvidenceTests(unittest.TestCase):
    def test_small_accidental_overlap(self):
        result = classify_overlap(100, 120, 10, valid_boolean=True)
        self.assertEqual(result.decision, "REJECT_CANDIDATE")

    def test_real_revision_candidate(self):
        result = classify_overlap(100, 120, 85, valid_boolean=True)
        self.assertEqual(result.decision, "POSSIBLE_REVISION")

    def test_small_part_inside_large_part_is_not_confirmed_revision(self):
        result = classify_overlap(10, 1000, 10, valid_boolean=True)
        self.assertEqual(result.decision, "REVIEW_CANDIDATE")

    def test_invalid_common_fails_closed(self):
        result = classify_overlap(100, 100, -5, valid_boolean=True)
        self.assertEqual(result.decision, "UNKNOWN")

    def test_boolean_error_fails_closed(self):
        result = classify_overlap(100, 100, 50, valid_boolean=False)
        self.assertEqual(result.decision, "UNKNOWN")

    def test_intermediate_overlap(self):
        result = classify_overlap(100, 100, 35, valid_boolean=True)
        self.assertEqual(result.decision, "REVIEW_CANDIDATE")

if __name__ == "__main__":
    unittest.main()
