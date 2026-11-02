import unittest
from dsac29.candidate_policy import decide_pair

class CandidatePolicyTests(unittest.TestCase):
    def test_different_shapes_small_overlap_search_first(self):
        d=decide_pair(volume_a=100,volume_b=120,common_volume=8,valid_boolean=True)
        self.assertEqual(d.action,"SEARCH_ALTERNATIVES")
    def test_different_shapes_after_exhaustion(self):
        d=decide_pair(volume_a=100,volume_b=120,common_volume=8,valid_boolean=True,other_candidates_exhausted=True)
        self.assertEqual(d.action,"UNMATCHED_A_AND_B")
    def test_invalid_boolean_does_not_force_added_removed(self):
        d=decide_pair(volume_a=100,volume_b=120,common_volume=-1,valid_boolean=False,other_candidates_exhausted=True)
        self.assertEqual(d.action,"RETRY_ISOLATED")
    def test_true_revision_retained(self):
        d=decide_pair(volume_a=100,volume_b=120,common_volume=85,valid_boolean=True,shape_evidence=True)
        self.assertEqual(d.action,"VERIFY_CHANGED")
    def test_similar_sizes_alone_do_not_match(self):
        d=decide_pair(volume_a=100,volume_b=101,common_volume=60,valid_boolean=True)
        self.assertEqual(d.action,"REVIEW_CANDIDATE")
    def test_geometry_signature(self):
        d=decide_pair(volume_a=100,volume_b=100,same_geometry_signature=True)
        self.assertEqual(d.action,"KEEP_GEOMETRY_MATCH")

if __name__=="__main__":
    unittest.main()
