"""Cross-stage regressions for the 0.6.15 user diagnostic bottlenecks."""
import json
from dataclasses import replace
import numpy as np
import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Trsf, gp_Vec, gp_Ax1, gp_Pnt, gp_Dir
from OCP.TopLoc import TopLoc_Location
from dsac29.geometry import describe, _precise_world_bounds
from dsac29.parallel_import import write_cache, read_cache
from dsac29 import occurrence_identity, cad_registration, deferred_alignment
from dsac29.world_bounds import WorldBoundsCache
from dsac29.geometry_registry import GeometryRegistry


def copies(count=12):
    shape = BRepPrimAPI_MakeBox(7., 11., 13.).Shape()
    rows = []
    for i in range(count):
        tr = gp_Trsf(); tr.SetTranslation(gp_Vec(i*20., i*3., 0.))
        part = describe(shape.Moved(TopLoc_Location(tr)), 'part', str(i))
        part.step_definition_key = ('immutable-import-A', '0:1:1:10', 1)
        rows.append(part)
    return rows


def test_import_transport_preserves_definitions_and_distinct_placements(tmp_path, monkeypatch):
    original = copies()
    write_cache(tmp_path, original, {'solids': len(original)})
    restored, stats = read_cache(tmp_path)
    assert stats['solids'] == len(original)
    assert [x.step_definition_key for x in restored] == [x.step_definition_key for x in original]
    assert np.allclose([x.center for x in restored], [x.center for x in original])
    calls = []
    canonical = occurrence_identity._canonical
    def counted(*args):
        calls.append(1)
        return canonical(*args)
    monkeypatch.setattr(occurrence_identity, '_canonical', counted)
    result = occurrence_identity.prepare_occurrence_identities(restored, [])
    assert len(calls) == 1
    assert result['xcaf_reuse'] == len(original)-1
    from dsac29.compare import _location_matrix
    assert not np.allclose(_location_matrix(restored[0]), _location_matrix(restored[1]))


def test_old_transport_schema_and_invalid_identity_are_rejected(tmp_path):
    write_cache(tmp_path, copies(1), {})
    path = tmp_path/'shapes.json'
    meta = json.loads(path.read_text())
    meta['schema'] = 1; path.write_text(json.dumps(meta))
    with pytest.raises(RuntimeError, match='wersja'):
        read_cache(tmp_path)
    meta['schema'] = 2
    meta['solids'][0]['step_definition_key'] = ['wrong']
    path.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='XCAF'):
        read_cache(tmp_path)


def test_native_normalization_cache_does_not_lose_wrapper_identity(monkeypatch):
    rows = copies(30)
    for part in rows:
        del part.step_definition_key
    calls = []
    canonical = occurrence_identity._canonical
    def counted(*args):
        calls.append(1)
        return canonical(*args)
    monkeypatch.setattr(occurrence_identity, '_canonical', counted)
    result = occurrence_identity.prepare_occurrence_identities(rows, [])
    assert len(calls) == 1
    assert result['native_reuse'] == 29


def test_exact_bounds_shared_across_stages_and_translated_instances():
    rows = copies(30); context = GeometryRegistry()
    first = WorldBoundsCache.shared(context)
    for part in rows:
        assert first.bounds(part) == pytest.approx(_precise_world_bounds(part.shape), abs=1e-8)
    second = WorldBoundsCache.shared(context)
    assert first is second
    for part in rows:
        second.bounds(part)
    assert first.calculations == 1
    assert first.hits == 59


def test_bounds_rotation_and_replaced_geometry_do_not_reuse_stale_box():
    part = copies(1)[0]; cache = WorldBoundsCache()
    cache.bounds(part)
    tr = gp_Trsf(); tr.SetRotation(gp_Ax1(gp_Pnt(), gp_Dir(0, 0, 1)), .7)
    rotated = replace(part, shape=part.shape.Moved(TopLoc_Location(tr)))
    assert cache.bounds(rotated) == pytest.approx(_precise_world_bounds(rotated.shape))
    part.shape = BRepPrimAPI_MakeBox(50., 11., 13.).Shape()
    assert cache.bounds(part) == pytest.approx(_precise_world_bounds(part.shape))
    assert cache.calculations == 3


