"""RC7 safety regression: small leftover sets must not bypass isolation."""
from dsac29.revision_overlap import _should_guard_common

def test_trident_1595_with_52_unmatched_is_guarded():
    assert _should_guard_common(1595,1595)

def test_v2_1715_with_few_unmatched_is_guarded():
    assert _should_guard_common(1715,1715)

def test_mixed_sizes_use_larger_assembly():
    assert _should_guard_common(599,600)
    assert _should_guard_common(600,599)

def test_small_assemblies_keep_existing_fast_path():
    assert not _should_guard_common(599,599)
    assert not _should_guard_common(5,5)
