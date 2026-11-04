"""Guard against reintroducing expensive identical material retries.

This is a source-level regression test: full OCCT behavioral validation runs
separately against public OpenArm/Voron/Trident STEP assemblies.
"""
import ast
from pathlib import Path


def test_deterministic_native_failure_is_fail_closed():
    source = (Path(__file__).resolve().parents[1] / 'dsac29' / 'revision_overlap.py').read_text(encoding='utf8')
    tree = ast.parse(source)
    # Guard ordering matters: skip must occur before the fresh native call.
    guard = source.index("'MATERIAL_BOOLEAN_UNVERIFIED:'")
    skip = source.index("'SKIP_DETERMINISTIC_FAILURE'")
    failure = source.index("'Niepotwierdzony podział materiału (bez ponawiania identycznej operacji): '")
    retry = source.index("measured_brep('revision_material_regions_fresh_retry'")
    assert guard < skip < failure < retry
    assert "'INVALID_BREP_AFTER_REPAIR:'" in source[guard:retry]
    assert "stat['region_retry_skipped_deterministic']" in source[guard:retry]
    assert 'continue' in source[failure:retry]
    assert tree is not None
