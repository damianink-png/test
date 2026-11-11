"""Regression: accelerated occurrence bucket selection must equal exhaustive scan.

Candidate selection is never a geometric proof.  The fast neighbourhood
index may only change cost, not which CAD solids reach the B-Rep stage.
"""
from collections import Counter
from random import Random
from types import SimpleNamespace

from dsac29.occurrence_identity import prepare_occurrence_identities


def test_neighbourhood_index_matches_exhaustive_candidate_filter(monkeypatch):
    from dsac29 import occurrence_identity as identity

    rng = Random(20261111)
    # Include negative coordinates, boundary offsets and many unrelated families.
    keys = [(rng.randrange(-150, 151), rng.randrange(-150, 151))
            for _ in range(1200)]
    keys += [(-7, 11)] * 3 + [(0, 0)] * 3 + [(99, -99)] * 4
    keys += [(-9, 9), (-5, 13), (2, 2), (97, -101), None]
    counts = Counter(k for k in keys if k is not None)
    repeated = {k for k, count in counts.items() if count >= 3}
    expected = sum(
        k is not None and any(abs(k[0] - r[0]) <= 2 and
                              abs(k[1] - r[1]) <= 2 for r in repeated)
        for k in keys
    )

    # Avoid native CAD and expensive serialization: limit=0 returns immediately
    # after the candidate selection stage, which is exactly what is under test.
    parts = [SimpleNamespace(key=k) for k in keys]
    monkeypatch.setattr(identity, "_bucket", lambda part: part.key)
    result = prepare_occurrence_identities(parts, [], limit=0)
    assert result["selected"] == expected
    assert result["skipped"] == expected
    assert result["proven"] == 0


def test_no_repeated_family_does_not_select_or_serialize(monkeypatch):
    from dsac29 import occurrence_identity as identity

    keys = [(i * 7, i * 11) for i in range(200)]
    parts = [SimpleNamespace(key=k) for k in keys]
    monkeypatch.setattr(identity, "_bucket", lambda part: part.key)
    result = prepare_occurrence_identities(parts, [], limit=0)
    assert result["selected"] == 0
    assert result["proven"] == 0


def test_neighbourhood_boundary_and_large_sparse_families(monkeypatch):
    """No false exclusions at +/-2; +/-3 must remain outside the filter."""
    from dsac29 import occurrence_identity as identity

    # Families are spaced apart so their expanded neighbourhoods cannot
    # overlap; also exercise negative bucket coordinates and axis corners.
    centres = [(i * 17 - 510, i * 23 - 690) for i in range(80)]
    keys = [centre for centre in centres for _ in range(3)]
    for v, a in centres:
        keys.extend(((v + 2, a + 2), (v - 2, a - 2),
                     (v + 2, a - 2), (v - 2, a + 2),
                     (v + 3, a), (v, a - 3)))
    keys.append(None)
    counts = Counter(k for k in keys if k is not None)
    repeated = {k for k, count in counts.items() if count >= 3}
    expected = sum(k is not None and any(
        abs(k[0] - r[0]) <= 2 and abs(k[1] - r[1]) <= 2
        for r in repeated) for k in keys)
    parts = [SimpleNamespace(key=k) for k in keys]
    monkeypatch.setattr(identity, "_bucket", lambda part: part.key)
    result = prepare_occurrence_identities(parts, [], limit=0)
    assert result["selected"] == expected
    assert result["skipped"] == expected
    assert result["proven"] == 0