@pytest.mark.parametrize('change_pose', [False, True])
def test_retry_retains_finished_negatives_only_for_identical_pose(monkeypatch, change_pose):
    from test_incomplete_registration_retry import scene
    from dsac29.registration_search import continue_registration
    a, b, rows, state = scene(monkeypatch)
    snapshots = []
    def support(*args, **kwargs):
        cache = kwargs['proof_cache']
        snapshots.append(set(cache.completed_negative_pairs))
        if len(snapshots) == 1:
            cache.completed_negative_pairs.add((0, 0))
            cache.failed_pairs.add((1, 1))
            cache.native_errors[1, 1] = 'fixture timeout'
        return dict(count=8, checked=8, proofs=0)
    monkeypatch.setattr(deferred_alignment, 'frame_support', support)
    deferred_alignment.propose(a, b, rows, .01, search_state=state)
    assert state.failures[0]['completed_negative_pairs'] == [(0, 0)]
    if change_pose:
        state.failures[0]['offset'][0] += .04
    continue_registration(a, b, .01, state)
    assert snapshots[1] == (set() if change_pose else {(0, 0)})


def test_expired_anchor_search_keeps_previous_diagnostics():
    from types import SimpleNamespace
    from dsac29.unique_anchors import proven_translations
    evidence = {'proven': 2, 'anchors': [{'a': 0, 'b': 1}]}
    state = SimpleNamespace(unique_anchor_diagnostics=evidence)
    assert proven_translations([], [], .01, state, 0, clock=lambda: 1) == []
    assert state.unique_anchor_diagnostics is evidence


def test_retry_uses_other_diverse_witnesses_without_shrinking_sample():
    from dsac29.registration_gate import _select_retry_proof_pairs
    parts = copies(80); pairs = [(i, i) for i in range(80)]
    initial = _select_retry_proof_pairs(pairs, parts, 24, set())
    slow = set(initial[:18])
    retry = _select_retry_proof_pairs(pairs, parts, 24, slow)
    assert len(retry) == len(set(retry)) == 24
    assert not slow.intersection(retry)
    assert {i for i, j in retry} != {i for i, j in initial}
    full = _select_retry_proof_pairs(pairs, parts, 80, slow)
    assert set(full) == set(pairs)  # exhausted alternatives must not hide failures
    assert set(full[-18:]) == slow


def test_persistent_import_namespace_survives_cache_but_not_changed_source(tmp_path, monkeypatch):
    from pathlib import Path
    from dsac29.import_cache import load_step_persistent
    monkeypatch.setenv('DSCOMPARE_IMPORT_CACHE', 'on')
    monkeypatch.setenv('DSCOMPARE_CACHE_DIR', str(tmp_path/'cache'))
    source = Path(__file__).resolve().parents[1]/'samples'/'RAMA_REV_03.step'
    path = tmp_path/'input.step'; path.write_bytes(source.read_bytes())
    first = load_step_persistent(path)
    cached = load_step_persistent(path)
    assert [p.step_definition_key for p in first] == [p.step_definition_key for p in cached]
    path.write_bytes(path.read_bytes().replace(b'ISO-10303-21;', b'ISO-10303-21;\n/* changed */', 1))
    changed = load_step_persistent(path)
    assert first[0].step_definition_key != changed[0].step_definition_key


def test_expanded_frame_sample_keeps_all_preliminary_witnesses():
    from test_r13_deferred_alignment import models
    from dsac29.registration_gate import frame_support, FrameProofCache
    a, _ = models(count=80, stable=80, shift=0)
    cache = FrameProofCache()
    initial = frame_support(a, a, .01, proofs=24, proof_cache=cache)
    saved = list(cache.sample_pairs)
    expanded = frame_support(a, a, .01, proofs=48, proof_cache=cache)
    assert initial['proofs'] == 24 and expanded['proofs'] == 48
    assert cache.sample_pairs[:24] == saved
    assert len(set(cache.sample_pairs)) == 48
    assert cache.proof_calls == 48


def test_broad_bounds_contain_exact_bounds_without_extrema(monkeypatch):
    from dsac29 import geometry
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    part = describe(BRepPrimAPI_MakeCylinder(6., 17.).Shape(), 'cylinder', '0')
    tr = gp_Trsf(); tr.SetRotation(gp_Ax1(gp_Pnt(), gp_Dir(1, 1, 0)), .7)
    part.shape = part.shape.Moved(TopLoc_Location(tr))
    exact = geometry._precise_world_bounds(part.shape)
    def forbidden(*args):
        raise AssertionError('Broad phase must not compute precise extrema')
    monkeypatch.setattr(geometry, '_precise_world_bounds', forbidden)
    cache = WorldBoundsCache()
    broad = cache.broad_bounds(part)
    assert np.all(broad[:3] <= exact[:3] + 1e-8)
    assert np.all(broad[3:] >= exact[3:] - 1e-8)
    delta = np.array([130., 280., 410.])
    tr = gp_Trsf(); tr.SetTranslation(gp_Vec(*delta))
    moved = replace(part, shape=part.shape.Moved(TopLoc_Location(tr)))
    assert cache.broad_bounds(moved) == pytest.approx(broad + np.tile(delta, 2))
    assert cache.calculations == 0
    assert cache.broad_calculations == 1
    assert cache.broad_hits == 1
